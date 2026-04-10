#!/usr/bin/env python3
"""
OpenAI Token Usage Logger

Captures token consumption and estimated cost for every LLM API call.
Usage data is appended to ~/.economist-agents/token-usage.jsonl and a
summary line is printed to stdout.

Cost estimates are defined as module-level constants to make pricing
updates easy.

Usage:
    from token_usage import log_token_usage

    log_token_usage(
        model="gpt-4o",
        prompt_tokens=1240,
        completion_tokens=387,
        total_tokens=1627,
    )
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pricing constants (USD per 1 000 000 tokens) — update when OpenAI changes
# rates.  Using April 2026 list prices.
# ---------------------------------------------------------------------------

#: Pricing table: model -> (prompt $/1M, completion $/1M)
MODEL_COSTS: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4-turbo-preview": (10.00, 30.00),
    # Fallback for unknown models – use gpt-4o rates as a conservative default
    "default": (2.50, 10.00),
}

# Path where JSONL usage records are written
_DEFAULT_LOG_DIR = Path.home() / ".economist-agents"
_DEFAULT_LOG_FILE = _DEFAULT_LOG_DIR / "token-usage.jsonl"


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost for a single API call.

    Args:
        model: OpenAI model name (e.g. ``"gpt-4o"``).
        prompt_tokens: Number of prompt tokens consumed.
        completion_tokens: Number of completion tokens generated.

    Returns:
        Estimated cost in USD, rounded to six decimal places.
    """
    prompt_rate, completion_rate = MODEL_COSTS.get(model, MODEL_COSTS["default"])
    cost = (
        prompt_tokens * prompt_rate + completion_tokens * completion_rate
    ) / 1_000_000
    return round(cost, 6)


def log_token_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    log_file: Path | None = None,
) -> float:
    """Log token usage for a single LLM API call.

    Appends a JSONL record to *log_file* (defaults to
    ``~/.economist-agents/token-usage.jsonl``) and prints a one-line
    summary to stdout.

    Args:
        model: OpenAI model name used for the call.
        prompt_tokens: Prompt tokens consumed.
        completion_tokens: Completion tokens generated.
        total_tokens: Total tokens (prompt + completion).
        log_file: Override the default JSONL log path (mainly for testing).

    Returns:
        Estimated cost in USD for this call.
    """
    import orjson  # noqa: PLC0415 — deferred so module loads without orjson

    cost = estimate_cost(model, prompt_tokens, completion_tokens)

    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": cost,
    }

    # Print summary line
    print(
        f"[token-usage] {model}  "
        f"prompt={prompt_tokens}  "
        f"completion={completion_tokens}  "
        f"total={total_tokens}  "
        f"est_cost=${cost:.3f}"
    )

    # Persist to JSONL log
    target = log_file if log_file is not None else _DEFAULT_LOG_FILE
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("ab") as fh:
            fh.write(orjson.dumps(record) + b"\n")
    except OSError as exc:
        logger.warning("Could not write token-usage log to %s: %s", target, exc)

    return cost


def read_usage_log(log_file: Path | None = None) -> list[dict]:
    """Read all token-usage records from the JSONL log.

    Args:
        log_file: Override the default JSONL log path.

    Returns:
        List of usage record dicts, in append order (oldest first).
    """
    import orjson  # noqa: PLC0415

    target = log_file if log_file is not None else _DEFAULT_LOG_FILE
    if not target.exists():
        return []

    records: list[dict] = []
    try:
        with target.open("rb") as fh:
            for raw in fh:
                raw = raw.strip()
                if raw:
                    records.append(orjson.loads(raw))
    except OSError as exc:
        logger.warning("Could not read token-usage log %s: %s", target, exc)
    return records


def summarise_usage(records: list[dict]) -> dict:
    """Aggregate token-usage records by model.

    Args:
        records: List of records as returned by :func:`read_usage_log`.

    Returns:
        Dict mapping model name to aggregated stats::

            {
                "gpt-4o": {
                    "calls": 3,
                    "prompt_tokens": 3720,
                    "completion_tokens": 1161,
                    "total_tokens": 4881,
                    "estimated_cost_usd": 0.042,
                }
            }
    """
    totals: dict[str, dict] = {}
    for rec in records:
        model = rec.get("model", "unknown")
        entry = totals.setdefault(
            model,
            {
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
            },
        )
        entry["calls"] += 1
        entry["prompt_tokens"] += rec.get("prompt_tokens", 0)
        entry["completion_tokens"] += rec.get("completion_tokens", 0)
        entry["total_tokens"] += rec.get("total_tokens", 0)
        entry["estimated_cost_usd"] = round(
            entry["estimated_cost_usd"] + rec.get("estimated_cost_usd", 0.0), 6
        )
    return totals


def print_ci_summary(log_file: Path | None = None) -> None:
    """Write a Markdown token-usage table to ``$GITHUB_STEP_SUMMARY``.

    If ``GITHUB_STEP_SUMMARY`` is not set this function is a no-op.

    Args:
        log_file: Override the default JSONL log path.
    """
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    records = read_usage_log(log_file)
    if not records:
        return

    by_model = summarise_usage(records)

    lines = [
        "## OpenAI Token Usage (this run)",
        "",
        "| Model | Calls | Prompt tokens | Completion tokens | Est. cost |",
        "|-------|-------|--------------|-------------------|-----------|",
    ]
    for model, stats in sorted(by_model.items()):
        lines.append(
            f"| {model} "
            f"| {stats['calls']:,} "
            f"| {stats['prompt_tokens']:,} "
            f"| {stats['completion_tokens']:,} "
            f"| ${stats['estimated_cost_usd']:.4f} |"
        )

    total_cost = sum(s["estimated_cost_usd"] for s in by_model.values())
    lines += ["", f"**Total estimated cost: ${total_cost:.4f}**", ""]

    try:
        with open(summary_path, "a") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError as exc:
        logger.warning("Could not write to GITHUB_STEP_SUMMARY: %s", exc)


if __name__ == "__main__":  # pragma: no cover
    # Quick smoke-test / manual inspection helper
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        records = read_usage_log()
        by_model = summarise_usage(records)
        if not by_model:
            print("No token-usage records found.")
        else:
            print(
                f"{'Model':<20} {'Calls':>6} {'Prompt':>10} {'Completion':>12} {'Cost':>10}"
            )
            print("-" * 64)
            for model, stats in sorted(by_model.items()):
                print(
                    f"{model:<20} "
                    f"{stats['calls']:>6,} "
                    f"{stats['prompt_tokens']:>10,} "
                    f"{stats['completion_tokens']:>12,} "
                    f"${stats['estimated_cost_usd']:>9.4f}"
                )
    else:
        # Demo log call
        log_token_usage("gpt-4o", 1240, 387, 1627)
