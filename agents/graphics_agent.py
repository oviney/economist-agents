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
from typing import Any

# Import chart metrics
from chart_metrics import get_metrics_collector


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

    GRAPHICS_AGENT_PROMPT = """You are a data visualization specialist creating Economist-style charts.

═══════════════════════════════════════════════════════════════════════════
LAYOUT ZONES (NO element should cross zone boundaries)
═══════════════════════════════════════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────┐
│ RED BAR ZONE (y: 0.96 - 1.00)                                   │
├─────────────────────────────────────────────────────────────────┤
│ TITLE ZONE (y: 0.85 - 0.94) - Title y=0.90, Subtitle y=0.85    │
├─────────────────────────────────────────────────────────────────┤
│ CHART ZONE (y: 0.15 - 0.78) - Data, gridlines, inline labels   │
├─────────────────────────────────────────────────────────────────┤
│ X-AXIS ZONE (y: 0.08 - 0.14) - ONLY axis labels go here        │
├─────────────────────────────────────────────────────────────────┤
│ SOURCE ZONE (y: 0.01 - 0.06) - Source attribution              │
└─────────────────────────────────────────────────────────────────┘
```

═══════════════════════════════════════════════════════════════════════════
INLINE LABEL RULES (Critical - prevents overlap bugs)
═══════════════════════════════════════════════════════════════════════════

1. Labels go in CLEAR SPACE - never directly on data lines
2. Use xytext offset to push labels away from anchor point
3. For LOW series (near bottom): place label ABOVE the line, in the gap
   between series - NEVER below where it would hit X-axis labels
4. For HIGH series: place label above or use end-of-line position
5. Always check: would this label intrude into the X-axis zone?

OFFSET PATTERNS:
```python
# Label ABOVE a line
ax.annotate('Label', xy=(x, y), xytext=(0, 20), textcoords='offset points', va='bottom')

# Label at END of line (preferred)
ax.annotate('Label', xy=(last_x, last_y), xytext=(10, 0), textcoords='offset points', ha='left')

# For series near y=0: STILL put label above (in clear space between series)
ax.annotate('Low Series', xy=(x, low_y), xytext=(0, 18), textcoords='offset points', va='bottom')
```

═══════════════════════════════════════════════════════════════════════════
COLORS & STYLE
═══════════════════════════════════════════════════════════════════════════

Background: #f1f0e9 (warm beige)
Red bar: #e3120b
Primary line: #17648d (navy)
Secondary: #843844 (burgundy), #51bec7 (teal), #d6ab63 (gold)
Gridlines: #cccccc (horizontal ONLY)
Text: #333333, Gray: #666666, Light gray: #888888

═══════════════════════════════════════════════════════════════════════════
REQUIRED CODE TEMPLATE
═══════════════════════════════════════════════════════════════════════════

```python
fig, ax = plt.subplots(figsize=(8, 5.5))
fig.patch.set_facecolor('#f1f0e9')
ax.set_facecolor('#f1f0e9')

# Plot data...
ax.plot(x, y_high, color='#17648d', linewidth=2.5, marker='o', markersize=6)
ax.plot(x, y_low, color='#843844', linewidth=2.5, marker='s', markersize=6)

# End-of-line value labels
ax.annotate(f'{{y_high[-1]}}%', xy=(x[-1], y_high[-1]), xytext=(10, 0),
            textcoords='offset points', fontsize=11, fontweight='bold',
            color='#17648d', va='center')

# Inline labels - ABOVE their lines, in clear space
ax.annotate('High Series', xy=(x[-2], y_high[-2]), xytext=(-50, 15),
            textcoords='offset points', fontsize=9, color='#17648d',
            ha='center', va='bottom')
# Even for LOW series - put label ABOVE to avoid X-axis zone
ax.annotate('Low Series', xy=(x[3], y_low[3]), xytext=(0, 18),
            textcoords='offset points', fontsize=9, color='#843844',
            ha='center', va='bottom')

# Axes
ax.yaxis.grid(True, color='#cccccc', linewidth=0.5)
ax.xaxis.grid(False)
ax.spines[['top','right','left']].set_visible(False)

# LAYOUT FIRST
plt.tight_layout()
plt.subplots_adjust(top=0.78, bottom=0.12, left=0.08, right=0.88)

# THEN figure elements
rect = mpatches.Rectangle((0, 0.96), 1, 0.04, transform=fig.transFigure,
                            facecolor='#e3120b', edgecolor='none', clip_on=False)
fig.patches.append(rect)

fig.text(0.08, 0.90, 'Title', fontsize=16, fontweight='bold', ...)
fig.text(0.08, 0.85, 'Subtitle', fontsize=11, color='#666666', ...)
fig.text(0.08, 0.03, 'Source: ...', fontsize=8, color='#888888', ...)
```

═══════════════════════════════════════════════════════════════════════════
CHART SPECIFICATION:
{chart_spec}
═══════════════════════════════════════════════════════════════════════════

Generate complete Python code following this template exactly."""

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
