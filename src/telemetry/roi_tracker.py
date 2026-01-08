"""ROI Tracker - Business Value Telemetry

Logs token costs and human-hour equivalent savings to logs/execution_roi.json
for business ROI validation.

Design Philosophy:
- Minimal overhead (<10ms per LLM call)
- Accurate cost tracking (±1% of actual API charges)
- No PII in logs
- 30-day rotation policy

Author: Economist Agents Team
Sprint: 14, Story: STORY-007
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Model pricing (as of Jan 2026) - USD per 1M tokens
MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
}

# Human-hour benchmarks (hours to complete task manually)
HUMAN_HOUR_BENCHMARKS = {
    "research_agent": 2.0,  # 2 hours for research
    "writer_agent": 3.0,  # 3 hours to write article
    "editor_agent": 1.0,  # 1 hour to edit
    "graphics_agent": 0.5,  # 30 min for charts
}

# Human hourly rate (USD) - QE engineer average
HUMAN_HOURLY_RATE = 75.0


class ROITracker:
    """Track ROI metrics for agent execution.

    Features:
    - Token usage tracking with model-specific pricing
    - Cost calculation accurate to ±1% of API charges
    - Human-hour equivalent savings calculation
    - ROI multiplier (efficiency gain vs manual)
    - Per-agent breakdown
    - Minimal overhead (<10ms per call)

    Usage:
        tracker = ROITracker()

        # Start tracking an execution
        execution_id = tracker.start_execution("research_agent")

        # Log LLM call
        tracker.log_llm_call(
            execution_id=execution_id,
            agent="research_agent",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500
        )

        # End tracking
        tracker.end_execution(execution_id)

        # Get ROI metrics
        metrics = tracker.get_metrics(execution_id)
    """

    def __init__(self, log_file: str = "logs/execution_roi.json"):
        """Initialize ROI tracker.

        Args:
            log_file: Path to JSON log file
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # In-memory execution tracking
        self.active_executions: dict[str, dict[str, Any]] = {}

        # Load existing log
        self._load_log()

    def _load_log(self) -> None:
        """Load existing execution log from disk."""
        if self.log_file.exists():
            with open(self.log_file) as f:
                self.log = json.load(f)
        else:
            self.log = {
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "executions": [],
                "summary": {
                    "total_executions": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "total_human_hours_saved": 0.0,
                    "avg_roi_multiplier": 0.0,
                },
            }
            # Create initial log file
            self._save_log()

    def _save_log(self) -> None:
        """Persist execution log to disk with minimal overhead."""
        start_time = time.perf_counter()

        with open(self.log_file, "w") as f:
            json.dump(self.log, f, indent=2)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        if elapsed_ms > 10:
            # Log warning if overhead exceeds 10ms
            print(f"⚠️  ROI logging overhead: {elapsed_ms:.1f}ms (target: <10ms)")

    def start_execution(self, agent: str, execution_id: str | None = None) -> str:
        """Start tracking a new execution.

        Args:
            agent: Agent name (research_agent, writer_agent, etc.)
            execution_id: Optional custom ID (auto-generated if not provided)

        Returns:
            execution_id: Unique identifier for this execution
        """
        if execution_id is None:
            execution_id = f"{agent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.active_executions[execution_id] = {
            "execution_id": execution_id,
            "agent": agent,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "llm_calls": [],
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "human_hours_equivalent": HUMAN_HOUR_BENCHMARKS.get(agent, 1.0),
            "human_cost_equivalent": HUMAN_HOUR_BENCHMARKS.get(agent, 1.0)
            * HUMAN_HOURLY_RATE,
            "roi_multiplier": 0.0,
        }

        return execution_id

    def log_llm_call(
        self,
        execution_id: str,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an LLM call with token usage.

        Args:
            execution_id: Execution identifier
            agent: Agent name
            model: Model name (e.g., "gpt-4o")
            input_tokens: Input token count
            output_tokens: Output token count
            metadata: Optional metadata (task, stage, etc.)
        """
        start_time = time.perf_counter()

        if execution_id not in self.active_executions:
            raise ValueError(f"Execution {execution_id} not started")

        # Calculate cost
        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        # Log call
        call_record = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": round(total_cost, 6),
            "metadata": metadata or {},
        }

        # Update execution
        execution = self.active_executions[execution_id]
        execution["llm_calls"].append(call_record)
        execution["total_input_tokens"] += input_tokens
        execution["total_output_tokens"] += output_tokens
        execution["total_tokens"] += input_tokens + output_tokens
        execution["total_cost_usd"] += total_cost

        # Check overhead
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        if elapsed_ms > 10:
            print(f"⚠️  ROI logging overhead: {elapsed_ms:.1f}ms (target: <10ms)")

    def end_execution(self, execution_id: str) -> dict[str, Any]:
        """End tracking and calculate final ROI metrics.

        Args:
            execution_id: Execution identifier

        Returns:
            Final execution metrics
        """
        if execution_id not in self.active_executions:
            raise ValueError(f"Execution {execution_id} not found")

        execution = self.active_executions[execution_id]
        execution["end_time"] = datetime.now().isoformat()

        # Calculate ROI multiplier
        if execution["total_cost_usd"] > 0:
            execution["roi_multiplier"] = round(
                execution["human_cost_equivalent"] / execution["total_cost_usd"], 2
            )
        else:
            execution["roi_multiplier"] = 0.0

        # Round final cost
        execution["total_cost_usd"] = round(execution["total_cost_usd"], 4)

        # Add to log
        self.log["executions"].append(execution)

        # Update summary
        self._update_summary()

        # Persist to disk
        self._save_log()

        # Clean up active tracking
        del self.active_executions[execution_id]

        # Rotate old logs (30-day retention)
        self._rotate_logs()

        return execution

    def _update_summary(self) -> None:
        """Update aggregate summary metrics."""
        executions = self.log["executions"]

        if not executions:
            return

        self.log["summary"] = {
            "total_executions": len(executions),
            "total_tokens": sum(e["total_tokens"] for e in executions),
            "total_cost_usd": round(sum(e["total_cost_usd"] for e in executions), 2),
            "total_human_hours_saved": round(
                sum(e["human_hours_equivalent"] for e in executions), 2
            ),
            "total_human_cost_saved": round(
                sum(e["human_cost_equivalent"] for e in executions), 2
            ),
            "avg_roi_multiplier": round(
                sum(e["roi_multiplier"] for e in executions if e["roi_multiplier"] > 0)
                / len(executions),
                2,
            )
            if executions
            else 0.0,
            "last_updated": datetime.now().isoformat(),
        }

    def _rotate_logs(self) -> None:
        """Remove executions older than 30 days."""
        cutoff = datetime.now() - timedelta(days=30)

        self.log["executions"] = [
            e
            for e in self.log["executions"]
            if datetime.fromisoformat(e["start_time"]) > cutoff
        ]

    def get_metrics(self, execution_id: str) -> dict[str, Any] | None:
        """Get metrics for a specific execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Execution metrics or None if not found
        """
        # Check active executions
        if execution_id in self.active_executions:
            return self.active_executions[execution_id]

        # Check completed executions
        for execution in self.log["executions"]:
            if execution["execution_id"] == execution_id:
                return execution

        return None

    def get_agent_summary(self, agent: str) -> dict[str, Any]:
        """Get aggregate metrics for a specific agent.

        Args:
            agent: Agent name

        Returns:
            Aggregate metrics for the agent
        """
        agent_executions = [e for e in self.log["executions"] if e["agent"] == agent]

        if not agent_executions:
            return {
                "agent": agent,
                "total_executions": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_roi_multiplier": 0.0,
            }

        return {
            "agent": agent,
            "total_executions": len(agent_executions),
            "total_tokens": sum(e["total_tokens"] for e in agent_executions),
            "total_cost_usd": round(
                sum(e["total_cost_usd"] for e in agent_executions), 2
            ),
            "total_human_hours_saved": round(
                sum(e["human_hours_equivalent"] for e in agent_executions), 2
            ),
            "avg_roi_multiplier": round(
                sum(e["roi_multiplier"] for e in agent_executions)
                / len(agent_executions),
                2,
            ),
            "avg_tokens_per_execution": round(
                sum(e["total_tokens"] for e in agent_executions)
                / len(agent_executions),
                0,
            ),
        }

    def get_all_agent_summaries(self) -> list[dict[str, Any]]:
        """Get aggregate metrics for all agents.

        Returns:
            List of agent summaries sorted by total cost
        """
        agents = {e["agent"] for e in self.log["executions"]}
        summaries = [self.get_agent_summary(agent) for agent in agents]

        # Sort by total cost descending
        return sorted(summaries, key=lambda x: x["total_cost_usd"], reverse=True)

    def generate_report(self) -> str:
        """Generate human-readable ROI report.

        Returns:
            Formatted report string
        """
        summary = self.log["summary"]
        agent_summaries = self.get_all_agent_summaries()

        report = [
            "=" * 70,
            "ROI TELEMETRY REPORT",
            "=" * 70,
            "",
            "SUMMARY:",
            f"  Total Executions: {summary['total_executions']}",
            f"  Total Tokens: {summary['total_tokens']:,}",
            f"  Total Cost: ${summary['total_cost_usd']:.2f}",
            f"  Human Hours Saved: {summary['total_human_hours_saved']:.1f}h",
            f"  Human Cost Saved: ${summary.get('total_human_cost_saved', 0):.2f}",
            f"  Average ROI Multiplier: {summary['avg_roi_multiplier']}x",
            "",
            "BY AGENT:",
        ]

        for agent_summary in agent_summaries:
            report.extend(
                [
                    f"  {agent_summary['agent']}:",
                    f"    Executions: {agent_summary['total_executions']}",
                    f"    Tokens: {agent_summary['total_tokens']:,}",
                    f"    Cost: ${agent_summary['total_cost_usd']:.2f}",
                    f"    ROI: {agent_summary['avg_roi_multiplier']}x",
                    "",
                ]
            )

        report.append("=" * 70)

        return "\n".join(report)


# Singleton instance for global access
_tracker: ROITracker | None = None


def get_tracker() -> ROITracker:
    """Get the global ROI tracker instance.

    Returns:
        Global ROITracker singleton
    """
    global _tracker
    if _tracker is None:
        _tracker = ROITracker()
    return _tracker
