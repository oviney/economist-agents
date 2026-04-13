#!/usr/bin/env python3
"""
Agent Performance Metrics Dashboard (Streamlit)

Visualises quality, cost, and performance metrics stored in data/metrics.db
over time. Run with:

    streamlit run scripts/metrics_dashboard.py

The dashboard requires no API keys. All data is sourced from the local
SQLite database populated by ``scripts/record_metrics.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow ``streamlit run scripts/metrics_dashboard.py`` from any working dir.
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st  # noqa: E402

from scripts.record_metrics import (  # noqa: E402
    compute_summary,
    fetch_all_runs,
    get_db_path,
)
from scripts.token_usage import read_usage_log, summarise_usage  # noqa: E402

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Agent Performance Dashboard",
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_runs() -> list[dict]:
    """Fetch all pipeline runs from the database.

    Returns:
        List of run dicts, newest first.
    """
    db_path = get_db_path()
    if not db_path.exists():
        return []
    return fetch_all_runs(db_path)


# ---------------------------------------------------------------------------
# Dashboard layout
# ---------------------------------------------------------------------------

st.title("📊 Agent Performance Metrics Dashboard")
st.caption(f"Database: `{get_db_path()}`")

runs = _load_runs()

if not runs:
    st.warning(
        "No pipeline runs recorded yet. "
        "Run `python scripts/record_metrics.py --help` to get started."
    )
    st.stop()

# ----- Summary KPIs ---------------------------------------------------------
summary = compute_summary(runs)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Runs", summary["total_runs"])
col2.metric("✅ Published", summary["published_count"])
col3.metric("🔄 Revision", summary["revision_count"])
col4.metric("❌ Failed", summary["failed_count"])
col5.metric("Success Rate", f"{summary['success_rate_pct']:.1f}%")

st.divider()

# ----- Imports deferred so the dashboard still loads without optional libs --
try:
    import pandas as pd  # type: ignore[import]

    _HAS_PANDAS = True
except ImportError:  # pragma: no cover
    _HAS_PANDAS = False

if not _HAS_PANDAS:
    st.error(
        "pandas is required for chart rendering. Install it with `pip install pandas`."
    )
    st.stop()

df = pd.DataFrame(runs)
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
df = df.sort_values("timestamp")

# ----- Quality trend --------------------------------------------------------
st.subheader("📈 Editorial Score Over Time")
score_chart = df.set_index("timestamp")[["editorial_score"]]
st.line_chart(score_chart, use_container_width=True)

# ----- Cost per run ---------------------------------------------------------
st.subheader("💰 Cost per Run (USD)")
cost_chart = df.set_index("timestamp")[["cost_usd"]]
st.bar_chart(cost_chart, use_container_width=True)

# ----- Status breakdown -----------------------------------------------------
st.subheader("📊 Success / Revision / Fail Rates")

status_counts = df["status"].value_counts().reset_index()
status_counts.columns = ["status", "count"]
status_col, _ = st.columns([1, 2])
with status_col:
    st.dataframe(status_counts, use_container_width=True, hide_index=True)

# ----- Per-agent breakdown --------------------------------------------------
st.subheader("🤖 Per-Agent Breakdown")

agent_df = (
    df.groupby("agent_name")
    .agg(
        runs=("run_id", "count"),
        avg_editorial_score=("editorial_score", "mean"),
        avg_cost_usd=("cost_usd", "mean"),
        avg_duration_s=("duration_s", "mean"),
        avg_gates_passed=("gates_passed", "mean"),
    )
    .reset_index()
    .rename(columns={"agent_name": "Agent"})
)

_ROUNDED_COLS = [
    "avg_editorial_score",
    "avg_cost_usd",
    "avg_duration_s",
    "avg_gates_passed",
]

for col in _ROUNDED_COLS:
    agent_df[col] = agent_df[col].round(2)

st.dataframe(agent_df, use_container_width=True, hide_index=True)

# ----- Raw data (expandable) ------------------------------------------------
with st.expander("🗄️ Raw run data"):
    display_df = df.copy()
    display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Token usage section
# ---------------------------------------------------------------------------

st.divider()
st.subheader("🪙 OpenAI Token Usage (cumulative)")

_token_records = read_usage_log()
if not _token_records:
    st.info(
        "No token-usage records found. "
        "Records are written to `~/.economist-agents/token-usage.jsonl` "
        "whenever `llm_client.call_llm` is invoked."
    )
else:
    _by_model = summarise_usage(_token_records)
    _total_cost = sum(s["estimated_cost_usd"] for s in _by_model.values())

    _tok_col1, _tok_col2, _tok_col3 = st.columns(3)
    _tok_col1.metric("Total calls logged", sum(s["calls"] for s in _by_model.values()))
    _tok_col2.metric(
        "Total tokens", f"{sum(s['total_tokens'] for s in _by_model.values()):,}"
    )
    _tok_col3.metric("Est. total cost", f"${_total_cost:.4f}")

    if _HAS_PANDAS:
        _tok_df = pd.DataFrame(
            [
                {
                    "Model": model,
                    "Calls": stats["calls"],
                    "Prompt tokens": stats["prompt_tokens"],
                    "Completion tokens": stats["completion_tokens"],
                    "Total tokens": stats["total_tokens"],
                    "Est. cost (USD)": f"${stats['estimated_cost_usd']:.4f}",
                }
                for model, stats in sorted(_by_model.items())
            ]
        )
        st.dataframe(_tok_df, use_container_width=True, hide_index=True)

        # Cost-per-model bar chart
        _cost_df = pd.DataFrame(
            [
                {"Model": model, "Est. cost (USD)": stats["estimated_cost_usd"]}
                for model, stats in sorted(_by_model.items())
            ]
        ).set_index("Model")
        st.bar_chart(_cost_df, use_container_width=True)
