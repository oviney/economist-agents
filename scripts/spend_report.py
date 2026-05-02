"""Pipeline cost and outcome report.

Reads ``logs/agent_sdk_costs.jsonl`` and prints a summary of spend,
success rate, and the most expensive topics.

Usage::

    python scripts/spend_report.py
    python scripts/spend_report.py --since 2026-05-01
    python scripts/spend_report.py --json
    python scripts/spend_report.py --log path/to/other.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

DEFAULT_LOG = Path("logs/agent_sdk_costs.jsonl")


# ---------------------------------------------------------------------------
# T2 — data loading
# ---------------------------------------------------------------------------


def load_log(path: Path) -> list[dict]:
    """Parse a JSONL cost log into a list of run dicts.

    Raises FileNotFoundError when the log does not exist so callers can
    surface a clear error rather than an empty result.
    """
    if not path.exists():
        raise FileNotFoundError(f"Cost log not found: {path}")
    runs = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            runs.append(json.loads(line))
    return runs


# ---------------------------------------------------------------------------
# T6 — date filter
# ---------------------------------------------------------------------------


def filter_since(runs: list[dict], since: str | None) -> list[dict]:
    """Return only runs whose timestamp is on or after *since* (YYYY-MM-DD).

    Passes all runs through when *since* is None.
    """
    if since is None:
        return runs
    cutoff = date.fromisoformat(since)
    return [r for r in runs if date.fromisoformat(r["timestamp"][:10]) >= cutoff]


# ---------------------------------------------------------------------------
# T3 + T4 — aggregation
# ---------------------------------------------------------------------------


@dataclass
class TopicSummary:
    topic: str
    run_count: int
    total_cost_usd: float
    pass_count: int

    @property
    def success_rate(self) -> float:
        return self.pass_count / self.run_count if self.run_count else 0.0


@dataclass
class SpendReport:
    total_runs: int
    total_cost_usd: float
    avg_cost_usd: float
    success_rate: float
    top_topics: list[TopicSummary] = field(default_factory=list)

    # T7 — JSON output
    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d, indent=2)

    # T5 — table output
    def to_table(self) -> str:
        lines: list[str] = []
        lines.append("=" * 56)
        lines.append("  Pipeline Spend Report")
        lines.append("=" * 56)
        lines.append(f"  Total runs   : {self.total_runs}")
        lines.append(f"  Total cost   : ${self.total_cost_usd:.4f}")
        lines.append(f"  Avg cost/run : ${self.avg_cost_usd:.4f}")
        lines.append(f"  Success rate : {self.success_rate:.1%}")
        lines.append("")
        lines.append("  Top topics by cost:")
        lines.append(f"  {'Topic':<32} {'Runs':>4} {'Cost':>8} {'Pass':>5}")
        lines.append("  " + "-" * 52)
        for t in self.top_topics:
            topic_col = t.topic[:31] + "…" if len(t.topic) > 32 else t.topic
            lines.append(
                f"  {topic_col:<32} {t.run_count:>4} "
                f"${t.total_cost_usd:>7.4f} {t.pass_count:>4}/{t.run_count}"
            )
        lines.append("=" * 56)
        return "\n".join(lines)


def aggregate(runs: list[dict], top_n: int = 5) -> SpendReport:
    """Compute global and per-topic stats from a list of run dicts."""
    if not runs:
        return SpendReport(
            total_runs=0,
            total_cost_usd=0.0,
            avg_cost_usd=0.0,
            success_rate=0.0,
            top_topics=[],
        )

    total_cost = sum(r.get("total_cost_usd", 0.0) for r in runs)
    passed = sum(1 for r in runs if r.get("publication_validator_passed", False))

    # Group by topic
    by_topic: dict[str, TopicSummary] = {}
    for r in runs:
        topic = r.get("topic", "unknown")
        if topic not in by_topic:
            by_topic[topic] = TopicSummary(
                topic=topic, run_count=0, total_cost_usd=0.0, pass_count=0
            )
        s = by_topic[topic]
        s.run_count += 1
        s.total_cost_usd += r.get("total_cost_usd", 0.0)
        if r.get("publication_validator_passed", False):
            s.pass_count += 1

    top = sorted(by_topic.values(), key=lambda s: s.total_cost_usd, reverse=True)

    return SpendReport(
        total_runs=len(runs),
        total_cost_usd=total_cost,
        avg_cost_usd=total_cost / len(runs),
        success_rate=passed / len(runs),
        top_topics=top[:top_n],
    )


# ---------------------------------------------------------------------------
# T8 — CLI entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarise pipeline cost log.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=DEFAULT_LOG,
        help=f"Path to JSONL cost log (default: {DEFAULT_LOG})",
    )
    parser.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        default=None,
        help="Only include runs on or after this date",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output as JSON instead of a table",
    )
    args = parser.parse_args()

    try:
        runs = load_log(args.log)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    runs = filter_since(runs, args.since)
    report = aggregate(runs)

    if args.as_json:
        print(report.to_json())
    else:
        print(report.to_table())


if __name__ == "__main__":
    main()
