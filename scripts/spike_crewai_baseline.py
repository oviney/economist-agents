"""Run CrewAI Stage 3 on the same topic as the Agent SDK spike for comparison.

Captures wall time, output size, and stat-audit removals. CrewAI does not
expose per-run cost, so OpenAI usage for this run must be checked against
the OpenAI dashboard manually if the dollar figure is needed.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import orjson

from src.crews.stage3_crew import Stage3Crew


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    topic = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "the productivity paradox of AI coding assistants"
    )
    print(f"Running CrewAI baseline on topic: {topic}")

    start = time.perf_counter()
    crew = Stage3Crew(topic)
    result = crew.kickoff()
    elapsed = time.perf_counter() - start

    out_dir = Path("logs/spike")
    out_dir.mkdir(parents=True, exist_ok=True)
    article = result.get("article", "")
    chart = result.get("chart_data", {})
    (out_dir / "crewai_article.md").write_text(article)
    (out_dir / "crewai_chart.json").write_bytes(
        orjson.dumps(chart, option=orjson.OPT_INDENT_2)
    )
    metrics = {
        "topic": topic,
        "wall_seconds": elapsed,
        "article_chars": len(article),
        "chart_keys": sorted(chart.keys()) if isinstance(chart, dict) else [],
    }
    (out_dir / "crewai_metrics.json").write_bytes(
        orjson.dumps(metrics, option=orjson.OPT_INDENT_2)
    )
    print(f"Baseline complete: {elapsed:.1f}s, {len(article)} chars.")


if __name__ == "__main__":
    main()
