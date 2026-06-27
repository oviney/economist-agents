#!/usr/bin/env python3
"""Economist Content Flow — Agent SDK orchestration.

The original implementation used CrewAI Flow decorators (@start /
@listen / @router) to chain Stage 3 + Stage 4 crews. After the ADR-0006
Phase 2 migration (epic #308), the LLM work runs through the Anthropic
Agent SDK pipeline at ``src.agent_sdk.pipeline.run_pipeline`` and the
state machine becomes plain sequential Python — easier to read, easier
to test, and one fewer framework dependency.

Stages:
    1. discover_topics — topic scout + dedup gate
    2. editorial_review — 6-persona weighted board vote
    3. generate_content — Agent SDK Stage 3 (Writer + Graphics); hero image
       only when ``image_mode="hero"`` (see Image policy below)
    4. quality_gate — frontmatter schema + Agent SDK Stage 4 + validator
    5a. publish — index + persist
    5b. revise — one retry with feedback, then quarantine

Image policy (#410):
    The CLI (``python -m src.agent_sdk.pipeline``) implements the #403
    human handshake — it pauses after Stage 3 (exit code 10) for a
    human-dropped hero image and resumes via ``--resume``. This Python
    API does NOT pause; instead ``EconomistContentFlow(image_mode=...)``
    chooses the policy up front:
    - ``"chart_only"`` (default): ship on the chart alone; no paid image
      API; Stage 4 validates without a hero so a missing hero never
      forces a revision.
    - ``"hero"``: explicit opt-in to generate a DALL-E hero after Stage 3.

Usage:
    from src.economist_agents.flow import EconomistContentFlow

    flow = EconomistContentFlow()
    result = flow.kickoff()
"""

from __future__ import annotations

import asyncio
import logging
import os
import pathlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import orjson
import yaml as _yaml

from scripts.article_evaluator import ArticleEvaluator
from scripts.frontmatter_schema import FrontmatterSchema
from src.agent_sdk._shared import (
    BudgetExceededError,
    EmptyResearchBriefError,
    refine_image_metadata,
)
from src.agent_sdk.pipeline import run_pipeline
from src.agent_sdk.stage3_runner import MalformedArticleError
from src.economist_agents.adapters import (
    create_llm_client,
    generate_featured_image,
    run_editorial_board,
    scout_topics,
)
from src.tools.topic_deduplicator import TopicDeduplicator

logger = logging.getLogger(__name__)

PUBLISH_THRESHOLD = 70
MAX_REVISIONS = 2
PIPELINE_RESULT_PATH = Path(
    os.environ.get("PIPELINE_RESULT_PATH", "output/pipeline_result.json")
)


class EconomistContentFlow:
    """Sequential orchestrator for the end-to-end content pipeline."""

    def __init__(
        self, image_mode: Literal["chart_only", "hero"] = "chart_only"
    ) -> None:
        """Construct the flow.

        ``image_mode`` is the Python-API image policy (#410). Unlike the CLI
        handshake (``python -m src.agent_sdk.pipeline``, which pauses for a
        human-dropped hero image), the flow does not pause:
        - ``"chart_only"`` (default): ship the article on its chart alone. No
          paid image API is called, and Stage 4 is told to validate without a
          hero image so a missing hero never routes a valid draft to revision.
        - ``"hero"``: explicit opt-in to generate a DALL-E hero image after
          Stage 3 (requires ``OPENAI_API_KEY``).
        """
        if image_mode not in {"chart_only", "hero"}:
            raise ValueError(
                f"image_mode must be 'chart_only' or 'hero', got {image_mode!r}"
            )
        self.image_mode = image_mode
        self._deduplicator = TopicDeduplicator()
        self.state: dict[str, Any] = {}

    @staticmethod
    def _null_article_draft(check: str, message: str) -> dict[str, Any]:
        """Zero-score draft that routes quality_gate to revision."""
        return {
            "article": "",
            "chart_data": {},
            # Empty string lets _patch_frontmatter on retry use the writer's own image field.
            "featured_image": "",
            "featured_image_local": "",
            "image_alt": "",
            "image_caption": "",
            "stage4_already_run": False,
            "publication_validator_passed": False,
            "publication_validator_issues": [
                {"check": check, "severity": "CRITICAL", "message": message}
            ],
            "editorial_score": 0,
            "gates_passed": 0,
        }

    # ─── public entry point ────────────────────────────────────────────

    def kickoff(self) -> dict[str, Any]:
        """Run the full pipeline and return the terminal result dict."""
        topics = self.discover_topics()
        selected = self.editorial_review(topics)
        draft = self.generate_content(selected)
        # Budget-exceeded is a hard abort — revising won't lower per-call
        # cost, so skip the quality_gate/revision dance entirely.
        if self.state.get("abort_reason") == "budget_exceeded":
            result = self._budget_exceeded_result()
        else:
            decision = self.quality_gate(draft)
            if decision == "publish":
                result = self.publish_article()
            else:
                result = self.request_revision()
        self._write_pipeline_result(result)
        return result

    def _budget_exceeded_result(self) -> dict[str, Any]:
        """Terminal pipeline result when an Agent SDK call hit max_budget_usd."""
        logger.error("⛔ Flow aborted: budget exceeded")
        return {
            "status": "budget_exceeded",
            "editorial_score": 0,
            "gates_passed": 0,
            "revision_reason": self.state.get(
                "revision_reason", "Agent SDK budget exceeded"
            ),
            "budget_usd": self.state.get("budget_usd"),
        }

    def _write_pipeline_result(self, result: dict[str, Any]) -> None:
        """Write output/pipeline_result.json for the CI metrics step in content-pipeline.yml."""
        PIPELINE_RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "status": result.get("status", "unknown"),
            "editorial_score": result.get("editorial_score", 0),
            "gates_passed": result.get("gates_passed", 0),
        }
        if result.get("status") == "budget_exceeded":
            payload["revision_reason"] = result.get("revision_reason", "")
            payload["budget_usd"] = result.get("budget_usd")
        try:
            PIPELINE_RESULT_PATH.write_bytes(orjson.dumps(payload))
        except Exception as exc:
            logger.warning("Failed to write pipeline result file (non-fatal): %s", exc)

    # ─── stage 1 ───────────────────────────────────────────────────────

    def discover_topics(self) -> dict[str, Any]:
        logger.info("🔭 Flow Stage 1: Topic Discovery")
        client = create_llm_client()

        raw_topics: list[dict[str, Any]] = []
        for attempt in range(2):
            raw_topics = scout_topics(
                client,
                focus_area=None,
                allow_empty_archive=bool(
                    os.environ.get("TOPIC_SCOUT_ALLOW_EMPTY_ARCHIVE", "").strip(),
                ),
            )
            if raw_topics:
                break
            logger.warning(
                "   ⚠️  Topic scout returned empty (attempt %d/2), retrying...",
                attempt + 1,
            )

        if not raw_topics:
            raise ValueError(
                "Topic scout returned no topics after 2 attempts. "
                "Check LLM connectivity and scout_topics() JSON parsing.",
            )

        topics = []
        for t in raw_topics:
            topics.append(
                {
                    "topic": t["topic"],
                    "score": round(t.get("total_score", 0) * 10 / 25, 1),
                    "hook": t.get("hook", ""),
                    "thesis": t.get("thesis", ""),
                    "data_sources": t.get("data_sources", []),
                    "contrarian_angle": t.get("contrarian_angle", ""),
                    "talking_points": t.get("talking_points", ""),
                    "raw": t,
                },
            )
        logger.info("   Generated %d topic candidates", len(topics))

        topics, rejected = self._deduplicator.filter_topics(topics)
        if rejected:
            logger.info(
                "   🚫 Dedup filtered %d topic(s): %s",
                len(rejected),
                ", ".join(f"'{t.get('topic', '?')}'" for t in rejected),
            )
        warned = [t for t in topics if t.get("dedup_warning")]
        if warned:
            logger.warning(
                "   ⚠️  Dedup flagged %d topic(s) as related coverage: %s",
                len(warned),
                ", ".join(f"'{t.get('topic', '?')}'" for t in warned),
            )
        logger.info("   %d topic(s) forwarded to editorial board", len(topics))
        return {"topics": topics, "timestamp": datetime.now().isoformat()}

    # ─── stage 2 ───────────────────────────────────────────────────────

    def editorial_review(self, topics: dict[str, Any]) -> dict[str, Any]:
        logger.info("📋 Flow Stage 2: Editorial Review")

        topic_list = topics.get("topics", [])
        if not topic_list:
            raise ValueError("No topics available for editorial review")

        client = create_llm_client()
        raw_topics = [t.get("raw", t) for t in topic_list]
        board_result = run_editorial_board(client, raw_topics, parallel=True)

        top = board_result.get("top_pick")
        if not top:
            selected = max(topic_list, key=lambda t: t.get("score", 0))
            logger.warning("   Fallback selection: %s", selected["topic"])
            return selected

        original = top.get("original_topic", {})
        selected = {
            "topic": top["topic"],
            "score": top.get("weighted_score", 0),
            "hook": original.get("hook", ""),
            "thesis": original.get("thesis", ""),
            "consensus": board_result.get("consensus", False),
            "dissenting_views": board_result.get("dissenting_views", []),
        }
        logger.info("   Selected: %s", selected["topic"])
        logger.info("   Score: %.1f/10", selected["score"])
        logger.info("   Consensus: %s", selected["consensus"])
        return selected

    # ─── stage 3 ───────────────────────────────────────────────────────

    def generate_content(self, selected_topic: dict[str, Any]) -> dict[str, Any]:
        self.state["selected_topic"] = selected_topic
        topic = selected_topic.get("topic", "")

        logger.info("✍️  Flow Stage 3: Content Generation (Agent SDK pipeline)")
        logger.info("   Topic: %s", topic)

        try:
            result = asyncio.run(run_pipeline(topic, image_mode=self.image_mode))
        except MalformedArticleError as exc:
            logger.warning(
                "Writer returned malformed output — routing to revision: %s", exc
            )
            self.state["revision_reason"] = str(exc)
            self.state["revision_feedback"] = [
                "Writer returned malformed output with no YAML frontmatter. "
                "Retry: output must start with --- and include a non-empty body."
            ]
            return self._null_article_draft(
                "malformed_output",
                "Writer returned malformed output — see logs for details.",
            )
        except EmptyResearchBriefError as exc:
            logger.warning(
                "Web searches returned no results — routing to revision: %s", exc
            )
            self.state["revision_reason"] = str(exc)
            self.state["revision_feedback"] = [
                "Research providers (arXiv, Semantic Scholar) returned no sources "
                "— try a more research-covered angle on the topic."
            ]
            return self._null_article_draft(
                "empty_research_brief",
                "No research sources found — try a more research-covered topic angle.",
            )
        except BudgetExceededError as exc:
            # Hard abort. Revising won't lower per-call cost — it just burns
            # more budget — so we mark the run terminal and let kickoff()
            # short-circuit to a `status: budget_exceeded` pipeline result.
            logger.error("Agent SDK budget exceeded — aborting pipeline: %s", exc)
            self.state["abort_reason"] = "budget_exceeded"
            self.state["revision_reason"] = str(exc)
            self.state["budget_usd"] = exc.budget_usd
            return self._null_article_draft(
                "budget_exceeded",
                f"Agent SDK budget exceeded — pipeline aborted: {exc}",
            )
        article = result.article
        logger.info("   ✅ Article generated: %d words", len(article.split()))
        logger.info(
            "   ✅ Cost: $%.4f (%s + %s)",
            result.total_cost_usd,
            result.writer_model,
            result.graphics_model,
        )
        logger.info(
            "   ✅ Score: %s%% / %s/5 gates",
            result.editorial_score,
            result.gates_passed,
        )

        if self.image_mode == "chart_only":
            # Ship on the chart alone. No paid image API, no vision refine.
            # run_pipeline already stripped the hero frontmatter before Stage 4,
            # so a missing hero never forces a revision. featured_image is left
            # EMPTY (not blog-default.svg): _patch_frontmatter's
            # `if featured_image:` guard then leaves the article image-less,
            # which the publication validator accepts ("no image → pass"). The
            # default-image fallback would instead be a CRITICAL deploy-time
            # rejection (publication_validator default_image_fallback).
            logger.info("   🖼️  image_mode=chart_only — skipping hero image generation")
            return {
                "article": article,
                "chart_data": result.chart_data,
                "featured_image": "",
                "featured_image_local": "",
                "image_alt": "",
                "image_caption": "",
                "stage4_already_run": True,
                "publication_validator_passed": result.publication_validator_passed,
                "publication_validator_issues": result.publication_validator_issues,
                "editorial_score": result.editorial_score,
                "gates_passed": result.gates_passed,
            }

        # ── hero mode (explicit opt-in): generate a DALL-E featured image ──
        # Slug for the DALL-E filename
        slug = topic.lower()
        for ch in " :?!,.'\"()":
            slug = slug.replace(ch, "-")
        slug = slug.strip("-")[:60]

        output_dir = Path("output/images")
        output_dir.mkdir(parents=True, exist_ok=True)
        image_path = str(output_dir / f"{slug}.png")

        if not os.environ.get("OPENAI_API_KEY"):
            logger.warning(
                "   ⚠️  OPENAI_API_KEY not set — DALL-E image generation requires it "
                "even when Claude is the primary LLM",
            )

        logger.info("🎨 Generating featured image...")
        featured_image = "/assets/images/blog-default.svg"
        try:
            generated = generate_featured_image(
                topic=topic,
                article_summary=article[:200],
                output_path=image_path,
            )
            if generated:
                featured_image = f"/assets/images/{slug}.png"
                logger.info("   ✅ Featured image: %s", image_path)
            else:
                logger.info("   ℹ️  Using default image")
        except Exception as exc:
            logger.warning("   ℹ️  Image generation failed (%s), using default", exc)

        # Extract image_alt / image_caption drafts emitted by the writer
        _image_alt, _image_caption = "", ""
        if article.startswith("---"):
            _parts = article.split("---", 2)
            if len(_parts) >= 2:
                try:
                    _fm = _yaml.safe_load(_parts[1]) or {}
                    _image_alt = _fm.get("image_alt", "") or ""
                    _image_caption = _fm.get("image_caption", "") or ""
                except Exception:
                    pass

        # Ground image metadata with Claude vision (async; falls back on failure)
        _refined = asyncio.run(
            refine_image_metadata(image_path, _image_alt, _image_caption)
        )

        return {
            "article": article,
            "chart_data": result.chart_data,
            "featured_image": featured_image,
            "featured_image_local": image_path,
            "image_alt": _refined["image_alt"],
            "image_caption": _refined["image_caption"],
            "stage4_already_run": True,
            "publication_validator_passed": result.publication_validator_passed,
            "publication_validator_issues": result.publication_validator_issues,
            "editorial_score": result.editorial_score,
            "gates_passed": result.gates_passed,
        }

    # ─── stage 4 ───────────────────────────────────────────────────────

    def quality_gate(self, article_draft: dict[str, Any]) -> str:
        logger.info("🔍 Flow Stage 4: Quality Gate")
        self.state["article_draft"] = article_draft

        article_text = self._patch_frontmatter(
            article_draft.get("article", ""),
            article_draft.get("featured_image", "/assets/images/blog-default.svg"),
            image_alt=article_draft.get("image_alt", ""),
            image_caption=article_draft.get("image_caption", ""),
        )

        schema_result = FrontmatterSchema().validate_article(article_text)
        if not schema_result.is_valid:
            self.state["decision"] = "revision"
            self.state["revision_reason"] = (
                f"Frontmatter schema validation failed: {schema_result.errors}"
            )
            self.state["revision_feedback"] = schema_result.errors
            logger.warning("   Decision: REVISION (schema: %s)", schema_result.errors)
            return "revision"

        editorial_score = article_draft.get("editorial_score", 0)
        gates_passed = article_draft.get("gates_passed", 0)
        validator_passed = article_draft.get("publication_validator_passed", False)
        validator_issues = article_draft.get("publication_validator_issues", [])

        logger.info("   Editorial Score: %s/100", editorial_score)
        logger.info("   Gates Passed: %s/5", gates_passed)

        # The Agent SDK pipeline already ran ArticleEvaluator and
        # PublicationValidator inside Stage 4. Apply the same publish
        # rules here so the routing logic is explicit.
        self.state["quality_result"] = {
            "article": article_text,
            "editorial_score": editorial_score,
            "gates_passed": gates_passed,
            "publication_validator_passed": validator_passed,
            "publication_validator_issues": validator_issues,
        }
        self.state["validation_issues"] = validator_issues

        if editorial_score < PUBLISH_THRESHOLD:
            self.state["decision"] = "revision"
            self.state["revision_reason"] = (
                f"Editorial score {editorial_score}/100 below {PUBLISH_THRESHOLD}"
            )
            self.state["revision_feedback"] = [
                f"Score {editorial_score} too low; tighten thesis, evidence, ending.",
            ]
            logger.warning(
                "   Decision: REVISION (score %s < %s)",
                editorial_score,
                PUBLISH_THRESHOLD,
            )
            return "revision"

        if not validator_passed:
            critical = [i for i in validator_issues if i.get("severity") == "CRITICAL"]
            self.state["decision"] = "revision"
            self.state["revision_reason"] = (
                f"Publication validation failed: {len(critical)} critical issues"
            )
            self.state["revision_feedback"] = [i.get("message", "") for i in critical]
            logger.warning(
                "   Decision: REVISION (%d critical validation issues)", len(critical)
            )
            for ci in critical:
                logger.warning(
                    "      ❌ %s: %s",
                    ci.get("check", "unknown"),
                    ci.get("message", ""),
                )
            return "revision"

        self.state["decision"] = "publish"
        logger.info("   Decision: PUBLISH ✅")
        return "publish"

    # ─── publish path ──────────────────────────────────────────────────

    def publish_article(self) -> dict[str, Any]:
        quality_result = self.state.get("quality_result", {})
        article_text = quality_result.get("article", "")

        logger.info("✅ Flow Complete: PUBLISHED")
        logger.info(
            "   Editorial Score: %s/100", quality_result.get("editorial_score", 0)
        )

        self._run_article_eval(article_text, "published")

        selected_topic = self.state.get("selected_topic", {})
        title = selected_topic.get("topic", "")
        if title and article_text:
            self._deduplicator.index_article(title=title, content=article_text)

        # Deploy to the blog repo when credentials are present. In CI this is
        # invoked instead by the "Publish to Blog Repository" workflow step;
        # this path covers local runs and the MCP-triggered flow. See #336.
        deploy_status = self._deploy_to_blog(article_text, title)

        return {
            "status": "published",
            "article": article_text,
            "editorial_score": quality_result.get("editorial_score", 0),
            "gates_passed": quality_result.get("gates_passed", 0),
            "deploy_status": deploy_status,
        }

    def _deploy_to_blog(self, article_text: str, title: str) -> str:
        """Persist the article and invoke :func:`scripts.deploy_to_blog.deploy`.

        Returns one of:
          - ``"skipped_no_credentials"``: BLOG_REPO_* env vars not set.
          - ``"skipped_empty_article"``: nothing to publish.
          - ``"skipped_in_ci"``: ``GITHUB_ACTIONS=true`` — CI workflow handles it.
          - The :class:`DeployResult.status` string on success
            (``"published"``, ``"up_to_date"``, ``"validation_failed"``, ``"dry_run"``).
          - ``"failed"`` if deploy raises — flow continues, error is logged.
        """
        if not article_text:
            return "skipped_empty_article"

        blog_owner = os.environ.get("BLOG_REPO_OWNER") or os.environ.get(
            "BLOG_OWNER", ""
        )
        blog_repo = os.environ.get("BLOG_REPO_NAME") or os.environ.get("BLOG_REPO", "")
        token = os.environ.get("BLOG_REPO_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
        if not (blog_owner and blog_repo and token):
            logger.info(
                "🚫 Blog deploy skipped — BLOG_REPO_OWNER/BLOG_REPO_NAME/"
                "BLOG_REPO_TOKEN not all set"
            )
            return "skipped_no_credentials"

        # In CI the workflow's "Publish to Blog Repository" step runs the
        # script explicitly. Avoid a double-deploy when invoked from there.
        if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
            logger.info("🚫 Blog deploy delegated to CI workflow step")
            return "skipped_in_ci"

        # Persist the article so deploy() has a real file path to work with.
        slug = self._slugify(title) or "generated-article"
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        article_path = output_dir / f"{date_str}-{slug}.md"
        article_path.write_text(article_text)
        logger.info("📝 Wrote article: %s", article_path)

        # Lazy import keeps test collection fast and avoids loading PIL
        # transitively until we actually deploy.
        from scripts.deploy_to_blog import DeployError, deploy

        try:
            result = deploy(
                article_path=article_path,
                blog_owner=blog_owner,
                blog_repo=blog_repo,
                token=token,
            )
        except DeployError as exc:
            logger.error("Blog deploy failed (non-fatal): %s", exc)
            return "failed"

        logger.info("🚀 Blog deploy finished: %s", result.status)
        return result.status

    @staticmethod
    def _slugify(text: str) -> str:
        """Best-effort lowercase-dashed slug suitable for a Jekyll filename."""
        if not text:
            return ""
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        return slug[:60]

    # ─── revision path ─────────────────────────────────────────────────

    def request_revision(self) -> dict[str, Any]:
        retry_count = self.state.get("retry_count", 0)
        if retry_count >= MAX_REVISIONS:
            quality_result = self.state.get("quality_result", {})
            logger.warning(
                "⛔ Revision exhausted (%d/%d retries used)",
                retry_count,
                MAX_REVISIONS,
            )
            return {
                "status": "needs_revision",
                "editorial_score": quality_result.get("editorial_score", 0),
                "gates_passed": quality_result.get("gates_passed", 0),
                "revision_reason": self.state.get("revision_reason", "Unknown"),
                "retry_count": retry_count,
            }

        self.state["retry_count"] = retry_count + 1
        revision_feedback = self.state.get("revision_feedback", [])
        revision_reason = self.state.get("revision_reason", "")
        feedback_text = (
            "\n".join(revision_feedback) if revision_feedback else revision_reason
        )

        logger.info("🔄 Revision attempt %d/%d", retry_count + 1, MAX_REVISIONS)
        logger.info("   Feedback: %s", feedback_text[:200])

        topic = self.state.get("selected_topic", {}).get("topic", "")
        enhanced_topic = (
            f"{topic}\n\n"
            f"REVISION INSTRUCTIONS — the previous draft failed review. "
            f"Fix these issues:\n{feedback_text}"
        )

        try:
            # Must carry the flow's image policy: a chart_only flow that runs
            # revision in the default "hero" mode would re-introduce the #403
            # missing-image-file false rejection (no DALL-E runs on this path).
            result = asyncio.run(
                run_pipeline(enhanced_topic, image_mode=self.image_mode)
            )
        except BudgetExceededError as exc:
            # Budget caps don't get fixed by retrying — abort cleanly.
            logger.error("Agent SDK budget exceeded on revision — aborting: %s", exc)
            return {
                "status": "budget_exceeded",
                "editorial_score": 0,
                "gates_passed": 0,
                "revision_reason": str(exc),
                "budget_usd": exc.budget_usd,
                "retry_count": retry_count + 1,
            }
        except (MalformedArticleError, EmptyResearchBriefError) as exc:
            logger.warning("Pipeline error on revision — quarantining: %s", exc)
            return {
                "status": "needs_revision",
                "editorial_score": 0,
                "gates_passed": 0,
                "revision_reason": str(exc),
                "retry_count": retry_count + 1,
            }
        draft = self.state.get("article_draft", {})
        edited_article = self._patch_frontmatter(
            result.article,
            draft.get("featured_image", ""),
            image_alt=draft.get("image_alt", ""),
            image_caption=draft.get("image_caption", ""),
        )

        editorial_score = result.editorial_score
        gates_passed = result.gates_passed
        validator_passed = result.publication_validator_passed
        validator_issues = result.publication_validator_issues

        self.state["quality_result"] = {
            "article": edited_article,
            "editorial_score": editorial_score,
            "gates_passed": gates_passed,
            "publication_validator_passed": validator_passed,
        }

        if editorial_score >= PUBLISH_THRESHOLD and validator_passed:
            logger.info("   ✅ Revision succeeded (score: %s/100)", editorial_score)
            return {
                "status": "published",
                "article": edited_article,
                "editorial_score": editorial_score,
                "gates_passed": gates_passed,
                "retry_count": self.state["retry_count"],
            }

        critical = [i for i in validator_issues if i.get("severity") == "CRITICAL"]
        logger.warning(
            "   ⚠️  Revision still failing (score: %s, issues: %d)",
            editorial_score,
            len(critical),
        )
        for ci in critical:
            logger.warning(
                "      ❌ %s: %s",
                ci.get("check", "unknown"),
                ci.get("message", ""),
            )

        title_match = re.search(
            r'title:\s*["\']?(.+?)["\']?\s*$',
            edited_article,
            re.MULTILINE,
        )
        slug_source = title_match.group(1) if title_match else edited_article[:80]
        slug = re.sub(r"[^a-z0-9]+", "-", slug_source.lower()).strip("-")[:60]
        quarantine_dir = pathlib.Path("output") / "quarantine"
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        quarantine_path = (
            quarantine_dir / f"{datetime.now().strftime('%Y-%m-%d')}-{slug}.md"
        )
        quarantine_path.write_text(edited_article)
        logger.warning("   📄 Quarantined article saved: %s", quarantine_path)

        self._run_article_eval(edited_article, "quarantined")

        return {
            "status": "needs_revision",
            "editorial_score": editorial_score,
            "gates_passed": gates_passed,
            "validation_issues": [i.get("message", "") for i in critical],
            "retry_count": self.state["retry_count"],
            "quarantine_path": str(quarantine_path),
        }

    # ─── helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _patch_frontmatter(
        article_text: str,
        featured_image: str,
        *,
        image_alt: str = "",
        image_caption: str = "",
    ) -> str:
        """Force image path, inject image metadata, rename summary→description."""
        if not article_text.startswith("---"):
            return article_text
        parts = article_text.split("---", 2)
        if len(parts) < 3:
            return article_text
        fm = parts[1]
        if featured_image:
            if "image:" in fm:
                fm = re.sub(r"image:.*", f"image: {featured_image}", fm)
            else:
                fm = fm.rstrip() + f"\nimage: {featured_image}\n"
        if image_alt:
            if "image_alt:" in fm:
                fm = re.sub(r"image_alt:.*", f'image_alt: "{image_alt}"', fm)
            else:
                fm = fm.rstrip() + f'\nimage_alt: "{image_alt}"\n'
        if image_caption:
            if "image_caption:" in fm:
                fm = re.sub(
                    r"image_caption:.*", f'image_caption: "{image_caption}"', fm
                )
            else:
                fm = fm.rstrip() + f'\nimage_caption: "{image_caption}"\n'
        if "summary:" in fm and "description:" not in fm:
            fm = fm.replace("summary:", "description:", 1)
        return "---" + fm + "---" + parts[2]

    def _run_article_eval(self, article: str, status: str) -> None:
        try:
            evaluator = ArticleEvaluator()
            result = evaluator.evaluate(article, filename=status)
            result.persist("logs/article_evals.json")
            logger.info(
                "   📊 Article eval: %s/%s (%s%%)",
                result.total_score,
                result.max_score,
                result.percentage,
            )
            for dim, score in result.scores.items():
                detail = result.details.get(dim, "")
                logger.info("      %s: %s/10 — %s", dim, score, detail)
        except Exception as exc:
            logger.warning("   ⚠️  Article evaluation failed: %s", exc)


def main() -> None:
    """CLI entry point for standalone Flow execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("╔════════════════════════════════════════════════════════════════╗")
    logger.info("║ ECONOMIST CONTENT FLOW - End-to-End Pipeline                  ║")
    logger.info("╚════════════════════════════════════════════════════════════════╝")

    flow = EconomistContentFlow()
    try:
        result = flow.kickoff()
        logger.info(
            "╔════════════════════════════════════════════════════════════════╗"
        )
        logger.info(
            "║ FLOW RESULT                                                     ║"
        )
        logger.info(
            "╚════════════════════════════════════════════════════════════════╝"
        )
        logger.info("Status: %s", result.get("status", "unknown"))
        logger.info("Editorial Score: %s/100", result.get("editorial_score", 0))
        if result.get("retry_count"):
            logger.info("Retries: %s", result["retry_count"])
    except Exception as exc:
        logger.error("❌ Flow execution failed: %s", exc)
        raise


if __name__ == "__main__":
    main()
