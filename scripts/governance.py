#!/usr/bin/env python3
"""
Governance and Human Review System

Adds transparency, approval gates, and decision tracking to the agent pipeline.

Features:
- Saves all agent outputs for review
- Interactive approval gates between stages
- Decision tracking and audit logs
- Summary reports for human oversight
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


class GovernanceTracker:
    """Tracks agent decisions and enables human review"""

    def __init__(self, output_dir: str = "output/governance"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.output_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.decisions = []
        self.agent_outputs = {}

    def log_agent_output(self, agent_name: str, output: Any, metadata: dict = None):
        """Save agent output for review"""
        timestamp = datetime.now().isoformat()

        # Save to session directory
        output_file = self.session_dir / f"{agent_name}.json"
        data = {
            "agent": agent_name,
            "timestamp": timestamp,
            "output": output,
            "metadata": metadata or {},
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

        self.agent_outputs[agent_name] = data

        print(f"   📁 Saved {agent_name} output: {output_file}")

    def request_approval(self, stage: str, summary: str, details: dict = None) -> bool:
        """Interactive approval gate"""
        print("\n" + "=" * 70)
        print(f"🚦 APPROVAL GATE: {stage}")
        print("=" * 70)
        print(f"\n{summary}\n")

        if details:
            print("Details:")
            for key, value in details.items():
                print(f"  • {key}: {value}")
            print()

        # Show review file location
        if stage.lower().replace(" ", "_") in [a.lower() for a in self.agent_outputs]:
            agent_key = [
                k
                for k in self.agent_outputs.keys()
                if k.lower() == stage.lower().replace(" ", "_")
            ][0]
            print(f"📄 Review file: {self.session_dir / f'{agent_key}.json'}")
            print()

        response = input("Approve and continue? [Y/n/skip-all]: ").strip().lower()

        decision = {
            "stage": stage,
            "timestamp": datetime.now().isoformat(),
            "approved": response in ["", "y", "yes"],
            "skip_all": response == "skip-all",
        }
        self.decisions.append(decision)

        if response == "skip-all":
            return True  # Caller should check self.skip_approvals

        return decision["approved"]

    def log_decision(
        self, decision_type: str, choice: str, rationale: str, data: dict = None
    ):
        """Log a decision for audit trail"""
        decision = {
            "type": decision_type,
            "choice": choice,
            "rationale": rationale,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
        }
        self.decisions.append(decision)

        # Save to decisions log
        decisions_file = self.session_dir / "decisions.jsonl"
        with open(decisions_file, "a") as f:
            f.write(json.dumps(decision, default=str) + "\n")

    def generate_report(self, output_file: str | None = None) -> str:
        """Generate human-readable governance report"""
        if output_file is None:
            output_file = str(self.session_dir / "governance_report.md")

        report_lines = [
            "# Governance Report",
            f"**Session**: {self.session_id}",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## Agent Outputs",
            "",
        ]

        for agent_name, data in self.agent_outputs.items():
            report_lines.append(f"### {agent_name.replace('_', ' ').title()}")
            report_lines.append(f"**Timestamp**: {data['timestamp']}")
            report_lines.append(f"**Output File**: `{agent_name}.json`")

            # Add summary based on agent type
            if "metadata" in data and data["metadata"]:
                report_lines.append("\n**Metadata**:")
                for key, value in data["metadata"].items():
                    report_lines.append(f"- {key}: {value}")

            report_lines.append("")

        report_lines.extend(["## Decisions", ""])

        for decision in self.decisions:
            if "stage" in decision:
                # Approval decision
                status = "✅ Approved" if decision["approved"] else "❌ Rejected"
                report_lines.append(f"### {decision['stage']}")
                report_lines.append(f"**Status**: {status}")
                report_lines.append(f"**Time**: {decision['timestamp']}")
            elif "type" in decision:
                # Regular decision
                report_lines.append(f"### {decision['type']}")
                report_lines.append(f"**Choice**: {decision['choice']}")
                report_lines.append(f"**Rationale**: {decision['rationale']}")
                report_lines.append(f"**Time**: {decision['timestamp']}")

            report_lines.append("")

        report_lines.extend(
            [
                "---",
                "",
                f"**Session Directory**: `{self.session_dir}`",
                "",
                "All agent outputs and decisions are saved in this directory for audit and review.",
            ]
        )

        report_content = "\n".join(report_lines)

        with open(output_file, "w") as f:
            f.write(report_content)

        print(f"\n📊 Governance report: {output_file}")

        return report_content


class InteractiveMode:
    """Helper for interactive review and editing"""

    @staticmethod
    def review_and_edit(content: str, content_type: str = "text") -> str:
        """Allow user to review and optionally edit content"""
        print("\n" + "=" * 70)
        print(f"📝 REVIEW: {content_type}")
        print("=" * 70)
        print("\nContent preview (first 500 chars):")
        print("-" * 70)
        print(content[:500])
        if len(content) > 500:
            print(f"\n... ({len(content) - 500} more characters)")
        print("-" * 70)
        print()

        response = input("Options: [c]ontinue, [e]dit, [r]eject: ").strip().lower()

        if response == "e":
            print("\nEnter your edits (press Ctrl+D when done):")
            print("Original content will be shown in your editor...")

            # Save to temp file for editing
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(content)
                temp_path = f.name

            # Open in editor
            editor = os.environ.get("EDITOR", "nano")
            os.system(f"{editor} {temp_path}")

            # Read edited content
            with open(temp_path) as f:
                edited_content = f.read()

            os.unlink(temp_path)
            print("✓ Edits applied")
            return edited_content

        elif response == "r":
            raise ValueError("Content rejected by human reviewer")

        return content

    @staticmethod
    def select_option(prompt: str, options: list) -> int:
        """Present options and get selection"""
        print("\n" + prompt)
        for i, option in enumerate(options, 1):
            print(f"  {i}. {option}")

        while True:
            try:
                choice = input(f"\nSelect option [1-{len(options)}]: ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    return idx
                print(f"Please enter a number between 1 and {len(options)}")
            except (ValueError, KeyboardInterrupt):
                print("Invalid input. Please try again.")


def create_governance_tracker(output_dir: str = None) -> GovernanceTracker:
    """Factory function for governance tracker"""
    if output_dir is None:
        output_dir = os.environ.get("GOVERNANCE_DIR", "output/governance")
    return GovernanceTracker(output_dir)


if __name__ == "__main__":
    # Demo usage
    tracker = create_governance_tracker()

    # Log some sample outputs
    tracker.log_agent_output(
        "research_agent",
        {"data_points": 5, "verified": 4},
        metadata={"topic": "Self-Healing Tests"},
    )

    # Request approval
    approved = tracker.request_approval(
        "Research Phase",
        "Research agent found 5 data points (4 verified)",
        {"unverified": 1, "sources": ["Capgemini", "TestGuild"]},
    )

    if approved:
        tracker.log_decision(
            "research_approval",
            "approved",
            "Data quality acceptable for article generation",
        )

    # Generate report
    report = tracker.generate_report()
    print("\n" + report)
