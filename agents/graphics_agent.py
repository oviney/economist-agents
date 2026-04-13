#!/usr/bin/env python3
"""
Graphics Agent - Economist-Style Chart Generation

Extracts the Graphics Agent from economist_agent.py for better modularity and testing.
Generates Economist-style data visualizations with strict zone boundary enforcement.

Design Principles:
- Zone boundary enforcement (red bar, title, chart, x-axis, source)
- Inline labels in clear space (not on data lines)
- Economist color palette (#17648d navy, #843844 burgundy, #e3120b red bar)
- Matplotlib code generation via LLM
- Metrics collection for visual QA tracking
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Add scripts directory to path for agent_loader
_scripts_dir = Path(__file__).parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

# Import chart metrics and agent loader
from agent_loader import (  # noqa: E402
    load_content_agent as _load_content_agent,  # type: ignore
)
from chart_metrics import get_metrics_collector  # type: ignore  # noqa: E402

# Module-level prompt constant loaded from YAML
_graphics_config = _load_content_agent("graphics")
GRAPHICS_AGENT_PROMPT = _graphics_config.system_message


class GraphicsAgent:
    """
    Generates Economist-style charts from specifications.

    Key Features:
    - Generates matplotlib code via LLM
    - Enforces zone boundaries (red bar, title, chart, x-axis, source)
    - Inline labels in clear space
    - Economist color palette
    - Metrics tracking via chart_metrics

    Example:
        >>> agent = GraphicsAgent(llm_client)
        >>> chart_path = agent.generate_chart(
        ...     chart_spec={"title": "AI Adoption", "data": {...}},
        ...     output_path="/path/to/chart.png"
        ... )
    """

    GRAPHICS_AGENT_PROMPT = (
        GRAPHICS_AGENT_PROMPT  # loaded from agents/content_generation/graphics.yaml
    )

    def __init__(self, llm_client):
        """Initialize Graphics Agent with LLM client."""
        self.client = llm_client
        self.metrics = get_metrics_collector()

    def generate_chart(
        self, chart_spec: dict[str, Any], output_path: str, max_tokens: int = 2500
    ) -> str | None:
        """
        Generate Economist-style chart from specification.

        Args:
            chart_spec: Chart specification with title, data, type
            output_path: Path to save generated PNG file
            max_tokens: Maximum tokens for LLM response

        Returns:
            output_path if successful, None otherwise

        Raises:
            ValueError: If chart_spec or output_path invalid
        """
        if not chart_spec:
            print("📈 Graphics Agent: No chart data provided, skipping...")
            return None

        # Input validation
        if not isinstance(chart_spec, dict):
            raise ValueError(
                "[GRAPHICS_AGENT] Invalid chart_spec. Expected dict, "
                f"got: {type(chart_spec).__name__}"
            )

        required_fields = ["title", "data"]
        missing = [f for f in required_fields if f not in chart_spec]
        if missing:
            raise ValueError(
                f"[GRAPHICS_AGENT] Chart spec missing required fields: {missing}"
            )

        if not output_path or not isinstance(output_path, str):
            raise ValueError(
                "[GRAPHICS_AGENT] Invalid output_path. Expected non-empty string, "
                f"got: {type(output_path).__name__}"
            )

        print(
            f"📈 Graphics Agent: Creating visualization '{chart_spec.get('title', 'Untitled')[:40]}...'"
        )

        # Start metrics collection
        chart_record = self.metrics.start_chart(
            chart_spec.get("title", "Untitled"), chart_spec
        )

        try:
            # Generate matplotlib code via LLM
            code = self._generate_matplotlib_code(chart_spec, max_tokens)

            # Execute code to create chart
            success = self._execute_matplotlib_code(code, output_path)

            if success:
                print(f"   ✓ Chart saved to {output_path}")
                self.metrics.record_generation(chart_record, success=True)
                return output_path
            else:
                return None

        except Exception as e:
            error_msg = str(e)
            print(f"   ⚠ Chart generation error: {error_msg}")
            self.metrics.record_generation(chart_record, success=False, error=error_msg)
            return None

    def _generate_matplotlib_code(
        self, chart_spec: dict[str, Any], max_tokens: int
    ) -> str:
        """Generate matplotlib code via LLM."""
        from llm_client import call_llm

        prompt = self.GRAPHICS_AGENT_PROMPT.format(
            chart_spec=json.dumps(chart_spec, indent=2)
        )

        code = call_llm(
            self.client,
            prompt,
            "Generate the matplotlib code.",
            max_tokens=max_tokens,
        )

        # Extract code from markdown blocks if present
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]

        return code

    def _execute_matplotlib_code(self, code: str, output_path: str) -> bool:
        """
        Execute matplotlib code to generate chart.

        Args:
            code: Python code string to execute
            output_path: Path to save chart PNG

        Returns:
            True if successful, False otherwise
        """
        # Ensure savefig with correct parameters
        if "plt.savefig" not in code:
            code += f"\nplt.savefig('{output_path}', dpi=300, bbox_inches='tight', facecolor='#f1f0e9')"
        else:
            code = re.sub(
                r"plt\.savefig\([^)]+\)",
                f"plt.savefig('{output_path}', dpi=300, bbox_inches='tight', facecolor='#f1f0e9')",
                code,
            )

        # Write code to temp script
        temp_script = "/tmp/chart_gen.py"
        with open(temp_script, "w") as f:
            f.write("import matplotlib\nmatplotlib.use('Agg')\n")
            f.write(
                "import matplotlib.pyplot as plt\n"
                "import matplotlib.patches as mpatches\n"
                "import numpy as np\n"
            )
            f.write(code)

        # Execute script
        result = subprocess.run(
            [sys.executable, temp_script], capture_output=True, text=True
        )

        if result.returncode == 0:
            return True
        else:
            error_msg = result.stderr[:200]
            print(f"   ⚠ Chart generation failed: {error_msg}")

            # Record failure in chart record
            if (
                hasattr(self.metrics, "current_session")
                and self.metrics.current_session["charts"]
            ):
                chart_record = self.metrics.current_session["charts"][-1]
                self.metrics.record_generation(
                    chart_record, success=False, error=error_msg
                )

            return False


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════


def run_graphics_agent(client, chart_spec: dict, output_path: str) -> str | None:
    """
    Backward-compatible wrapper for Graphics Agent.

    Maintains 100% compatibility with economist_agent.py usage.

    Args:
        client: LLM client instance
        chart_spec: Chart specification dict
        output_path: Path to save chart PNG

    Returns:
        output_path if successful, None otherwise
    """
    agent = GraphicsAgent(client)
    return agent.generate_chart(chart_spec, output_path)


if __name__ == "__main__":
    print("Graphics Agent - Economist-Style Chart Generation")
    print("=" * 70)
    print("\nUsage:")
    print("  from agents.graphics_agent import GraphicsAgent")
    print("  agent = GraphicsAgent(llm_client)")
    print("  chart_path = agent.generate_chart(chart_spec, output_path)")
