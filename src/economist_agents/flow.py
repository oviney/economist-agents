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
    3. generate_content — Agent SDK Stage 3 (Writer + Graphics) + DALL-E
    4. quality_gate — frontmatter schema + Agent SDK Stage 4 + validator
    5a. publish — index + persist
    5b. revise — one retry with feedback, then quarantine

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
from typing import Any

from scripts.article_evaluator import ArticleEvaluator
from scripts.frontmatter_schema import FrontmatterSchema
from src.agent_sdk.pipeline import run_pipeline
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


class EconomistContentFlow:
    """Sequential orchestrator for the end-to-end content pipeline."""

    def __init__(self) -> None:
        self._deduplicator = TopicDeduplicator()
        self.state: dict[str, Any] = {}

    # ─── public entry point ────────────────────────────────────────────

    def kickoff(self) -> dict[str, Any]:
        """Run the full pipeline and return the terminal result dict."""
        topics = self.discover_topics()
        selected = self.editorial_review(topics)
        draft = self.generate_content(selected)
        decision = self.quality_gate(draft)
        if decision == "publish":
            return self.publish_article()
        return self.request_revision()

    # ─── stage 1 ───────────────────────────────────────────────────────

    def discover_topics(self) -> dict[str, Any]:
        print("🔭 Flow Stage 1: Topic Discovery")
        client = create_llm_client()

        raw_topics: list[dict[str, Any]] = []
        for attempt in range(2):
            raw_topics = scout_topics(
                client,
                focus_area=None,
                allow_empty_archive=bool(
                    os.environ.get("TOPIC_SCOUT_ALLOW_EMPTY_ARCHIVE", "").strip()
                ),
            )
            if raw_topics:
                break
            print(
                f"   ⚠️  Topic scout returned empty (attempt {attempt + 1}/2), retrying..."
            )

        if not raw_topics:
            raise ValueError(
                "Topic scout returned no topics after 2 attempts. "
                "Check LLM connectivity and scout_topics() JSON parsing."
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
                }
            )
        print(f"   Generated {len(topics)} topic candidates")

        topics, rejected = self._deduplicator.filter_topics(topics)
        if rejected:
            print(
                f"   🚫 Dedup filtered {len(rejected)} topic(s): "
                + ", ".join(f"'{t.get('topic', '?')}'" for t in rejected)
            )
        warned = [t for t in topics if t.get("dedup_warning")]
        if warned:
            print(
                f"   ⚠️  Dedup flagged {len(warned)} topic(s) as related coverage: "
                + ", ".join(f"'{t.get('topic', '?')}'" for t in warned)
            )
        print(f"   {len(topics)} topic(s) forwarded to editorial board")
        return {"topics": topics, "timestamp": datetime.now().isoformat()}

    # ─── stage 2 ───────────────────────────────────────────────────────

    def editorial_review(self, topics: dict[str, Any]) -> dict[str, Any]:
        print("📋 Flow Stage 2: Editorial Review")

        topic_list = topics.get("topics", [])
        if not topic_list:
            raise ValueError("No topics available for editorial review")

        client = create_llm_client()
        raw_topics = [t.get("raw", t) for t in topic_list]
        board_result = run_editorial_board(client, raw_topics, parallel=True)

        top = board_result.get("top_pick")
        if not top:
            selected = max(topic_list, key=lambda t: t.get("score", 0))
            print(f"   Fallback selection: {selected['topic']}")
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
        print(f"   Selected: {selected['topic']}")
        print(f"   Score: {selected['score']:.1f}/10")
        print(f"   Consensus: {selected['consensus']}")
        return selected

    # ─── stage 3 ───────────────────────────────────────────────────────

    def generate_content(self, selected_topic: dict[str, Any]) -> dict[str, Any]:
        self.state["selected_topic"] = selected_topic
        topic = selected_topic.get("topic", "")

        print("✍️  Flow Stage 3: Content Generation (Agent SDK pipeline)")
        print(f"   Topic: {topic}")

        result = asyncio.run(run_pipeline(topic))
        article = result.article
        print(f"   ✅ Article generated: {len(article.split())} words")
        print(
            f"   ✅ Cost: ${result.total_cost_usd:.4f} "
            f"({result.writer_model} + {result.graphics_model})"
        )
        print(f"   ✅ Score: {result.editorial_score}% / {result.gates_passed}/5 gates")

        # Slug for the DALL-E filename
        slug = topic.lower()
        for ch in " :?!,.'\"()":
            slug = slug.replace(ch, "-")
        slug = slug.strip("-")[:60]

        output_dir = Path("output/images")
        output_dir.mkdir(parents=True, exist_ok=True)
        image_path = str(output_dir / f"{slug}.png")

        if not os.environ.get("OPENAI_API_KEY"):
            print(
                "   ⚠️  OPENAI_API_KEY not set — DALL-E image generation requires it "
                "even when Claude is the primary LLM"
            )

        print("🎨 Generating featured image...")
        featured_image = "/assets/images/blog-default.svg"
        try:
            generated = generate_featured_image(
                topic=topic,
                article_summary=article[:200],
                output_path=image_path,
            )
            if generated:
                featured_image = f"/assets/images/{slug}.png"
                print(f"   ✅ Featured image: {image_path}")
            else:
                print("   ℹ️  Using default image")
        except Exception as exc:
            print(f"   ℹ️  Image generation failed ({exc}), using default")

        return {
            "article": article,
            "chart_data": result.chart_data,
            "featured_image": featured_image,
            "featured_image_local": image_path,
            "stage4_already_run": True,
            "publication_validator_passed": result.publication_validator_passed,
            "publication_validator_issues": result.publication_validator_issues,
            "editorial_score": result.editorial_score,
            "gates_passed": result.gates_passed,
        }

    # ─── stage 4 ───────────────────────────────────────────────────────

    def quality_gate(self, article_draft: dict[str, Any]) -> str:
        print("🔍 Flow Stage 4: Quality Gate")
        self.state["article_draft"] = article_draft

        article_text = self._patch_frontmatter(
            article_draft.get("article", ""),
            article_draft.get("featured_image", "/assets/images/blog-default.svg"),
        )

        schema_result = FrontmatterSchema().validate_article(article_text)
        if not schema_result.is_valid:
            self.state["decision"] = "revision"
            self.state["revision_reason"] = (
                f"Frontmatter schema validation failed: {schema_result.errors}"
            )
            self.state["revision_feedback"] = schema_result.errors
            print(f"   Decision: REVISION (schema: {schema_result.errors})")
            return "revision"

        editorial_score = article_draft.get("editorial_score", 0)
        gates_passed = article_draft.get("gates_passed", 0)
        validator_passed = article_draft.get("publication_validator_passed", False)
        validator_issues = article_draft.get("publication_validator_issues", [])

        print(f"   Editorial Score: {editorial_score}/100")
        print(f"   Gates Passed: {gates_passed}/5")

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
                f"Score {editorial_score} too low; tighten thesis, evidence, ending."
            ]
            print(
                f"   Decision: REVISION (score {editorial_score} < {PUBLISH_THRESHOLD})"
            )
            return "revision"

        if not validator_passed:
            critical = [i for i in validator_issues if i.get("severity") == "CRITICAL"]
            self.state["decision"] = "revision"
            self.state["revision_reason"] = (
                f"Publication validation failed: {len(critical)} critical issues"
            )
            self.state["revision_feedback"] = [i.get("message", "") for i in critical]
            print(f"   Decision: REVISION ({len(critical)} critical validation issues)")
            for ci in critical:
                print(f"      ❌ {ci.get('check', 'unknown')}: {ci.get('message', '')}")
            return "revision"

        self.state["decision"] = "publish"
        print("   Decision: PUBLISH ✅")
        return "publish"

    # ─── publish path ──────────────────────────────────────────────────

    def publish_article(self) -> dict[str, Any]:
        quality_result = self.state.get("quality_result", {})
        article_text = quality_result.get("article", "")

        print("✅ Flow Complete: PUBLISHED")
        print(f"   Editorial Score: {quality_result.get('editorial_score', 0)}/100")

        self._run_article_eval(article_text, "published")

        selected_topic = self.state.get("selected_topic", {})
        title = selected_topic.get("topic", "")
        if title and article_text:
            self._deduplicator.index_article(title=title, content=article_text)

        return {
            "status": "published",
            "article": article_text,
            "editorial_score": quality_result.get("editorial_score", 0),
            "gates_passed": quality_result.get("gates_passed", 0),
        }

    # ─── revision path ─────────────────────────────────────────────────

    def request_revision(self) -> dict[str, Any]:
        retry_count = self.state.get("retry_count", 0)
        if retry_count >= MAX_REVISIONS:
            quality_result = self.state.get("quality_result", {})
            print(f"⛔ Revision exhausted ({retry_count}/{MAX_REVISIONS} retries used)")
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

        print(f"🔄 Revision attempt {retry_count + 1}/{MAX_REVISIONS}")
        print(f"   Feedback: {feedback_text[:200]}")

        topic = self.state.get("selected_topic", {}).get("topic", "")
        enhanced_topic = (
            f"{topic}\n\n"
            f"REVISION INSTRUCTIONS — the previous draft failed review. "
            f"Fix these issues:\n{feedback_text}"
        )

        result = asyncio.run(run_pipeline(enhanced_topic))
        edited_article = self._patch_frontmatter(
            result.article,
            self.state.get("article_draft", {}).get("featured_image", ""),
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
            print(f"   ✅ Revision succeeded (score: {editorial_score}/100)")
            return {
                "status": "published",
                "article": edited_article,
                "editorial_score": editorial_score,
                "gates_passed": gates_passed,
                "retry_count": self.state["retry_count"],
            }

        critical = [i for i in validator_issues if i.get("severity") == "CRITICAL"]
        print(
            f"   ⚠️  Revision still failing (score: {editorial_score}, issues: {len(critical)})"
        )
        for ci in critical:
            print(f"      ❌ {ci.get('check', 'unknown')}: {ci.get('message', '')}")

        title_match = re.search(
            r'title:\s*["\']?(.+?)["\']?\s*$', edited_article, re.MULTILINE
        )
        slug_source = title_match.group(1) if title_match else edited_article[:80]
        slug = re.sub(r"[^a-z0-9]+", "-", slug_source.lower()).strip("-")[:60]
        quarantine_dir = pathlib.Path("output") / "quarantine"
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        quarantine_path = (
            quarantine_dir / f"{datetime.now().strftime('%Y-%m-%d')}-{slug}.md"
        )
        quarantine_path.write_text(edited_article)
        print(f"   📄 Quarantined article saved: {quarantine_path}")

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
    def _patch_frontmatter(article_text: str, featured_image: str) -> str:
        """Force the image path and rename `summary:` → `description:`."""
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
        if "summary:" in fm and "description:" not in fm:
            fm = fm.replace("summary:", "description:", 1)
        return "---" + fm + "---" + parts[2]

    def _run_article_eval(self, article: str, status: str) -> None:
        try:
            evaluator = ArticleEvaluator()
            result = evaluator.evaluate(article, filename=status)
            result.persist("logs/article_evals.json")
            print(
                f"   📊 Article eval: {result.total_score}/{result.max_score} "
                f"({result.percentage}%)"
            )
            for dim, score in result.scores.items():
                detail = result.details.get(dim, "")
                print(f"      {dim}: {score}/10 — {detail}")
        except Exception as exc:
            print(f"   ⚠️  Article evaluation failed: {exc}")


def main() -> None:
    """CLI entry point for standalone Flow execution."""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║ ECONOMIST CONTENT FLOW - End-to-End Pipeline                  ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")

    flow = EconomistContentFlow()
    try:
        result = flow.kickoff()
        print("\n╔════════════════════════════════════════════════════════════════╗")
        print("║ FLOW RESULT                                                     ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Editorial Score: {result.get('editorial_score', 0)}/100")
        if result.get("retry_count"):
            print(f"Retries: {result['retry_count']}")
    except Exception as exc:
        print(f"\n❌ Flow execution failed: {exc}")
        raise


if __name__ == "__main__":
    main()
