#!/usr/bin/env python3
"""
Economist Content Flow - Deterministic State-Machine Orchestration

Implements João Moura's Production ROI principles via CrewAI Flows:
- Deterministic progression (@start/@listen decorators)
- Zero-agency state transitions (no autonomous routing)
- Quality gate routing (@router for publish/revision paths)

Usage:
    from src.economist_agents.flow import EconomistContentFlow

    flow = EconomistContentFlow()
    result = flow.kickoff()
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from crewai.flow.flow import Flow, listen, router, start

from src.crews.stage3_crew import Stage3Crew
from src.crews.stage4_crew import Stage4Crew
from src.economist_agents.adapters import (
    PublicationValidator,
    create_llm_client,
    generate_featured_image,
    run_editorial_board,
    scout_topics,
)
from src.tools.topic_deduplicator import TopicDeduplicator

# Editorial score threshold (0-100 scale) for publication
PUBLISH_THRESHOLD = 80
MAX_REVISIONS = 2


class EconomistContentFlow(Flow):
    """
    Production-grade content generation flow with deterministic orchestration.

    Flow Stages:
    1. discover_topics() - @start - LLM-based topic scouting
    2. editorial_review() - @listen - 6-persona weighted board voting
    3. generate_content() - @listen - Research → Write → Graphics pipeline
    4. quality_gate() - @router - Stage4Crew + PublicationValidator routing
    5a. publish_article() - @listen("publish") - Terminal success
    5b. request_revision() - @listen("revision") - 1-retry with feedback
    """

    def __init__(self) -> None:
        """Initialize flow with crew dependencies."""
        super().__init__()
        self.stage4_crew = Stage4Crew()
        self._deduplicator = TopicDeduplicator()

    @start()
    def discover_topics(self) -> dict[str, Any]:
        """Stage 1: Discover topic candidates via Topic Scout.

        Makes 2 LLM calls (trend research + topic generation).

        Returns:
            dict with "topics" list and "timestamp".
        """
        print("🔭 Flow Stage 1: Topic Discovery")

        client = create_llm_client()

        # Retry once if scout returns empty (LLM JSON parsing can fail)
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

        # Normalise scout scores (0-25 sum) to 0-10 scale for display
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

        # ── Deduplication step ──────────────────────────────────────────
        # Query published_articles ChromaDB collection and remove near-
        # duplicates before the editorial board wastes a vote on them.
        # Thresholds (issue #157):
        #   >0.8  → REJECT (too similar to existing article)
        #   0.6-0.8 → WARN  (related coverage exists; flagged for editors)
        #   <0.6  → PASS   (novel topic)
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
        # ───────────────────────────────────────────────────────────────

        return {"topics": topics, "timestamp": datetime.now().isoformat()}

    @listen(discover_topics)
    def editorial_review(self, topics: dict[str, Any]) -> dict[str, Any]:
        """Stage 2: Editorial board selects winning topic.

        6 personas vote in parallel with weighted scoring.

        Args:
            topics: Output from discover_topics().

        Returns:
            dict with selected topic, score, consensus info.
        """
        print("📋 Flow Stage 2: Editorial Review")

        topic_list = topics.get("topics", [])
        if not topic_list:
            raise ValueError("No topics available for editorial review")

        client = create_llm_client()
        raw_topics = [t.get("raw", t) for t in topic_list]

        board_result = run_editorial_board(client, raw_topics, parallel=True)

        top = board_result.get("top_pick")
        if not top:
            # Fallback: pick highest-scored topic
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

    @listen(editorial_review)
    def generate_content(self, selected_topic: dict[str, Any]) -> dict[str, Any]:
        """Stage 3: Research → Write → Graphics pipeline via Stage3Crew.

        Args:
            selected_topic: Output from editorial_review().

        Returns:
            dict with "article" (markdown) and "chart_data" (dict).
        """
        # Preserve for revision loop
        self.state["selected_topic"] = selected_topic

        topic = selected_topic.get("topic", "")

        print("✍️  Flow Stage 3: Content Generation (Stage3Crew)")
        print(f"   Topic: {topic}")

        stage3_crew = Stage3Crew(topic=topic)
        result = stage3_crew.kickoff()

        article = result.get("article", "")
        print(f"   ✅ Article generated: {len(article.split())} words")

        # Generate featured image via DALL-E
        slug = topic.lower()
        for ch in " :?!,.'\"()":
            slug = slug.replace(ch, "-")
        slug = slug.strip("-")[:60]

        output_dir = Path("output/images")
        output_dir.mkdir(parents=True, exist_ok=True)
        image_path = str(output_dir / f"{slug}.png")

        print("🎨 Generating featured image...")
        try:
            generated = generate_featured_image(
                topic=topic,
                article_summary=article[:200],
                output_path=image_path,
            )
            if generated:
                result["featured_image"] = f"/assets/images/{slug}.png"
                result["featured_image_local"] = image_path
                print(f"   ✅ Featured image: {image_path}")
            else:
                result["featured_image"] = "/assets/images/blog-default.svg"
                print("   ℹ️  Using default image")
        except Exception as e:
            result["featured_image"] = "/assets/images/blog-default.svg"
            print(f"   ℹ️  Image generation failed ({e}), using default")

        return result

    @router(generate_content)
    def quality_gate(self, article_draft: dict[str, Any]) -> str:
        """Stage 4: Editorial review + publication validation.

        Runs Stage4Crew (5-gate editorial review) then PublicationValidator.
        Routes to "publish" if both pass, "revision" otherwise.

        Args:
            article_draft: Output from generate_content().

        Returns:
            "publish" or "revision" routing decision.
        """
        print("🔍 Flow Stage 4: Quality Gate")

        # Preserve draft for revision loop
        self.state["article_draft"] = article_draft

        # Override image path with the actual generated path (the Writer Agent
        # invents its own slug which won't match the DALL-E output filename)
        article_text = article_draft.get("article", "")
        featured_image = article_draft.get(
            "featured_image", "/assets/images/blog-default.svg"
        )
        if article_text.startswith("---"):
            parts = article_text.split("---", 2)
            if len(parts) >= 3:
                import re as _re

                # Replace existing image: or add if missing
                fm = parts[1]
                if "image:" in fm:
                    fm = _re.sub(r"image:.*", f"image: {featured_image}", fm)
                else:
                    fm = fm.rstrip() + f"\nimage: {featured_image}\n"

                # Fix Writer's persistent summary→description confusion.
                # gpt-4o outputs "summary:" despite prompt saying "description:".
                if "summary:" in fm and "description:" not in fm:
                    fm = fm.replace("summary:", "description:", 1)

                article_text = "---" + fm + "---" + parts[2]

        # Gate 0: Frontmatter schema validation (Story #117 boundary)
        from scripts.frontmatter_schema import FrontmatterSchema

        schema_result = FrontmatterSchema().validate_article(article_text)
        if not schema_result.is_valid:
            self.state["decision"] = "revision"
            self.state["revision_reason"] = (
                f"Frontmatter schema validation failed: {schema_result.errors}"
            )
            self.state["revision_feedback"] = schema_result.errors
            print(f"   Decision: REVISION (schema: {schema_result.errors})")
            return "revision"

        # Stage4Crew expects positional dict with "article" key
        result = self.stage4_crew.kickoff(
            {
                "article": article_text,
                "chart_data": article_draft.get("chart_data"),
            }
        )

        editorial_score = result.get("editorial_score", 0)
        gates_passed = result.get("gates_passed", 0)
        edited_article = result.get("article", article_draft.get("article", ""))

        print(f"   Editorial Score: {editorial_score}/100")
        print(f"   Gates Passed: {gates_passed}/5")

        self.state["quality_result"] = result

        # Gate 1: All 5 editorial gates must pass
        if gates_passed < 5:
            self.state["decision"] = "revision"
            self.state["revision_reason"] = (
                f"Only {gates_passed}/5 editorial gates passed"
            )
            self.state["revision_feedback"] = result.get("specific_edits", [])
            print(f"   Decision: REVISION ({gates_passed}/5 gates, need 5/5)")
            return "revision"

        # Gate 2: Editorial score
        if editorial_score < PUBLISH_THRESHOLD:
            self.state["decision"] = "revision"
            self.state["revision_reason"] = (
                f"Editorial score {editorial_score}/100 below {PUBLISH_THRESHOLD} threshold"
            )
            self.state["revision_feedback"] = result.get("specific_edits", [])
            print(
                f"   Decision: REVISION (score {editorial_score} < {PUBLISH_THRESHOLD})"
            )
            return "revision"

        # Gate 3: Publication validator
        validator = PublicationValidator(
            expected_date=datetime.now().strftime("%Y-%m-%d")
        )
        is_valid, issues = validator.validate(edited_article)
        self.state["validation_issues"] = issues

        if not is_valid:
            critical = [i for i in issues if i["severity"] == "CRITICAL"]
            self.state["decision"] = "revision"
            self.state["revision_reason"] = (
                f"Publication validation failed: {len(critical)} critical issues"
            )
            self.state["revision_feedback"] = [i["message"] for i in critical]
            print(f"   Decision: REVISION ({len(critical)} critical validation issues)")
            return "revision"

        self.state["decision"] = "publish"
        print("   Decision: PUBLISH ✅")
        return "publish"

    @listen("publish")
    def publish_article(self) -> dict[str, Any]:
        """Terminal stage (publish path): Article approved for publication.

        Returns:
            dict with status, article, editorial_score, gates_passed.
        """
        quality_result = self.state.get("quality_result", {})
        article_text = quality_result.get("article", "")

        print("✅ Flow Complete: PUBLISHED")
        print(f"   Editorial Score: {quality_result.get('editorial_score', 0)}/100")

        # ── Post-publication indexing ───────────────────────────────────
        # Index the article in the published_articles archive so future
        # deduplication runs can detect coverage of this topic.
        selected_topic = self.state.get("selected_topic", {})
        title = selected_topic.get("topic", "")
        if title and article_text:
            self._deduplicator.index_article(title=title, content=article_text)
        # ───────────────────────────────────────────────────────────────

        return {
            "status": "published",
            "article": article_text,
            "editorial_score": quality_result.get("editorial_score", 0),
            "gates_passed": quality_result.get("gates_passed", 0),
        }

    @listen("revision")
    def request_revision(self) -> dict[str, Any]:
        """Revision path: retry content generation once with feedback.

        Re-runs Stage3Crew with revision instructions, then re-runs
        Stage4Crew + PublicationValidator. Returns final result regardless
        of pass/fail (max 1 retry to avoid runaway LLM costs).

        Returns:
            dict with status, article (if published), scores, retry_count.
        """
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

        # Re-run Stage3Crew with revision instructions appended to topic
        topic = self.state.get("selected_topic", {}).get("topic", "")
        enhanced_topic = (
            f"{topic}\n\n"
            f"REVISION INSTRUCTIONS — the previous draft failed review. "
            f"Fix these issues:\n{feedback_text}"
        )

        stage3_crew = Stage3Crew(topic=enhanced_topic)
        new_draft = stage3_crew.kickoff()

        # Re-run Stage4Crew
        result = self.stage4_crew.kickoff(
            {
                "article": new_draft.get("article", ""),
                "chart_data": new_draft.get("chart_data"),
            }
        )

        editorial_score = result.get("editorial_score", 0)
        gates_passed = result.get("gates_passed", 0)
        edited_article = result.get("article", new_draft.get("article", ""))

        # Apply summary→description fixup (same as quality_gate first pass).
        if "summary:" in edited_article and "description:" not in edited_article:
            edited_article = edited_article.replace("summary:", "description:", 1)

        self.state["quality_result"] = result

        # Run publication validator
        validator = PublicationValidator(
            expected_date=datetime.now().strftime("%Y-%m-%d")
        )
        is_valid, issues = validator.validate(edited_article)

        if editorial_score >= PUBLISH_THRESHOLD and is_valid:
            print(f"   ✅ Revision succeeded (score: {editorial_score}/100)")
            return {
                "status": "published",
                "article": edited_article,
                "editorial_score": editorial_score,
                "gates_passed": gates_passed,
                "retry_count": self.state["retry_count"],
            }

        critical = [i for i in issues if i.get("severity") == "CRITICAL"]
        print(
            f"   ⚠️  Revision still failing (score: {editorial_score}, issues: {len(critical)})"
        )

        # Persist quarantined article so it can be reviewed/fixed manually.
        import pathlib
        import re as _re_q

        title_match = _re_q.search(
            r'title:\s*["\']?(.+?)["\']?\s*$', edited_article, _re_q.MULTILINE
        )
        slug_source = title_match.group(1) if title_match else edited_article[:80]
        slug = _re_q.sub(r"[^a-z0-9]+", "-", slug_source.lower()).strip("-")[:60]
        quarantine_dir = pathlib.Path("output") / "quarantine"
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        quarantine_path = (
            quarantine_dir / f"{datetime.now().strftime('%Y-%m-%d')}-{slug}.md"
        )
        quarantine_path.write_text(edited_article)
        print(f"   📄 Quarantined article saved: {quarantine_path}")

        return {
            "status": "needs_revision",
            "editorial_score": editorial_score,
            "gates_passed": gates_passed,
            "validation_issues": [i["message"] for i in critical],
            "retry_count": self.state["retry_count"],
            "quarantine_path": str(quarantine_path),
        }


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

    except Exception as e:
        print(f"\n❌ Flow execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
