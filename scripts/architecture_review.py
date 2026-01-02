#!/usr/bin/env python3
"""
Architecture Review Agent with Self-Learning Skills

Analyzes codebase architecture and documents patterns, anti-patterns, and design decisions.
Uses Claude-style skills approach to learn and improve architectural understanding over time.

Usage:
    python3 scripts/architecture_review.py --full-review
    python3 scripts/architecture_review.py --focus agent-patterns
    python3 scripts/architecture_review.py --show-skills
"""

import re
import sys
from pathlib import Path

from skills_manager import SkillsManager


class ArchitectureReviewer:
    """Analyzes codebase architecture and learns patterns over time"""

    def __init__(self, project_root: Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent

        self.project_root = Path(project_root)
        self.skills_manager = SkillsManager()
        self.findings = []

    def analyze_all(self):
        """Run comprehensive architecture review"""
        print("\n" + "=" * 70)
        print("🏗️  ARCHITECTURE REVIEW - Learning Mode")
        print("=" * 70 + "\n")

        # 1. Analyze agent architecture
        print("📊 Analyzing agent patterns...")
        self._analyze_agent_architecture()

        # 2. Analyze data flow
        print("🔄 Analyzing data flow...")
        self._analyze_data_flow()

        # 3. Analyze prompt engineering patterns
        print("💬 Analyzing prompt patterns...")
        self._analyze_prompt_patterns()

        # 4. Analyze error handling
        print("🛡️  Analyzing error handling...")
        self._analyze_error_handling()

        # 5. Analyze dependencies
        print("📦 Analyzing dependencies...")
        self._analyze_dependencies()

        # 6. Analyze testing strategy
        print("🧪 Analyzing testing patterns...")
        self._analyze_testing_strategy()

        # Save findings
        self.skills_manager.record_run(len(self.findings), 0)
        self.skills_manager.save()

        print("\n" + "=" * 70)
        print(f"✅ Review complete: {len(self.findings)} patterns learned")
        print("=" * 70 + "\n")

        return self.findings

    def _analyze_agent_architecture(self):
        """Learn patterns from multi-agent system design"""

        # Pattern: Agent system prompts as first-class code
        scripts_dir = self.project_root / "scripts"
        prompt_constants = []

        for py_file in scripts_dir.glob("*.py"):
            with open(py_file) as f:
                content = f.read()
                # Find all caps constants that end in _PROMPT
                prompts = re.findall(
                    r'^([A-Z_]+_PROMPT)\s*=\s*"""', content, re.MULTILINE
                )
                if prompts:
                    prompt_constants.extend([(py_file.name, p) for p in prompts])

        if prompt_constants:
            self.skills_manager.learn_pattern(
                "agent_architecture",
                "prompts_as_code",
                {
                    "severity": "architectural",
                    "pattern": "Agent behavior defined by large prompt constants at top of files",
                    "rationale": "Makes agent logic explicit, versionable, and reviewable",
                    "examples": [f"{f}: {p}" for f, p in prompt_constants[:3]],
                    "check": "When modifying agent behavior, edit prompt constants first",
                    "learned_from": f"Found {len(prompt_constants)} prompt constants across agent files",
                },
            )
            self.findings.append(
                {
                    "category": "agent_architecture",
                    "pattern": "prompts_as_code",
                    "count": len(prompt_constants),
                }
            )

        # Pattern: Persona-driven agents
        editorial_board = scripts_dir / "editorial_board.py"
        if editorial_board.exists():
            with open(editorial_board) as f:
                content = f.read()
                if "BOARD_MEMBERS" in content:
                    # Count personas
                    personas = re.findall(r'"([a-z_]+)":\s*{[^}]*"name":', content)

                    self.skills_manager.learn_pattern(
                        "agent_architecture",
                        "persona_based_voting",
                        {
                            "severity": "architectural",
                            "pattern": "Editorial board uses weighted persona agents for consensus",
                            "rationale": "Simulates diverse stakeholder perspectives with different priorities",
                            "implementation": "Each persona has explicit 'what makes you click/scroll past' criteria",
                            "personas": personas,
                            "check": "New personas must define weight, perspective, and decision criteria",
                            "learned_from": f"Found {len(personas)} personas with weighted voting in editorial_board.py",
                        },
                    )
                    self.findings.append(
                        {
                            "category": "agent_architecture",
                            "pattern": "persona_based_voting",
                            "count": len(personas),
                        }
                    )

        # Pattern: Agent orchestration pattern
        economist_agent = scripts_dir / "economist_agent.py"
        if economist_agent.exists():
            with open(economist_agent) as f:
                content = f.read()
                agent_functions = re.findall(r"def (run_\w+_agent)\(", content)

                if agent_functions:
                    self.skills_manager.learn_pattern(
                        "agent_architecture",
                        "sequential_agent_orchestration",
                        {
                            "severity": "architectural",
                            "pattern": "Pipeline stages executed sequentially with data handoffs",
                            "stages": agent_functions,
                            "rationale": "Each agent specializes in one task, outputs feed next agent",
                            "check": "Ensure each agent validates its inputs and outputs structured data",
                            "learned_from": f"Found {len(agent_functions)} specialized agents in pipeline",
                        },
                    )
                    self.findings.append(
                        {
                            "category": "agent_architecture",
                            "pattern": "sequential_agent_orchestration",
                            "count": len(agent_functions),
                        }
                    )

    def _analyze_data_flow(self):
        """Learn patterns from data flow between pipeline stages"""

        # Pattern: JSON intermediate outputs
        scripts_dir = self.project_root / "scripts"
        json_outputs = []

        for py_file in scripts_dir.glob("*.py"):
            with open(py_file) as f:
                content = f.read()
                # Find JSON file writes
                json_files = re.findall(r'["\']([a-z_]+\.json)["\']', content)
                json_outputs.extend(set(json_files))

        if json_outputs:
            unique_jsons = list(set(json_outputs))
            self.skills_manager.learn_pattern(
                "data_flow",
                "json_intermediate_format",
                {
                    "severity": "architectural",
                    "pattern": "Pipeline stages communicate via JSON files on disk",
                    "files": unique_jsons,
                    "rationale": "Enables inspection between stages, supports manual intervention",
                    "governance": "Humans review JSON outputs before next stage execution",
                    "check": "Validate JSON schema compatibility between producer/consumer",
                    "learned_from": f"Found {len(unique_jsons)} JSON intermediate files",
                },
            )
            self.findings.append(
                {
                    "category": "data_flow",
                    "pattern": "json_intermediate_format",
                    "count": len(unique_jsons),
                }
            )

        # Pattern: Output directory configuration
        for py_file in scripts_dir.glob("*.py"):
            with open(py_file) as f:
                content = f.read()
                if "OUTPUT_DIR" in content and "environ" in content:
                    self.skills_manager.learn_pattern(
                        "data_flow",
                        "configurable_output_paths",
                        {
                            "severity": "architectural",
                            "pattern": "Output paths configurable via environment variables",
                            "rationale": "Supports multiple deployment targets (local, blog repo, CI/CD)",
                            "env_vars": ["OUTPUT_DIR", "ANTHROPIC_API_KEY"],
                            "check": "Provide sensible defaults when env vars not set",
                            "learned_from": "Found OUTPUT_DIR environment variable pattern",
                        },
                    )
                    self.findings.append(
                        {
                            "category": "data_flow",
                            "pattern": "configurable_output_paths",
                            "count": 1,
                        }
                    )
                    break

    def _analyze_prompt_patterns(self):
        """Learn patterns from prompt engineering practices"""

        scripts_dir = self.project_root / "scripts"

        for py_file in scripts_dir.glob("*agent*.py"):
            with open(py_file) as f:
                content = f.read()

                # Pattern: Structured output requirements
                if "OUTPUT STRUCTURE:" in content or "OUTPUT FORMAT:" in content:
                    self.skills_manager.learn_pattern(
                        "prompt_engineering",
                        "structured_output_specification",
                        {
                            "severity": "best_practice",
                            "pattern": "Prompts explicitly define expected JSON output structure",
                            "rationale": "Reduces parsing errors and improves output consistency",
                            "implementation": "Include example JSON schema in system prompt",
                            "check": "Every agent that returns structured data must specify format",
                            "learned_from": f"Found structured output specs in {py_file.name}",
                        },
                    )
                    self.findings.append(
                        {
                            "category": "prompt_engineering",
                            "pattern": "structured_output_specification",
                            "file": py_file.name,
                        }
                    )

                # Pattern: Voice/style constraints
                if "BANNED" in content or "FORBIDDEN" in content:
                    banned_sections = len(re.findall(r"BANNED|FORBIDDEN", content))

                    self.skills_manager.learn_pattern(
                        "prompt_engineering",
                        "explicit_constraint_lists",
                        {
                            "severity": "best_practice",
                            "pattern": "Style constraints explicitly listed as BANNED/FORBIDDEN",
                            "rationale": "Learned from manual editing cycles - codified editorial lessons",
                            "examples": [
                                "BANNED OPENINGS",
                                "BANNED PHRASES",
                                "FORBIDDEN CLOSINGS",
                            ],
                            "check": "Update constraint lists based on editor agent rejections",
                            "learned_from": f"Found {banned_sections} explicit constraint sections in {py_file.name}",
                        },
                    )
                    self.findings.append(
                        {
                            "category": "prompt_engineering",
                            "pattern": "explicit_constraint_lists",
                            "count": banned_sections,
                        }
                    )

    def _analyze_error_handling(self):
        """Learn patterns from error handling approaches"""

        scripts_dir = self.project_root / "scripts"

        # Pattern: Graceful JSON parsing
        json_parse_patterns = 0
        for py_file in scripts_dir.glob("*.py"):
            with open(py_file) as f:
                content = f.read()
                if (
                    "json.loads" in content
                    and "try:" in content
                    and ".find(" in content
                    and ".rfind(" in content
                ):
                    json_parse_patterns += 1

        if json_parse_patterns > 0:
            self.skills_manager.learn_pattern(
                "error_handling",
                "defensive_json_parsing",
                {
                    "severity": "best_practice",
                    "pattern": "Extract JSON from LLM responses with find/rfind before parsing",
                    "rationale": "LLMs may wrap JSON in markdown or explanatory text",
                    "implementation": "Find first '{' and last '}', parse substring",
                    "check": "Always use try/except around json.loads()",
                    "learned_from": f"Found defensive parsing in {json_parse_patterns} files",
                },
            )
            self.findings.append(
                {
                    "category": "error_handling",
                    "pattern": "defensive_json_parsing",
                    "count": json_parse_patterns,
                }
            )

        # Pattern: Unverified claims flagging
        economist_agent = scripts_dir / "economist_agent.py"
        if economist_agent.exists():
            with open(economist_agent) as f:
                content = f.read()
                if "[UNVERIFIED]" in content:
                    self.skills_manager.learn_pattern(
                        "error_handling",
                        "explicit_verification_flags",
                        {
                            "severity": "architectural",
                            "pattern": "Research agent flags unverifiable claims with [UNVERIFIED]",
                            "rationale": "Maintains credibility, prevents false claims in output",
                            "enforcement": "Editor agent rejects articles with [UNVERIFIED] markers",
                            "check": "Never publish content with verification flags",
                            "learned_from": "Found [UNVERIFIED] flagging system in research/editor flow",
                        },
                    )
                    self.findings.append(
                        {
                            "category": "error_handling",
                            "pattern": "explicit_verification_flags",
                            "count": 1,
                        }
                    )

    def _analyze_dependencies(self):
        """Learn patterns from dependency management"""

        # Pattern: External API usage
        scripts_dir = self.project_root / "scripts"
        anthropic_usage = 0

        for py_file in scripts_dir.glob("*.py"):
            with open(py_file) as f:
                content = f.read()
                if "anthropic.Anthropic" in content:
                    anthropic_usage += 1

        if anthropic_usage > 0:
            self.skills_manager.learn_pattern(
                "dependencies",
                "centralized_llm_client",
                {
                    "severity": "architectural",
                    "pattern": "All agents use Anthropic Claude API via shared client",
                    "rationale": "Consistent model selection, easier rate limiting, unified error handling",
                    "model": "claude-sonnet-4-20250514",
                    "check": "Create client once, pass to agents - don't create per-request",
                    "learned_from": f"Found Anthropic client usage in {anthropic_usage} files",
                },
            )
            self.findings.append(
                {
                    "category": "dependencies",
                    "pattern": "centralized_llm_client",
                    "count": anthropic_usage,
                }
            )

        # Pattern: Matplotlib for visualization
        chart_files = list(scripts_dir.glob("*chart*.py"))
        if chart_files:
            with open(chart_files[0]) as f:
                content = f.read()
                if "matplotlib.use('Agg')" in content:
                    self.skills_manager.learn_pattern(
                        "dependencies",
                        "headless_matplotlib_backend",
                        {
                            "severity": "best_practice",
                            "pattern": "Use Agg backend for headless chart generation",
                            "rationale": "Enables chart generation in CI/CD without display",
                            "implementation": "Set matplotlib.use('Agg') before importing pyplot",
                            "check": "Charts must work without X11/display environment",
                            "learned_from": "Found Agg backend configuration in chart generation",
                        },
                    )
                    self.findings.append(
                        {
                            "category": "dependencies",
                            "pattern": "headless_matplotlib_backend",
                            "count": 1,
                        }
                    )

    def _analyze_testing_strategy(self):
        """Learn patterns from testing and validation approaches"""

        # Pattern: Skills-based learning
        skills_files = list(self.project_root.glob("scripts/*skills*.py"))
        if skills_files:
            self.skills_manager.learn_pattern(
                "testing_strategy",
                "continuous_learning_validation",
                {
                    "severity": "architectural",
                    "pattern": "Validation agents learn from each run using skills system",
                    "rationale": "Zero-config improvement, patterns persist across runs",
                    "implementation": "SkillsManager stores patterns in skills/*.json",
                    "categories": [
                        "content_quality",
                        "seo_validation",
                        "link_validation",
                    ],
                    "check": "Call skills_manager.learn_pattern() when new issues discovered",
                    "learned_from": "Found SkillsManager implementation with pattern persistence",
                },
            )
            self.findings.append(
                {
                    "category": "testing_strategy",
                    "pattern": "continuous_learning_validation",
                    "count": len(skills_files),
                }
            )

        # Pattern: Manual quality gates
        scripts_dir = self.project_root / "scripts"
        for py_file in scripts_dir.glob("*.py"):
            with open(py_file) as f:
                content = f.read()
                if "content_queue.json" in content and "board_decision.json" in content:
                    self.skills_manager.learn_pattern(
                        "testing_strategy",
                        "human_review_checkpoints",
                        {
                            "severity": "architectural",
                            "pattern": "Manual review gates between pipeline stages",
                            "checkpoints": [
                                "Review content_queue.json after discovery",
                                "Review board_decision.json after voting",
                                "Review generated article before publish",
                            ],
                            "rationale": "Prevents runaway automation, ensures quality",
                            "check": "Never auto-publish - require explicit human approval",
                            "learned_from": "Found multi-stage review pattern in pipeline",
                        },
                    )
                    self.findings.append(
                        {
                            "category": "testing_strategy",
                            "pattern": "human_review_checkpoints",
                            "count": 1,
                        }
                    )
                    break

    def generate_report(self) -> str:
        """Generate comprehensive architecture report"""
        report = []
        report.append("=" * 70)
        report.append("ARCHITECTURE REVIEW REPORT")
        report.append("=" * 70)
        report.append("")

        # Group findings by category
        by_category = {}
        for finding in self.findings:
            cat = finding["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(finding)

        for category, findings in sorted(by_category.items()):
            report.append(f"\n{category.upper().replace('_', ' ')}")
            report.append("-" * 70)
            for finding in findings:
                pattern = finding["pattern"]
                count = finding.get("count", 1)
                report.append(f"  ✓ {pattern}: {count} instances")

        report.append("\n" + "=" * 70)
        report.append("SKILLS LEARNED")
        report.append("=" * 70)
        report.append(self.skills_manager.export_report())

        return "\n".join(report)

    def export_to_markdown(self, output_path: Path = None):
        """Export architectural knowledge to markdown documentation"""
        if output_path is None:
            output_path = self.project_root / "docs" / "ARCHITECTURE_PATTERNS.md"

        doc = []
        doc.append("# Architectural Patterns (Learned)")
        doc.append("")
        doc.append("This document is auto-generated from architecture review agent.")
        doc.append(
            f"Last updated: {self.skills_manager.skills.get('last_updated', 'Unknown')}"
        )
        doc.append("")

        # Export all learned patterns
        for category, cat_data in self.skills_manager.skills.get("skills", {}).items():
            if not category.startswith("seo_") and not category.startswith("link_"):
                doc.append(f"\n## {category.replace('_', ' ').title()}")
                doc.append("")

                for pattern in cat_data.get("patterns", []):
                    doc.append(f"### {pattern['id'].replace('_', ' ').title()}")
                    doc.append("")
                    doc.append(f"**Pattern:** {pattern.get('pattern', 'N/A')}")
                    doc.append("")

                    if "rationale" in pattern:
                        doc.append(f"**Rationale:** {pattern['rationale']}")
                        doc.append("")

                    if "implementation" in pattern:
                        doc.append(f"**Implementation:** {pattern['implementation']}")
                        doc.append("")

                    if "check" in pattern:
                        doc.append(f"**Quality Check:** {pattern['check']}")
                        doc.append("")

                    if "examples" in pattern:
                        doc.append("**Examples:**")
                        for ex in pattern["examples"]:
                            doc.append(f"- {ex}")
                        doc.append("")

                    doc.append(f"*Severity: {pattern.get('severity', 'unknown')}*")
                    doc.append("")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write("\n".join(doc))

        return output_path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Review architecture and learn patterns"
    )
    parser.add_argument(
        "--full-review", action="store_true", help="Run complete architecture review"
    )
    parser.add_argument(
        "--show-skills", action="store_true", help="Show learned architectural patterns"
    )
    parser.add_argument(
        "--export-docs", action="store_true", help="Export patterns to markdown"
    )
    parser.add_argument(
        "--focus", help="Focus on specific area (agent-patterns, data-flow, etc)"
    )

    args = parser.parse_args()

    reviewer = ArchitectureReviewer()

    if args.show_skills:
        print(reviewer.skills_manager.export_report())
        sys.exit(0)

    if args.full_review:
        reviewer.analyze_all()
        print("\n" + reviewer.generate_report())

        if args.export_docs:
            doc_path = reviewer.export_to_markdown()
            print(f"\n📄 Exported to {doc_path}")

    elif args.focus:
        print(f"Focus area: {args.focus} (not implemented yet)")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
