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
        "pandas is required for chart rendering. "
        "Install it with `pip install pandas`."
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

for col in ["avg_editorial_score", "avg_cost_usd", "avg_duration_s", "avg_gates_passed"]:
    agent_df[col] = agent_df[col].round(2)

st.dataframe(agent_df, use_container_width=True, hide_index=True)

# ----- Raw data (expandable) ------------------------------------------------
with st.expander("🗄️ Raw run data"):
    display_df = df.copy()
    display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(display_df, use_container_width=True, hide_index=True)
