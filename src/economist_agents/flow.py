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

from datetime import datetime
from pathlib import Path
from typing import Any

from crewai.flow.flow import Flow, listen, router, start

from scripts.agent_trace_logger import AgentTraceLogger
from src.crews.stage3_crew import Stage3Crew
from src.crews.stage4_crew import Stage4Crew
from src.economist_agents.adapters import (
    PublicationValidator,
    create_llm_client,
    generate_featured_image,
    run_editorial_board,
    scout_topics,
)

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
        """Initialize flow with crew dependencies and tracer."""
        super().__init__()
        self.stage4_crew = Stage4Crew()
        self._tracer = AgentTraceLogger()

    @property
    def tracer(self) -> AgentTraceLogger:
        """Expose the agent trace logger for downstream consumers."""
        return self._tracer

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
            raw_topics = scout_topics(client, focus_area=None)
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

        result: dict[str, Any] = {
            "topics": topics,
            "timestamp": datetime.now().isoformat(),
        }
        self._tracer.log_agent_action(
            agent_name="TopicScout",
            stage="discover_topics",
            inputs={"focus_area": None, "attempt_limit": 2},
            outputs={"topic_count": len(topics), "timestamp": result["timestamp"]},
            decision=f"generated {len(topics)} topic candidates",
        )
        return result

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
            self._tracer.log_agent_action(
                agent_name="EditorialBoard",
                stage="editorial_review",
                inputs={"topic_count": len(topic_list)},
                outputs={
                    "selected_topic": selected.get("topic"),
                    "score": selected.get("score"),
                },
                decision=f"fallback selection: '{selected.get('topic')}'",
                status="revision",
            )
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

        self._tracer.log_agent_action(
            agent_name="EditorialBoard",
            stage="editorial_review",
            inputs={"topic_count": len(topic_list)},
            outputs={
                "selected_topic": selected["topic"],
                "score": selected["score"],
                "consensus": selected["consensus"],
                "dissenting_views": selected.get("dissenting_views", []),
            },
            decision=f"selected '{selected['topic']}' (score {selected['score']:.1f})",
        )
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

        word_count = len(result.get("article", "").split())
        self._tracer.log_agent_action(
            agent_name="Stage3Crew",
            stage="generate_content",
            inputs={"topic": topic},
            outputs={
                "word_count": word_count,
                "featured_image": result.get("featured_image"),
                "has_chart_data": bool(result.get("chart_data")),
            },
            decision=f"generated article ({word_count} words)",
        )
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

        # Inject featured image into frontmatter before review
        article_text = article_draft.get("article", "")
        featured_image = article_draft.get(
            "featured_image", "/assets/images/blog-default.svg"
        )
        if (
            article_text.startswith("---")
            and "image:" not in article_text.split("---", 2)[1]
        ):
            parts = article_text.split("---", 2)
            if len(parts) >= 3:
                article_text = (
                    "---"
                    + parts[1].rstrip()
                    + f"\nimage: {featured_image}\n"
                    + "---"
                    + parts[2]
                )

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
            self._tracer.log_agent_action(
                agent_name="FrontmatterSchema",
                stage="quality_gate",
                inputs={"article_length": len(article_text)},
                outputs={"errors": schema_result.errors},
                decision=f"revision — schema validation failed: {schema_result.errors}",
                status="revision",
            )
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
            self._tracer.log_agent_action(
                agent_name="Stage4Crew",
                stage="quality_gate",
                inputs={"article_length": len(article_text)},
                outputs={
                    "editorial_score": editorial_score,
                    "gates_passed": gates_passed,
                },
                decision=f"revision — only {gates_passed}/5 editorial gates passed",
                status="revision",
            )
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
            self._tracer.log_agent_action(
                agent_name="Stage4Crew",
                stage="quality_gate",
                inputs={"article_length": len(article_text)},
                outputs={
                    "editorial_score": editorial_score,
                    "gates_passed": gates_passed,
                },
                decision=f"revision — score {editorial_score} below threshold {PUBLISH_THRESHOLD}",
                status="revision",
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
            self._tracer.log_agent_action(
                agent_name="PublicationValidator",
                stage="quality_gate",
                inputs={"article_length": len(edited_article)},
                outputs={"critical_issues": len(critical), "total_issues": len(issues)},
                decision=f"revision — {len(critical)} critical validation issues",
                status="revision",
            )
            return "revision"

        self.state["decision"] = "publish"
        print("   Decision: PUBLISH ✅")
        self._tracer.log_agent_action(
            agent_name="PublicationValidator",
            stage="quality_gate",
            inputs={"article_length": len(edited_article)},
            outputs={"editorial_score": editorial_score, "gates_passed": gates_passed},
            decision=f"publish — score {editorial_score}/100, all gates passed",
        )
        return "publish"

    @listen("publish")
    def publish_article(self) -> dict[str, Any]:
        """Terminal stage (publish path): Article approved for publication.

        Returns:
            dict with status, article, editorial_score, gates_passed.
        """
        quality_result = self.state.get("quality_result", {})

        print("✅ Flow Complete: PUBLISHED")
        print(f"   Editorial Score: {quality_result.get('editorial_score', 0)}/100")

        result: dict[str, Any] = {
            "status": "published",
            "article": quality_result.get("article", ""),
            "editorial_score": quality_result.get("editorial_score", 0),
            "gates_passed": quality_result.get("gates_passed", 0),
        }
        self._tracer.log_agent_action(
            agent_name="EconomistContentFlow",
            stage="publish_article",
            inputs={},
            outputs={
                "status": result["status"],
                "editorial_score": result["editorial_score"],
                "gates_passed": result["gates_passed"],
            },
            decision=f"published — editorial score {result['editorial_score']}/100",
        )
        return result

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
            result: dict[str, Any] = {
                "status": "needs_revision",
                "editorial_score": quality_result.get("editorial_score", 0),
                "gates_passed": quality_result.get("gates_passed", 0),
                "revision_reason": self.state.get("revision_reason", "Unknown"),
                "retry_count": retry_count,
            }
            self._tracer.log_agent_action(
                agent_name="EconomistContentFlow",
                stage="request_revision",
                inputs={"retry_count": retry_count, "max_revisions": MAX_REVISIONS},
                outputs=result,
                decision=f"revision exhausted after {retry_count} retries",
                status="error",
            )
            return result

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

        self.state["quality_result"] = result

        # Run publication validator
        validator = PublicationValidator(
            expected_date=datetime.now().strftime("%Y-%m-%d")
        )
        is_valid, issues = validator.validate(edited_article)

        if editorial_score >= PUBLISH_THRESHOLD and is_valid:
            print(f"   ✅ Revision succeeded (score: {editorial_score}/100)")
            published: dict[str, Any] = {
                "status": "published",
                "article": edited_article,
                "editorial_score": editorial_score,
                "gates_passed": gates_passed,
                "retry_count": self.state["retry_count"],
            }
            self._tracer.log_agent_action(
                agent_name="EconomistContentFlow",
                stage="request_revision",
                inputs={"retry_count": self.state["retry_count"]},
                outputs={
                    "status": published["status"],
                    "editorial_score": editorial_score,
                    "gates_passed": gates_passed,
                },
                decision=f"revision succeeded (score {editorial_score}/100)",
            )
            return published

        critical = [i for i in issues if i.get("severity") == "CRITICAL"]
        print(
            f"   ⚠️  Revision still failing (score: {editorial_score}, issues: {len(critical)})"
        )
        needs_revision: dict[str, Any] = {
            "status": "needs_revision",
            "editorial_score": editorial_score,
            "gates_passed": gates_passed,
            "validation_issues": [i["message"] for i in critical],
            "retry_count": self.state["retry_count"],
        }
        self._tracer.log_agent_action(
            agent_name="EconomistContentFlow",
            stage="request_revision",
            inputs={"retry_count": self.state["retry_count"]},
            outputs={
                "status": needs_revision["status"],
                "editorial_score": editorial_score,
                "critical_issues": len(critical),
            },
            decision=f"revision still failing (score {editorial_score}, {len(critical)} critical)",
            status="revision",
        )
        return needs_revision


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
