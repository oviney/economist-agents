#!/usr/bin/env python3
"""
Visual QA Agent

Validates Economist-style charts against visual quality standards.
Catches rendering bugs like overlapping text, clipped elements, and style violations.

Quality Gates:
1. LAYOUT - No overlapping elements, proper spacing
2. TYPOGRAPHY - Text readable, properly positioned
3. STYLE - Economist brand compliance (red bar, colors, gridlines)
4. DATA - Labels present, values visible
5. EXPORT - Resolution, format, file integrity
"""

import base64
import json
import os
from pathlib import Path

import anthropic

# ═══════════════════════════════════════════════════════════════════════════
# VISUAL QA PROMPT
# ═══════════════════════════════════════════════════════════════════════════

VISUAL_QA_PROMPT = """You are a Visual QA specialist reviewing an Economist-style chart for publication.

═══════════════════════════════════════════════════════════════════════════
QUALITY GATES - Each must PASS or chart is rejected
═══════════════════════════════════════════════════════════════════════════

GATE 1: LAYOUT INTEGRITY
□ Red bar at top is fully visible (not clipped)?
□ Title is BELOW the red bar with clear spacing (≥10px visual gap)?
□ No text overlapping other text?
□ No text overlapping data lines or points?
□ No elements clipped at edges?
□ Source line visible at bottom?

GATE 2: TYPOGRAPHY
□ Title is bold and clearly readable?
□ Subtitle is smaller than title and gray?
□ Axis labels are legible?
□ Data labels at end of lines are visible and not overlapping?
□ Inline series labels (if present) don't overlap the lines they describe?

GATE 3: ECONOMIST STYLE COMPLIANCE
□ Red bar present at top (#e3120b or similar red)?
□ Background is warm beige/cream (not white, not gray)?
□ Only horizontal gridlines (no vertical)?
□ No chart border/frame?
□ Colors from approved palette (navy, burgundy, teal, gold)?

GATE 4: DATA INTEGRITY
□ All data points visible?
□ Line/bar values appear reasonable (no obvious rendering errors)?
□ End-of-line percentage labels present and readable?
□ Y-axis starts at zero (unless justified)?

GATE 5: EXPORT QUALITY
□ Image is sharp (not blurry or pixelated)?
□ Aspect ratio looks correct (not stretched/squashed)?
□ No rendering artifacts or glitches?

═══════════════════════════════════════════════════════════════════════════
COMMON BUGS TO WATCH FOR
═══════════════════════════════════════════════════════════════════════════

These are bugs we've seen before - check carefully:

1. TITLE/RED BAR OVERLAP
   - Title text colliding with or partially hidden by the red bar
   - Fix: Title y-position must be ≤0.90 if red bar is at 0.96-1.0

2. INLINE LABEL/LINE OVERLAP
   - Series labels ("AI adoption") sitting directly ON the data line
   - Text should NOT intersect or touch the line it describes
   - Labels should be clearly ABOVE or BELOW the line with visible gap
   - Fix: Use xytext offset — e.g., (0, 15) for above, (0, -25) for below

3. CLIPPED ELEMENTS
   - Red bar cut off at top
   - Source line cut off at bottom
   - End-of-line labels cut off at right edge
   - Fix: Adjust figure margins or bbox_inches

4. GRIDLINE ERRORS
   - Vertical gridlines present (should be horizontal only)
   - Gridlines too dark or too prominent
   - Fix: ax.xaxis.grid(False), lighter gridline color

5. LEGEND BOX
   - Economist style uses inline labels, NOT legend boxes
   - Fix: Remove legend, add text annotations near lines

═══════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════

Respond with JSON:
{
  "gates": {
    "layout": {"pass": true/false, "issues": ["issue1", "issue2"]},
    "typography": {"pass": true/false, "issues": []},
    "style": {"pass": true/false, "issues": []},
    "data": {"pass": true/false, "issues": []},
    "export": {"pass": true/false, "issues": []}
  },
  "overall_pass": true/false,
  "critical_issues": ["Most important issues that MUST be fixed"],
  "warnings": ["Minor issues that should be fixed if possible"],
  "fix_suggestions": [
    {
      "issue": "Title overlaps red bar",
      "cause": "Title y-position too high",
      "fix": "Change fig.text y-coordinate from 0.95 to 0.90"
    }
  ]
}

Be strict. A chart with ANY critical issue should fail."""


# ═══════════════════════════════════════════════════════════════════════════
# VISUAL QA FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


def load_image_as_base64(image_path: str) -> str:
    """Load an image file and return base64 encoded string."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def get_image_media_type(image_path: str) -> str:
    """Determine media type from file extension."""
    ext = Path(image_path).suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return media_types.get(ext, "image/png")


def run_visual_qa(client, image_path: str, chart_context: dict = None) -> dict:
    """
    Run Visual QA on a chart image.

    Args:
        client: Anthropic client
        image_path: Path to the chart image
        chart_context: Optional dict with title, data info for context

    Returns:
        Dict with gate results, issues, and fix suggestions
    """
    print(f"🔍 Visual QA Agent: Inspecting {image_path}...")

    if not os.path.exists(image_path):
        return {
            "overall_pass": False,
            "critical_issues": [f"Image file not found: {image_path}"],
            "gates": {},
        }

    # Load image
    image_data = load_image_as_base64(image_path)
    media_type = get_image_media_type(image_path)

    # Build context message
    context_msg = ""
    if chart_context:
        context_msg = f"\n\nChart context:\n- Title: {chart_context.get('title', 'Unknown')}\n- Expected series: {chart_context.get('series', 'Unknown')}"

    # Call Claude with vision
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=VISUAL_QA_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": f"Review this chart for visual quality issues.{context_msg}",
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text

    # Parse JSON response
    try:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            result = json.loads(response_text[start:end])
        else:
            result = {
                "overall_pass": False,
                "critical_issues": ["Failed to parse QA response"],
                "raw_response": response_text,
            }
    except json.JSONDecodeError:
        result = {
            "overall_pass": False,
            "critical_issues": ["Failed to parse QA response as JSON"],
            "raw_response": response_text,
        }

    # Print summary
    gates = result.get("gates", {})
    passed = sum(1 for g in gates.values() if g.get("pass", False))
    total = len(gates)

    print(f"   Quality gates: {passed}/{total} passed")

    if result.get("overall_pass"):
        print("   ✓ Chart PASSED visual QA")
    else:
        print("   ✗ Chart FAILED visual QA")
        for issue in result.get("critical_issues", []):
            print(f"     • {issue}")

    return result


def validate_chart_before_publish(image_path: str, auto_fix: bool = False) -> tuple:
    """
    Validate a chart and optionally suggest fixes.

    Returns:
        (passed: bool, result: dict)
    """
    client = anthropic.Anthropic()
    result = run_visual_qa(client, image_path)

    passed = result.get("overall_pass", False)

    if not passed and auto_fix:
        print("\n   Generating fix suggestions...")
        fixes = result.get("fix_suggestions", [])
        if fixes:
            print("   Suggested fixes:")
            for fix in fixes:
                print(f"     Issue: {fix.get('issue')}")
                print(f"     Fix:   {fix.get('fix')}\n")

    return passed, result


# ═══════════════════════════════════════════════════════════════════════════
# ECONOMIST CHART STYLE VALIDATOR (Non-AI, rule-based checks)
# ═══════════════════════════════════════════════════════════════════════════


def validate_chart_file(image_path: str) -> dict:
    """
    Basic file-level validation (no AI required).

    Checks:
    - File exists
    - File size reasonable
    - Image dimensions appropriate
    """
    from PIL import Image

    issues = []

    # File exists
    if not os.path.exists(image_path):
        return {"pass": False, "issues": ["File does not exist"]}

    # File size (should be reasonable for 300 DPI PNG)
    file_size = os.path.getsize(image_path)
    if file_size < 10000:  # Less than 10KB is suspicious
        issues.append(f"File suspiciously small ({file_size} bytes)")
    if file_size > 10000000:  # More than 10MB is too large
        issues.append(f"File too large ({file_size / 1000000:.1f}MB)")

    # Image dimensions
    try:
        with Image.open(image_path) as img:
            width, height = img.size

            # Check minimum dimensions for 300 DPI
            if width < 1200:
                issues.append(f"Width too small ({width}px) for print quality")
            if height < 800:
                issues.append(f"Height too small ({height}px) for print quality")

            # Check aspect ratio (should be roughly 16:10 to 4:3)
            ratio = width / height
            if ratio < 1.0:
                issues.append("Portrait orientation - charts should be landscape")
            if ratio > 2.5:
                issues.append(f"Aspect ratio too wide ({ratio:.1f})")

            # Check color mode
            if img.mode not in ("RGB", "RGBA"):
                issues.append(f"Unexpected color mode: {img.mode}")

    except Exception as e:
        issues.append(f"Failed to read image: {e}")

    return {"pass": len(issues) == 0, "issues": issues}


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════


def main():
    """Run visual QA on a chart from command line or environment."""

    image_path = os.environ.get("CHART_PATH", "")

    if not image_path:
        # Default: check for any PNG in assets/charts
        charts_dir = Path("assets/charts")
        if charts_dir.exists():
            pngs = list(charts_dir.glob("*.png"))
            if pngs:
                image_path = str(pngs[0])

    if not image_path:
        print("No chart to validate. Set CHART_PATH or place PNG in assets/charts/")
        return

    # Run file-level checks first
    print(f"\n📋 Validating: {image_path}\n")

    file_check = validate_chart_file(image_path)
    if not file_check["pass"]:
        print("❌ File validation failed:")
        for issue in file_check["issues"]:
            print(f"   • {issue}")
        return

    print("✓ File validation passed\n")

    # Run AI visual QA
    passed, result = validate_chart_before_publish(image_path, auto_fix=True)

    # Save results
    result_path = image_path.replace(".png", "-qa-report.json")
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n📝 QA report saved to {result_path}")

    # Set GitHub Actions output
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"visual_qa_passed={str(passed).lower()}\n")
            f.write(f"critical_issues={len(result.get('critical_issues', []))}\n")


if __name__ == "__main__":
    main()
