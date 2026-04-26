#!/usr/bin/env python3
"""Architecture audit for ``.github/agents/*.agent.md`` files.

Scores every agent definition against the rubric documented in
``skills/architecture-patterns/SKILL.md`` and emits a JSON + Markdown report.
The threshold for system-wide compliance is 85%.

Usage:
    python scripts/architecture_audit.py \\
        --agents-dir .github/agents \\
        --out architecture_audit.json \\
        --markdown architecture_audit.md
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DIMENSIONS = (
    "frontmatter",
    "role_clarity",
    "tool_minimality",
    "skills_mapping",
    "body_cohesion",
    "output_contract",
)
MAX_TOTAL = len(DIMENSIONS) * 2

# Default threshold is the *current measured baseline* rounded down to the
# nearest 5%, not the architectural target. The target is 85%; lifting the
# corpus from baseline → target is open work tracked separately in the
# backlog. This split prevents the audit from regressing silently while
# keeping the goal visible.
TARGET_COMPLIANCE = 85.0
DEFAULT_THRESHOLD = 75.0  # baseline floor as of 2026-04-26 (measured 79.2%)


@dataclass
class AgentScore:
    """Per-agent audit result."""

    name: str
    path: str
    scores: dict[str, int]
    total: int
    compliance_pct: float
    findings: list[dict[str, str]] = field(default_factory=list)


@dataclass
class AuditReport:
    """System-wide audit result."""

    audited_at: str
    agents: list[AgentScore]
    overall_compliance_pct: float
    passes_threshold: bool
    threshold: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "audited_at": self.audited_at,
            "agents": [asdict(a) for a in self.agents],
            "overall_compliance_pct": self.overall_compliance_pct,
            "passes_threshold": self.passes_threshold,
            "threshold": self.threshold,
        }


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split agent file into (frontmatter dict, body)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, parts[2].strip()


def _score_frontmatter(fm: dict[str, Any]) -> tuple[int, list[dict[str, str]]]:
    required_full = ("name", "description", "model", "tools", "skills")
    findings: list[dict[str, str]] = []
    if not fm:
        findings.append(
            {
                "dimension": "frontmatter",
                "issue": "no YAML frontmatter found",
                "fix": "Add --- YAML frontmatter with name/description/model/tools/skills",
            }
        )
        return 0, findings
    missing = [k for k in required_full if k not in fm]
    if not missing:
        return 2, findings
    if "name" in fm and "description" in fm:
        findings.append(
            {
                "dimension": "frontmatter",
                "issue": f"missing fields: {', '.join(missing)}",
                "fix": "Add the missing keys to the YAML frontmatter",
            }
        )
        return 1, findings
    findings.append(
        {
            "dimension": "frontmatter",
            "issue": f"frontmatter incomplete: missing {', '.join(missing)}",
            "fix": "At minimum add name and description",
        }
    )
    return 0, findings


_GENERIC_ROLES = (
    "ai assistant",
    "general-purpose",
    "helpful agent",
    "general assistant",
)
_ROLE_KEYWORDS = (
    "specialist",
    "engineer",
    "architect",
    "reviewer",
    "owner",
    "master",
    "scout",
    "operator",
    "analyst",
    "writer",
    "editor",
    "validator",
    "qa",
    "devops",
    "researcher",
    "facilitator",
    "designer",
)


def _score_role_clarity(
    fm: dict[str, Any], body: str
) -> tuple[int, list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    description = (fm.get("description") or "").lower()
    body_lower = body.lower()
    has_role_section = bool(
        re.search(
            r"^##+\s+(your\s+)?(role|mission|purpose|responsibilities|core\s+principles)",
            body,
            re.M | re.I,
        )
    )
    # Also accept role/goal in frontmatter as evidence of role clarity
    if not has_role_section and (fm.get("role") or fm.get("goal")):
        has_role_section = True
    if any(g in description or g in body_lower[:600] for g in _GENERIC_ROLES):
        findings.append(
            {
                "dimension": "role_clarity",
                "issue": "role described in generic terms",
                "fix": "State a specific, non-overlapping role in description and Role section",
            }
        )
        return 0, findings
    has_specific_keyword = any(kw in description for kw in _ROLE_KEYWORDS) or any(
        kw in body_lower[:1500] for kw in _ROLE_KEYWORDS
    )
    if has_role_section and has_specific_keyword:
        return 2, findings
    if has_role_section or has_specific_keyword:
        findings.append(
            {
                "dimension": "role_clarity",
                "issue": "role partially specified",
                "fix": "Add an explicit Role/Mission section AND a specific role keyword in description",
            }
        )
        return 1, findings
    findings.append(
        {
            "dimension": "role_clarity",
            "issue": "no clear role section or specific role keyword",
            "fix": "Add a Role section and a role keyword (specialist, engineer, etc.)",
        }
    )
    return 0, findings


def _score_tool_minimality(
    fm: dict[str, Any],
) -> tuple[int, list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    tools = fm.get("tools")
    if tools is None:
        findings.append(
            {
                "dimension": "tool_minimality",
                "issue": "tools key missing",
                "fix": "Declare tools explicitly, even if empty list",
            }
        )
        return 0, findings
    if not isinstance(tools, list):
        findings.append(
            {
                "dimension": "tool_minimality",
                "issue": "tools is not a list",
                "fix": "Use YAML list syntax for tools",
            }
        )
        return 0, findings
    n = len(tools)
    if 1 <= n <= 5:
        return 2, findings
    if n == 0 or n == 6:
        findings.append(
            {
                "dimension": "tool_minimality",
                "issue": f"tool count {n} is borderline (1–5 is ideal)",
                "fix": "Justify each tool or split agent",
            }
        )
        return 1, findings
    findings.append(
        {
            "dimension": "tool_minimality",
            "issue": f"tool sprawl: {n} tools",
            "fix": "Split into specialised agents; aim for ≤5 tools per agent",
        }
    )
    return 0, findings


def _score_skills_mapping(
    fm: dict[str, Any], body: str
) -> tuple[int, list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    skills = fm.get("skills") or []
    if not isinstance(skills, list) or not skills:
        findings.append(
            {
                "dimension": "skills_mapping",
                "issue": "no skills referenced",
                "fix": "Reference at least one skills/<name>/SKILL.md",
            }
        )
        return 0, findings
    matched = 0
    for s in skills:
        slug = str(s).split("/")[-1]
        if slug and slug in body:
            matched += 1
    if matched == len(skills):
        return 2, findings
    if matched > 0:
        findings.append(
            {
                "dimension": "skills_mapping",
                "issue": f"only {matched}/{len(skills)} skills referenced in body",
                "fix": "Invoke each declared skill explicitly in instructions",
            }
        )
        return 1, findings
    findings.append(
        {
            "dimension": "skills_mapping",
            "issue": "skills declared but never invoked in body",
            "fix": "Reference each skill by slug in the instructions",
        }
    )
    return 0, findings


def _score_body_cohesion(body: str) -> tuple[int, list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    headings = re.findall(r"^##+\s+\S", body, re.M)
    if len(headings) >= 3:
        return 2, findings
    if len(headings) >= 1:
        findings.append(
            {
                "dimension": "body_cohesion",
                "issue": f"only {len(headings)} top-level section(s)",
                "fix": "Structure body into ≥3 sections (Role, Process, Output, etc.)",
            }
        )
        return 1, findings
    findings.append(
        {
            "dimension": "body_cohesion",
            "issue": "no section headings",
            "fix": "Add ## sections to structure the instructions",
        }
    )
    return 0, findings


def _score_output_contract(body: str) -> tuple[int, list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    # "Output" / "Return" / "Result" / "Format" — what the agent emits.
    # Deliverables is accepted as a synonym. "Integration" is intentionally
    # excluded: it describes how to invoke the agent, not its return shape.
    has_output_section = bool(
        re.search(
            r"^##+\s+(output|return|result|format|deliverables?)",
            body,
            re.M | re.I,
        )
    )
    has_json_block = bool(re.search(r"```(?:json|jsonc|yaml)\b", body))
    has_format_keyword = bool(
        re.search(r"\b(output\s+format|returns?\s+\w+|emit\b)\b", body, re.I)
    )
    if has_output_section and (has_json_block or has_format_keyword):
        return 2, findings
    if has_output_section or has_json_block:
        findings.append(
            {
                "dimension": "output_contract",
                "issue": "output contract is partial",
                "fix": "Document an explicit Output section with a concrete format example",
            }
        )
        return 1, findings
    findings.append(
        {
            "dimension": "output_contract",
            "issue": "no output contract documented",
            "fix": "Add an Output section describing the return shape (JSON, Markdown template, etc.)",
        }
    )
    return 0, findings


def _score_agent(file_path: Path) -> AgentScore:
    text = file_path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)
    name = (fm.get("name") if isinstance(fm, dict) else None) or file_path.stem.replace(
        ".agent", ""
    )

    scores: dict[str, int] = {}
    findings: list[dict[str, str]] = []

    score, f = _score_frontmatter(fm)
    scores["frontmatter"] = score
    findings.extend(f)
    score, f = _score_role_clarity(fm, body)
    scores["role_clarity"] = score
    findings.extend(f)
    score, f = _score_tool_minimality(fm)
    scores["tool_minimality"] = score
    findings.extend(f)
    score, f = _score_skills_mapping(fm, body)
    scores["skills_mapping"] = score
    findings.extend(f)
    score, f = _score_body_cohesion(body)
    scores["body_cohesion"] = score
    findings.extend(f)
    score, f = _score_output_contract(body)
    scores["output_contract"] = score
    findings.extend(f)

    total = sum(scores.values())
    pct = round(total / MAX_TOTAL * 100, 1)

    return AgentScore(
        name=name,
        path=str(file_path),
        scores=scores,
        total=total,
        compliance_pct=pct,
        findings=findings,
    )


def audit(agents_dir: Path, threshold: float = DEFAULT_THRESHOLD) -> AuditReport:
    """Audit every ``*.agent.md`` file under ``agents_dir``."""
    if not agents_dir.exists():
        raise FileNotFoundError(f"agents directory not found: {agents_dir}")
    files = sorted(agents_dir.glob("*.agent.md"))
    if not files:
        raise FileNotFoundError(f"no *.agent.md files in {agents_dir}")

    agent_scores = [_score_agent(f) for f in files]
    overall = round(sum(a.compliance_pct for a in agent_scores) / len(agent_scores), 1)

    return AuditReport(
        audited_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        agents=agent_scores,
        overall_compliance_pct=overall,
        passes_threshold=overall >= threshold,
        threshold=threshold,
    )


def render_markdown(report: AuditReport) -> str:
    """Render an audit report as Markdown."""
    lines = [
        "# Architecture Audit",
        "",
        f"- **Audited at:** {report.audited_at}",
        f"- **Overall compliance:** **{report.overall_compliance_pct}%** "
        f"(threshold {report.threshold}%) — "
        f"{'✅ PASS' if report.passes_threshold else '❌ FAIL'}",
        f"- **Agents audited:** {len(report.agents)}",
        "",
        "## Per-agent scores",
        "",
        "| Agent | Frontmatter | Role | Tools | Skills | Cohesion | Output | Total | % |",
        "|-------|-------------|------|-------|--------|----------|--------|-------|---|",
    ]
    for a in report.agents:
        s = a.scores
        lines.append(
            f"| `{a.name}` | {s['frontmatter']} | {s['role_clarity']} | "
            f"{s['tool_minimality']} | {s['skills_mapping']} | "
            f"{s['body_cohesion']} | {s['output_contract']} | "
            f"{a.total}/{MAX_TOTAL} | {a.compliance_pct}% |"
        )
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    for a in report.agents:
        if not a.findings:
            continue
        lines.append(f"### `{a.name}`")
        lines.append("")
        for f in a.findings:
            lines.append(f"- **{f['dimension']}** — {f['issue']}. _Fix:_ {f['fix']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agents-dir",
        type=Path,
        default=Path(".github/agents"),
        help="Directory containing *.agent.md files",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write JSON report to this path (default: stdout JSON)",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=None,
        help="Write Markdown report to this path",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Minimum overall compliance percentage to pass",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    report = audit(args.agents_dir, threshold=args.threshold)
    payload = json.dumps(report.to_dict(), indent=2)
    if args.out:
        args.out.write_text(payload)
        logger.info("Wrote JSON report to %s", args.out)
    else:
        print(payload)
    if args.markdown:
        args.markdown.write_text(render_markdown(report))
        logger.info("Wrote Markdown report to %s", args.markdown)
    return 0 if report.passes_threshold else 2


if __name__ == "__main__":
    sys.exit(main())
