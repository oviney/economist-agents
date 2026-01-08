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

from typing import Any

from crewai.flow.flow import Flow, listen, router, start

from src.crews.stage3_crew import Stage3Crew
from src.crews.stage4_crew import Stage4Crew


class EconomistContentFlow(Flow):
    """
    Production-grade content generation flow with deterministic orchestration.

    Flow Stages:
    1. discover_topics() - @start - Entry point, generates topic candidates
    2. editorial_review() - @listen - Selects winning topic for production
    3. generate_content() - @listen - Research → Write → Graphics pipeline
    4. quality_gate() - @router - Editor evaluation with publish/revision routing

    State Management:
    - topics: List of topic candidates with scores
    - selected_topic: Editorial board winner
    - article_draft: Generated content with metadata
    - quality_score: Editor evaluation (0-10 scale)
    - decision: "publish" or "revision"
    """

    def __init__(self):
        """Initialize flow with crew dependencies."""
        super().__init__()
        # Note: Crews will be initialized on-demand in generate_content()
        # Stage3Crew requires topic parameter
        self.stage4_crew = Stage4Crew()

    @start()
    def discover_topics(self) -> dict[str, Any]:
        """
        Entry point: Generate topic candidates via Topic Scout.

        STUB: Currently returns mock topics for Flow architecture validation.
        TODO (Sprint 14): Integrate with Stage1Crew/Stage2Crew (Topic Scout + Editorial Board)

        Returns:
            dict: {
                "topics": [{"topic": str, "score": float, "hook": str}, ...],
                "timestamp": str
            }
        """
        # STUB: Mock topics for Flow validation
        mock_topics = {
            "topics": [
                {
                    "topic": "The AI Testing Paradox: Why Automation Creates More Work",
                    "score": 8.5,
                    "hook": "Companies adopting AI testing tools report 40% more maintenance work",
                    "thesis": "Self-healing tests promise to reduce overhead but create new complexity",
                },
                {
                    "topic": "Quality Engineering's Invisible Tax",
                    "score": 7.2,
                    "hook": "Flaky tests cost Fortune 500 companies $2.1B annually in lost productivity",
                    "thesis": "Test reliability is the new technical debt",
                },
            ],
            "timestamp": "2026-01-07T00:00:00Z",
        }

        print("🔭 Flow Stage 1: Topic Discovery")
        print(f"   Generated {len(mock_topics['topics'])} topic candidates")

        return mock_topics

    @listen(discover_topics)
    def editorial_review(self, topics: dict[str, Any]) -> dict[str, Any]:
        """
        Sequential stage: Editorial board selects winning topic.

        STUB: Currently selects top-scored topic for Flow validation.
        TODO (Sprint 14): Integrate with Stage2Crew (Editorial Board persona voting)

        Args:
            topics: Output from discover_topics()

        Returns:
            dict: {
                "selected_topic": str,
                "score": float,
                "hook": str,
                "thesis": str
            }
        """
        # STUB: Select top-scored topic
        topic_list = topics.get("topics", [])
        if not topic_list:
            raise ValueError("No topics available for editorial review")

        selected = max(topic_list, key=lambda t: t.get("score", 0))

        print("📋 Flow Stage 2: Editorial Review")
        print(f"   Selected: {selected['topic']}")
        print(f"   Score: {selected['score']}/10")

        return selected

    @listen(editorial_review)
    def generate_content(self, selected_topic: dict[str, Any]) -> dict[str, Any]:
        """
        Sequential stage: Research → Write → Graphics pipeline via Stage3Crew.

        Executes Stage3Crew.kickoff() with selected topic as input.
        Stage3Crew orchestrates: ResearchAgent → WriterAgent → GraphicsAgent

        Args:
            selected_topic: Output from editorial_review()

        Returns:
            dict: {
                "article": str (markdown with YAML frontmatter),
                "chart_path": str | None,
                "word_count": int,
                "metadata": dict
            }
        """
        topic = selected_topic.get("topic", "")

        print("✍️  Flow Stage 3: Content Generation (Stage3Crew)")
        print(f"   Topic: {topic}")

        # Initialize Stage3Crew with topic (required parameter)
        stage3_crew = Stage3Crew(topic=topic)

        # Execute Stage3Crew workflow
        # Stage3Crew.kickoff() returns: {article, chart_path, word_count, metadata}
        result = stage3_crew.kickoff()

        print(f"   ✅ Article generated: {result.get('word_count', 0)} words")
        if result.get("chart_path"):
            print(f"   ✅ Chart created: {result['chart_path']}")

        return result

    @router(generate_content)
    def quality_gate(self, article_draft: dict[str, Any]) -> str:
        """
        Router stage: Editor evaluation with publish/revision routing.

        Executes Stage4Crew.kickoff() for 5-gate editorial review.
        Routes based on quality score threshold (≥8 = publish, <8 = revision).

        Args:
            article_draft: Output from generate_content()

        Returns:
            str: "publish" or "revision" (routing decision)
        """
        print("🔍 Flow Stage 4: Quality Gate (Stage4Crew)")

        # Execute Stage4Crew workflow (5-gate editorial review)
        # Stage4Crew.kickoff() returns: {edited_article, gates_passed, quality_score}
        result = self.stage4_crew.kickoff(
            inputs={
                "draft": article_draft.get("article", ""),
                "chart_data": article_draft.get("chart_path"),
            }
        )

        quality_score = result.get("quality_score", 0)
        gates_passed = result.get("gates_passed", 0)

        print(f"   Quality Score: {quality_score}/10")
        print(f"   Gates Passed: {gates_passed}/5")

        # Routing decision: ≥8 publish, <8 revision
        decision = "publish" if quality_score >= 8 else "revision"

        print(f"   Decision: {decision.upper()}")

        # Store result in flow state for downstream access
        self.state["quality_result"] = result
        self.state["decision"] = decision

        return decision

    @listen("publish")
    def publish_article(self) -> dict[str, Any]:
        """
        Terminal stage (publish path): Finalize article for publication.

        TODO (Future): Integrate with Stage5Crew (DevOps publishing automation)

        Returns:
            dict: {
                "status": "published",
                "article_path": str,
                "quality_score": float
            }
        """
        quality_result = self.state.get("quality_result", {})

        print("✅ Flow Complete: PUBLISH PATH")
        print(f"   Quality Score: {quality_result.get('quality_score', 0)}/10")

        return {
            "status": "published",
            "article": quality_result.get("edited_article", ""),
            "quality_score": quality_result.get("quality_score", 0),
            "gates_passed": quality_result.get("gates_passed", 0),
        }

    @listen("revision")
    def request_revision(self) -> dict[str, Any]:
        """
        Terminal stage (revision path): Flag article for rework.

        TODO (Future): Implement revision loop (Writer re-attempt with Editor feedback)

        Returns:
            dict: {
                "status": "needs_revision",
                "quality_score": float,
                "failed_gates": list[str]
            }
        """
        quality_result = self.state.get("quality_result", {})

        print("⚠️  Flow Complete: REVISION REQUIRED")
        print(f"   Quality Score: {quality_result.get('quality_score', 0)}/10")

        return {
            "status": "needs_revision",
            "quality_score": quality_result.get("quality_score", 0),
            "gates_passed": quality_result.get("gates_passed", 0),
            "gates_failed": 5 - quality_result.get("gates_passed", 0),
        }


def main():
    """CLI entry point for standalone Flow execution."""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║ ECONOMIST CONTENT FLOW - Deterministic Orchestration           ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")

    flow = EconomistContentFlow()

    try:
        result = flow.kickoff()

        print("\n╔════════════════════════════════════════════════════════════════╗")
        print("║ FLOW RESULT                                                     ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Quality Score: {result.get('quality_score', 0)}/10")

    except Exception as e:
        print(f"\n❌ Flow execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
