#!/usr/bin/env python3
"""
Product Owner Agent - Autonomous Backlog Refinement

Converts user requests into well-formed user stories with acceptance criteria,
enabling autonomous sprint execution.

Usage:
    python3 scripts/po_agent.py --request "Improve chart quality"
    python3 scripts/po_agent.py --backlog skills/backlog.json
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_client import call_llm, create_llm_client

# ═══════════════════════════════════════════════════════════════════════════
# PO AGENT SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════

PO_AGENT_PROMPT = """You are a Product Owner Agent assisting with autonomous backlog refinement.

YOUR MISSION:
Convert user requests into well-formed user stories with testable acceptance criteria.

STORY GENERATION:
Format: As a [role], I need [capability], so that [business value]

Process:
1. Identify stakeholder role (developer, QE lead, user, system)
2. Extract core capability needed
3. Articulate business value and success metrics
4. Flag ambiguities for human PO review

ACCEPTANCE CRITERIA (Given/When/Then):
Generate 3-7 testable criteria per story:
- Functional: What the system must do
- Quality: Performance, security, accessibility requirements
- Edge Cases: Error handling, boundary conditions

Example:
```
- [ ] Given user request, When PO Agent parses, Then generates user story
- [ ] Given ambiguous requirement, When detected, Then escalates with question
- [ ] Quality: Generation completes in <2 min
```

STORY POINT ESTIMATION:
Use historical velocity model:
- 1 point = 2.8 hours (simple, well-understood)
- 2 points = 5.6 hours (moderate complexity)
- 3 points = 8.4 hours (story size cap for single sprint)
- 5 points = 14 hours (multi-day, consider decomposition)
- 8 points = 22.4 hours (week-long, high risk - recommend split)

Factors:
- Technical complexity
- Functional scope
- Quality requirements (testing, docs, validation)
- Dependencies and unknowns

QUALITY REQUIREMENTS (from REQUIREMENTS_QUALITY_GUIDE.md):
Always specify:
1. Content Quality: Sources, citations, formatting
2. Performance: Time limits, resource usage
3. Accessibility: WCAG compliance if applicable
4. SEO: Meta tags if content-facing
5. Security/Privacy: Data handling requirements
6. Maintainability: Documentation standards

EDGE CASE DETECTION:
Flag for human PO when:
- Requirements ambiguous or contradictory
- Business value unclear
- Technical feasibility uncertain
- Estimated >8 points (needs decomposition)
- Cross-team dependencies detected

OUTPUT FORMAT:
Return JSON with this structure:
{
  "user_story": "As a [role], I need [capability], so that [value]",
  "acceptance_criteria": [
    "[ ] Given X, When Y, Then Z",
    "[ ] Quality: Specific measurable criterion"
  ],
  "story_points": 3,
  "estimation_confidence": "high|medium|low",
  "quality_requirements": {
    "content_quality": "...",
    "performance": "...",
    "accessibility": "...",
    "seo": "...",
    "security": "...",
    "maintainability": "..."
  },
  "priority": "P0|P1|P2",
  "escalations": [
    "Specific question for human PO"
  ],
  "implementation_notes": "Brief guidance for developer agent"
}

If user request is unclear, generate partial story and populate escalations[] with specific questions.
"""


# ═══════════════════════════════════════════════════════════════════════════
# PRODUCT OWNER AGENT
# ═══════════════════════════════════════════════════════════════════════════


class ProductOwnerAgent:
    """Product Owner Agent for autonomous backlog refinement"""

    def __init__(self, backlog_file: str = "skills/backlog.json"):
        self.client = create_llm_client()
        self.backlog_file = Path(backlog_file)
        self.backlog = self._load_backlog()
        self.velocity_history = self._load_velocity_history()

    def _load_backlog(self) -> dict[str, Any]:
        """Load existing backlog or create new"""
        if self.backlog_file.exists():
            with open(self.backlog_file) as f:
                return json.load(f)
        return {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "stories": [],
            "escalations": [],
        }

    def _load_velocity_history(self) -> dict[str, float]:
        """Load historical velocity data for estimation"""
        # From AGENT_VELOCITY_ANALYSIS.md
        return {
            "hours_per_story_point": 2.8,
            "quality_buffer": 0.4,  # 40% buffer for testing/docs/quality
            "recent_velocity": 13,  # Sprint 7 capacity
        }

    def parse_user_request(self, request: str) -> dict[str, Any]:
        """Parse user request into structured user story with AC"""
        print(f"🔄 PO Agent: Parsing user request...")
        print(f"   Request: {request[:80]}{'...' if len(request) > 80 else ''}")

        prompt = f"""User Request:
{request}

Generate a well-formed user story with acceptance criteria following the format specified above.
Consider historical context from similar stories in this quality engineering project.

{PO_AGENT_PROMPT}"""

        response_text = call_llm(
            self.client,
            "",  # System prompt embedded in PO_AGENT_PROMPT
            prompt,
            max_tokens=2000,
        )

        # Parse JSON from response
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end > start:
                story = json.loads(response_text[start:end])
            else:
                print("   ⚠ Could not parse story JSON")
                return self._create_error_story(request, "JSON parse failed")
        except json.JSONDecodeError as e:
            print(f"   ⚠ JSON parse error: {e}")
            return self._create_error_story(request, f"JSON error: {e}")

        # Add metadata
        story["created"] = datetime.now().isoformat()
        story["status"] = "backlog"
        story["request"] = request

        # Validate story structure
        if not self._validate_story(story):
            print("   ⚠ Story validation failed")
            return self._create_error_story(request, "Validation failed")

        print(f"   ✓ Generated story: {story.get('user_story', 'Unknown')[:60]}...")
        print(f"   ✓ AC count: {len(story.get('acceptance_criteria', []))}")
        print(f"   ✓ Story points: {story.get('story_points', '?')}")

        if story.get("escalations"):
            print(f"   ⚠ Escalations: {len(story['escalations'])} questions for human PO")

        return story

    def _validate_story(self, story: dict[str, Any]) -> bool:
        """Validate story has required fields"""
        required = ["user_story", "acceptance_criteria", "story_points"]
        for field in required:
            if field not in story:
                return False

        # Validate AC count (3-7)
        ac_count = len(story.get("acceptance_criteria", []))
        if ac_count < 3 or ac_count > 7:
            print(f"   ⚠ AC count {ac_count} outside 3-7 range")
            return False

        # Validate story points (1, 2, 3, 5, 8, 13)
        valid_points = [1, 2, 3, 5, 8, 13]
        if story.get("story_points") not in valid_points:
            print(
                f"   ⚠ Story points {story.get('story_points')} not in {valid_points}"
            )
            return False

        return True

    def _create_error_story(self, request: str, error: str) -> dict[str, Any]:
        """Create error story for escalation"""
        return {
            "user_story": f"ERROR: Could not parse request: {request[:50]}...",
            "acceptance_criteria": ["[ ] Manual review required"],
            "story_points": 0,
            "estimation_confidence": "none",
            "quality_requirements": {},
            "priority": "P0",
            "escalations": [f"PO Agent failed: {error}"],
            "request": request,
            "created": datetime.now().isoformat(),
            "status": "escalation",
        }

    def generate_acceptance_criteria(
        self, user_story: str, additional_context: str = ""
    ) -> list[str]:
        """Generate acceptance criteria for existing user story"""
        print(f"📋 PO Agent: Generating acceptance criteria...")

        prompt = f"""User Story:
{user_story}

Additional Context:
{additional_context}

Generate 3-7 testable acceptance criteria in Given/When/Then format.
Include quality requirements.

Return JSON array of strings:
["[ ] Given X, When Y, Then Z", "[ ] Quality: ..."]"""

        response_text = call_llm(
            self.client, PO_AGENT_PROMPT, prompt, max_tokens=1000
        )

        try:
            start = response_text.find("[")
            end = response_text.rfind("]") + 1
            if start != -1 and end > start:
                criteria = json.loads(response_text[start:end])
                print(f"   ✓ Generated {len(criteria)} acceptance criteria")
                return criteria
            else:
                print("   ⚠ Could not parse AC JSON")
                return [
                    "[ ] Manual acceptance criteria required - generation failed"
                ]
        except json.JSONDecodeError as e:
            print(f"   ⚠ JSON parse error: {e}")
            return ["[ ] Manual acceptance criteria required - JSON parse error"]

    def estimate_story_points(
        self, user_story: str, acceptance_criteria: list[str]
    ) -> tuple[int, str]:
        """Estimate story points using historical velocity"""
        print(f"📊 PO Agent: Estimating story points...")

        # Count AC complexity indicators
        ac_text = " ".join(acceptance_criteria)
        complexity_indicators = {
            "integration": ac_text.lower().count("integration"),
            "validation": ac_text.lower().count("validat"),
            "test": ac_text.lower().count("test"),
            "quality": ac_text.lower().count("quality"),
            "edge": ac_text.lower().count("edge case"),
        }

        total_indicators = sum(complexity_indicators.values())
        ac_count = len(acceptance_criteria)

        # Simple heuristic estimation
        if ac_count <= 3 and total_indicators <= 2:
            points = 1
            confidence = "high"
        elif ac_count <= 4 and total_indicators <= 4:
            points = 2
            confidence = "high"
        elif ac_count <= 5 and total_indicators <= 6:
            points = 3
            confidence = "medium"
        elif ac_count <= 6 and total_indicators <= 8:
            points = 5
            confidence = "medium"
        else:
            points = 8
            confidence = "low"

        hours = points * self.velocity_history["hours_per_story_point"]
        print(f"   ✓ Estimated {points} points ({hours:.1f} hours)")
        print(f"   ✓ Confidence: {confidence}")

        return points, confidence

    def add_to_backlog(self, story: dict[str, Any]) -> None:
        """Add story to backlog file"""
        self.backlog["stories"].append(story)

        # Handle escalations
        if story.get("escalations"):
            for escalation in story["escalations"]:
                self.backlog["escalations"].append(
                    {
                        "story_id": len(self.backlog["stories"]) - 1,
                        "question": escalation,
                        "created": datetime.now().isoformat(),
                        "status": "pending",
                    }
                )

        self._save_backlog()
        print(f"✅ Added story to backlog: {self.backlog_file}")

    def _save_backlog(self) -> None:
        """Persist backlog to disk"""
        self.backlog_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.backlog_file, "w") as f:
            json.dump(self.backlog, f, indent=2)

    def get_backlog_summary(self) -> str:
        """Generate human-readable backlog summary"""
        stories = self.backlog.get("stories", [])
        escalations = self.backlog.get("escalations", [])

        summary = [
            "═" * 60,
            "PRODUCT BACKLOG SUMMARY",
            "═" * 60,
            f"Total Stories: {len(stories)}",
            f"Pending Escalations: {len([e for e in escalations if e['status'] == 'pending'])}",
            "",
            "Stories by Priority:",
        ]

        # Count by priority
        priority_counts = {"P0": 0, "P1": 0, "P2": 0}
        for story in stories:
            priority = story.get("priority", "P2")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        for priority, count in sorted(priority_counts.items()):
            if count > 0:
                summary.append(f"  {priority}: {count} stories")

        # Total story points
        total_points = sum(s.get("story_points", 0) for s in stories)
        summary.append(f"\nTotal Story Points: {total_points}")

        if escalations:
            summary.append("\n" + "─" * 60)
            summary.append("ESCALATIONS (Human PO Review Required):")
            summary.append("─" * 60)
            for esc in escalations:
                if esc["status"] == "pending":
                    story_id = esc["story_id"]
                    summary.append(
                        f"\nStory {story_id}: {stories[story_id].get('user_story', 'Unknown')[:50]}..."
                    )
                    summary.append(f"  ❓ {esc['question']}")

        summary.append("═" * 60)
        return "\n".join(summary)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Product Owner Agent - Autonomous Backlog Refinement"
    )
    parser.add_argument(
        "--request", help="User request to convert into user story"
    )
    parser.add_argument(
        "--backlog",
        default="skills/backlog.json",
        help="Backlog file path (default: skills/backlog.json)",
    )
    parser.add_argument(
        "--summary", action="store_true", help="Show backlog summary"
    )

    args = parser.parse_args()

    agent = ProductOwnerAgent(backlog_file=args.backlog)

    if args.summary:
        print(agent.get_backlog_summary())
        return

    if args.request:
        story = agent.parse_user_request(args.request)
        agent.add_to_backlog(story)
        print("\n" + agent.get_backlog_summary())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
