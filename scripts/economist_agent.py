#!/usr/bin/env python3
"""
Economist-Style Blog Agent Orchestrator (v3)

Updated with governance and human review system.

Key improvements (v3):
- Interactive approval gates between stages
- All agent outputs saved for review
- Decision tracking and audit logs
- Governance reports for human oversight

Key improvements (v2):
- Writer agent now has explicit "lines to avoid" patterns
- Editor agent has specific quality gates with pass/fail criteria
- Research agent emphasizes source verification
- Added self-critique loop before final output
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Import agent metrics
from agent_metrics import AgentMetrics

# Import automated reviewer
# Import chart metrics
from chart_metrics import get_metrics_collector

# Import featured image generator
from featured_image_agent import generate_featured_image

# Import governance system
from governance import GovernanceTracker

# Import unified LLM client
from llm_client import call_llm, create_llm_client

# Import publication validator
from publication_validator import PublicationValidator
from slugify import slugify

# Import extracted Editor Agent
from agents.editor_agent import run_editor_agent

# Import extracted Graphics Agent
from agents.graphics_agent import run_graphics_agent

# Import extracted Research Agent
from agents.research_agent import run_research_agent

# Import extracted Writer Agent
from agents.writer_agent import run_writer_agent

# Sprint 14 Integration: Flow orchestration, Style Memory RAG, ROI Telemetry
try:
    from src.economist_agents.flow import EconomistContentFlow  # noqa: F401

    FLOW_AVAILABLE = True
except ImportError:
    FLOW_AVAILABLE = False
    print("⚠️  EconomistContentFlow not available - using legacy pipeline")

try:
    from src.tools.style_memory_tool import StyleMemoryTool

    STYLE_MEMORY_AVAILABLE = True
except ImportError:
    STYLE_MEMORY_AVAILABLE = False
    print("⚠️  StyleMemoryTool not available - Editor Agent without RAG")

try:
    from src.telemetry.roi_tracker import ROITracker

    ROI_TRACKER_AVAILABLE = True
except ImportError:
    ROI_TRACKER_AVAILABLE = False
    print("⚠️  ROITracker not available - no ROI telemetry logging")

# ═══════════════════════════════════════════════════════════════════════════
# AGENT SYSTEM PROMPTS (v2 - with codified editorial lessons)
# ═══════════════════════════════════════════════════════════════════════════

# Writer Agent has been extracted to agents/writer_agent.py
# Import: from agents.writer_agent import run_writer_agent
# See: agents/writer_agent.py for WriterAgent class and WRITER_AGENT_PROMPT

# Graphics Agent has been extracted to agents/graphics_agent.py
# Import: from agents.graphics_agent import run_graphics_agent
# See: agents/graphics_agent.py for GraphicsAgent class and GRAPHICS_AGENT_PROMPT

# Editor Agent has been extracted to agents/editor_agent.py
# Import: from agents.editor_agent import run_editor_agent
# See: agents/editor_agent.py for EditorAgent class and EDITOR_AGENT_PROMPT

# ═══════════════════════════════════════════════════════════════════════════
# LEGACY PROMPTS (for reference - moved to agent modules)
# ═══════════════════════════════════════════════════════════════════════════

# EDITOR_AGENT_PROMPT moved to agents/editor_agent.py
_EDITOR_AGENT_PROMPT_LEGACY = r"""You are the chief editor at The Economist reviewing a draft article.

═══════════════════════════════════════════════════════════════════════════
QUALITY GATES - Each must PASS or article needs revision
═══════════════════════════════════════════════════════════════════════════

GATE 1: OPENING (Must grab in first sentence)
□ Does first sentence contain a striking fact or observation?
□ Is there ANY throat-clearing before the hook? (If yes, FAIL)
□ Would a busy reader continue after paragraph 1?

❌ CUT THESE OPENINGS:
- "Amidst the [noun]..." → Start with the data point
- "As [topic] continues..." → Start with the contrast/tension
- "In the world of..." → Start with what's surprising

REWRITE to lead with the most compelling fact.

GATE 2: EVIDENCE (Every claim must be backed)
□ Is every statistic attributed to a named source?
□ Are there any weasel phrases like "studies show" without specifics?
□ Does the opening sentence have a source if it contains a number?

⚠️  CRITICAL: You must REMOVE all [NEEDS SOURCE] and [UNVERIFIED] flags.

Your options:
  a) Add proper source: "according to Gartner's 2024 survey"
  b) Delete the unsourced claim entirely
  c) Rewrite to avoid specific numbers: "many companies" instead of "50% of companies"

EXAMPLE:
WRONG: "50% of companies [NEEDS SOURCE] use AI testing"
RIGHT: "According to Gartner's 2024 World Quality Report, 50% of companies use AI testing"
OR: "Delete the claim if you cannot verify it"

NEVER leave [NEEDS SOURCE] or [UNVERIFIED] in final output. This will block publication.

GATE 3: VOICE (Must sound like The Economist)
□ British spelling throughout?
□ Active voice dominant?
□ No banned phrases from the writer's list?
□ No clichés: "hailed as breakthrough", "game-changer", "revolutionary"?
□ One or fewer analogies?
□ Zero exclamation points?

GATE 4: STRUCTURE (Must flow logically)
□ Does each section advance the argument?
□ Could any paragraph be cut without loss? (If yes, cut it)
□ Is the ending an implication/forward look, NOT a summary?

❌ CUT THESE ENDINGS IMMEDIATELY - PUBLICATION BLOCKER:
- "In conclusion" / "To conclude" / "In summary" → DELETE ENTIRE SENTENCE, start fresh
- "will depend largely on" → Make a definitive prediction
- "Whether [X] becomes reality" → State what WILL happen
- "remains to be seen" / "only time will tell" → Tell us what you see
- "The journey ahead" / "the road ahead" → Cut entirely
- Any sentence that summarizes points already made → DELETE IT

⚠️  ENDING MUST BE: A clear prediction, implication, or call to action. NO hedging.

REWRITE to state a clear implication or prediction.

GATE 5: CHART INTEGRATION (AUTOMATED CHECK)
□ If chart_data was provided, does article contain chart markdown?
□ Is chart filename from research present in article body?
□ Is the chart referenced naturally in the text (not "See figure 1")?
□ Does the text add insight beyond what the chart shows?

⚠️  CRITICAL: If chart was generated but NOT embedded:
  1. This is a PUBLICATION BLOCKER (same as BUG-016)
  2. Add chart markdown: ![Chart title](chart_filename.png)
  3. Add reference sentence: "As the chart shows, [insight]..."
  4. Place after paragraph discussing the data
  5. NEVER proceed without chart embedding if chart exists

═══════════════════════════════════════════════════════════════════════════
AUTOMATED QUALITY CHECKS (Run these first)
═══════════════════════════════════════════════════════════════════════════

BEFORE manual editing, scan the draft for these CRITICAL issues:

1. CHART EMBEDDING CHECK:
   - Pattern search: Look for ![.*]\(.*\.png\)
   - If chart_data exists but NO chart markdown found → FAIL GATE 5
   - If chart found but not referenced in text → FAIL GATE 5

2. BANNED OPENING CHECK:
   - Scan first 2 sentences for patterns:
     * "In today's", "It's no secret", "When it comes", "Amidst"
   - If found → FAIL GATE 1, DELETE and rewrite

3. BANNED CLOSING CHECK:
   - Scan last 2 paragraphs for patterns:
     * "In conclusion", "To conclude", "In summary"
     * "remains to be seen", "only time will tell"
     * "will depend largely on", "Whether [X]"
   - If found → FAIL GATE 4, DELETE and rewrite

4. UNSOURCED STATISTICS CHECK:
   - Pattern search: \d+% (any percentage)
   - Check for attribution in same/adjacent sentence
   - If missing → FAIL GATE 2, add source or delete

5. BANNED PHRASE CHECK:
   - Scan for: "game-changer", "paradigm shift", "leverage" (verb)
   - If found → FAIL GATE 3, replace with concrete description

6. EXCLAMATION POINT CHECK:
   - Search for: !
   - If found → FAIL GATE 3, remove immediately

If ANY automated check fails, note it in gate evaluation and fix in edited version.

═══════════════════════════════════════════════════════════════════════════
SPECIFIC EDITS TO MAKE
═══════════════════════════════════════════════════════════════════════════

1. CUT ruthlessly:
   - Any sentence that restates what was just said
   - Hedging phrases ("it could be argued", "perhaps")
   - Unnecessary adjectives ("very", "really", "extremely")

2. STRENGTHEN weak verbs:
   - "is experiencing growth" → "is growing" or better, "has grown"
   - "is focused on" → "focuses on"
   - "are in the process of" → just use the verb
   - "see potential alleviation" → "could reduce" or "may cut"

2b. ADD SOURCES to opening claims:
   - If first sentence has a statistic, add source immediately
   - "can reduce costs by 30%" → "According to Forrester, can reduce costs by 30%"

3. REPLACE banned phrases:
   - "leverage" → "use" or "exploit"
   - "game-changer" → describe the actual change
   - "at the end of the day" → delete entirely

4. FIX any prescriptive "First/Second/Third" lists:
   - Reframe as observations: "The shrewdest leaders are..."
   - Or convert to flowing prose

5. REWRITE WEAK ENDINGS immediately (CRITICAL - blocks publication):

   FORBIDDEN ENDING PATTERNS - If you see ANY of these, DELETE and rewrite:
   - "In conclusion" / "To conclude" / "In summary" (summative closings)
   - "remains uncertain" / "remains to be seen" / "only time will tell"
   - "will likely become" / "may well" / "could potentially"
   - "will depend largely on" / "will depend on whether"
   - "Success will belong to those who" (wishy-washy)
   - "The future of [X]" (vague)
   - Any recap/summary of what was already stated

   REQUIRED ENDING FORMULA:
   → State what WILL happen (not "may" or "might")
   → Make a specific prediction with confidence
   → Or identify the clear winner/loser

   Example fixes:
   ❌ "In conclusion, flaky tests present challenges. Success will belong to those who ensure stability."
   ✅ "Companies that invest in robust test infrastructure will outpace competitors. Those that don't will bleed talent."

   ❌ "The future of self-healing tests will depend largely on vendor improvements."
   ✅ "Self-healing tests will remain niche until vendors stop overselling and start delivering."

═══════════════════════════════════════════════════════════════════════════
DRAFT TO REVIEW:
{draft}
═══════════════════════════════════════════════════════════════════════════

⚠️  BEFORE YOU START: Scan the LAST 3 PARAGRAPHS of the draft for weak endings.
If you find "In conclusion", "To conclude", "In summary", or any recap:
  1. DELETE those paragraphs entirely
  2. Write a NEW ending with a definitive statement

First, evaluate each gate (PASS/FAIL with brief note).
Then return the EDITED article with all fixes applied.

⚠️  CRITICAL: YAML front matter format:
- Must use --- delimiters (NOT ```yaml code fences)
- Date must be TODAY: 2026-01-01 (not dates from sources)
- Title must be specific, not generic

❌ WRONG:
```yaml
title: "Myth vs Reality"
date: 2023-11-09
```

✅ CORRECT:
---
title: "Self-Healing Tests: Myth vs Reality"
date: 2026-01-01
---

═══════════════════════════════════════════════════════════════════════════
REQUIRED OUTPUT FORMAT (CRITICAL - Sprint 8 Enhancement)
═══════════════════════════════════════════════════════════════════════════

You MUST output in this EXACT format with explicit PASS/FAIL for each gate:

## Quality Gate Results

**GATE 1: OPENING** - [PASS/FAIL]
- First sentence hook: [Brief assessment]
- Throat-clearing present: [YES/NO]
- Reader engagement: [Assessment]
**Decision**: [PASS or FAIL with reason]

**GATE 2: EVIDENCE** - [PASS/FAIL]
- Statistics sourced: [X/Y statistics have sources]
- [NEEDS SOURCE] flags removed: [YES/NO]
- Weasel phrases present: [YES/NO]
**Decision**: [PASS or FAIL with reason]

**GATE 3: VOICE** - [PASS/FAIL]
- British spelling: [YES/NO]
- Active voice: [YES/NO]
- Banned phrases found: [List any found or "NONE"]
- Exclamation points: [Count or "NONE"]
**Decision**: [PASS or FAIL with reason]

**GATE 4: STRUCTURE** - [PASS/FAIL]
- Logical flow: [Assessment]
- Weak ending: [YES/NO - if yes, what pattern]
- Redundant paragraphs: [Count or "NONE"]
**Decision**: [PASS or FAIL with reason]

**GATE 5: CHART INTEGRATION** - [PASS/FAIL]
- Chart markdown present: [YES/NO]
- Chart referenced in text: [YES/NO]
- Natural integration: [Assessment]
**Decision**: [PASS or FAIL with reason if chart_data provided, otherwise N/A]

**OVERALL GATES PASSED**: [X/5]
**PUBLICATION DECISION**: [READY/NEEDS REVISION]

---

## Edited Article

[If ALL gates PASS, include edited article with YAML frontmatter]
[If ANY gate FAILS, explain what needs fixing before returning edited version]

---
layout: post
title: "Specific Title with Context"
date: 2026-01-01
---

[Full article content]

---

⚠️  CRITICAL: The explicit PASS/FAIL format is MANDATORY (Sprint 8 improvement).
This format enables automated quality tracking and prevents vague assessments."""


CRITIQUE_AGENT_PROMPT = """You are a hostile reviewer looking for ANY flaw in this Economist-style article.

Your job is to find problems, not praise. Be harsh.

Review for:
1. UNSOURCED CLAIMS: Any statistic without attribution? Flag it.
2. CLICHÉS: Any tired phrases that should be cut?
3. LOGIC GAPS: Does the argument have holes?
4. VOICE BREAKS: Any sentences that don't sound like The Economist?
5. MISSING CONTRARIAN: Is this just conventional wisdom repackaged?

For each issue found, provide:
- The problematic text
- Why it's a problem
- Suggested fix

If the article is genuinely good, say so briefly. Don't invent problems.

ARTICLE:
{article}"""


VISUAL_QA_PROMPT = """You are a Visual QA specialist reviewing an Economist-style chart for publication.

═══════════════════════════════════════════════════════════════════════════
LAYOUT ZONE VALIDATION (Critical - most bugs come from zone violations)
═══════════════════════════════════════════════════════════════════════════

The chart has 5 distinct zones. NO element should cross zone boundaries:

```
RED BAR ZONE (top 4%)      - Only the red bar
TITLE ZONE                 - Title and subtitle only
CHART ZONE                 - Data lines, gridlines, inline labels
X-AXIS ZONE                - ONLY x-axis tick labels (years, etc.)
SOURCE ZONE (bottom)       - Source attribution only
```

═══════════════════════════════════════════════════════════════════════════
QUALITY GATES
═══════════════════════════════════════════════════════════════════════════

GATE 1: ZONE INTEGRITY
□ Red bar fully visible at top (not clipped)?
□ Title BELOW red bar with visible gap?
□ All inline series labels in CHART ZONE only?
□ NO labels overlapping X-axis tick labels (years)?
□ Source line visible at bottom, not overlapping anything?

GATE 2: LABEL POSITIONING
□ Inline labels NOT directly on data lines (must have offset)?
□ For LOW series near bottom: is label ABOVE the line (in clear space)?
□ No label-to-label collision?
□ End-of-line value labels present and readable?

GATE 3: STYLE COMPLIANCE
□ Red bar present (#e3120b)?
□ Background warm beige (#f1f0e9)?
□ Horizontal gridlines only?
□ No legend box (direct labeling only)?

GATE 4: DATA & EXPORT
□ All data points visible?
□ Y-axis starts at zero?
□ Image sharp, no artifacts?

═══════════════════════════════════════════════════════════════════════════
SPECIFIC BUGS TO CHECK
═══════════════════════════════════════════════════════════════════════════

BUG #1: Title/red bar overlap
BUG #2: Inline label ON the data line (not offset)
BUG #3: Inline label in X-axis zone (overlapping year labels)
        → For LOW series, label must go ABOVE line, not below
BUG #4: Label-to-label overlap
BUG #5: Clipped elements at edges

═══════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════

{
  "gates": {
    "zone_integrity": {"pass": true/false, "issues": []},
    "label_positioning": {"pass": true/false, "issues": []},
    "style_compliance": {"pass": true/false, "issues": []},
    "data_export": {"pass": true/false, "issues": []}
  },
  "overall_pass": true/false,
  "critical_issues": ["Zone violations that MUST be fixed"],
  "fix_suggestions": [{"issue": "...", "fix": "..."}]
}

Zone boundary violations are CRITICAL failures."""


# ═══════════════════════════════════════════════════════════════════════════
# AGENT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


def create_client():
    """Create unified LLM client (supports Anthropic Claude and OpenAI)"""
    return create_llm_client()


# Research Agent has been extracted to agents/research_agent.py
# Import at top of file maintains backward compatibility


# Writer Agent has been extracted to agents/writer_agent.py
# Import at top of file maintains backward compatibility

# Graphics Agent has been extracted to agents/graphics_agent.py
# Import at top of file maintains backward compatibility

# Editor Agent has been extracted to agents/editor_agent.py
# Import at top of file maintains backward compatibility


def run_critique_agent(client, article: str) -> str:
    print("🔍 Critique Agent: Final hostile review...")

    critique = call_llm(
        client,
        CRITIQUE_AGENT_PROMPT.format(article=article),
        "Find any remaining flaws.",
        max_tokens=1500,
    )
    issues_found = (
        critique.lower().count("issue")
        + critique.lower().count("problem")
        + critique.lower().count("flag")
    )

    if issues_found > 0:
        print(f"   ⚠ {issues_found} potential issues flagged for review")
    else:
        print("   ✓ No major issues found")

    return critique


def run_visual_qa_agent(client, image_path: str, chart_record: dict = None) -> dict:
    """Visual QA Agent: Validates chart rendering quality.

    Sprint 8 Enhancement: Two-stage validation
    1. Programmatic zone boundary checks (fast, deterministic)
    2. LLM vision analysis (comprehensive, subjective)
    """
    print("🎨 Visual QA Agent: Inspecting chart...")

    if not os.path.exists(image_path):
        print(f"   ⚠ Chart not found: {image_path}")
        return {"overall_pass": False, "critical_issues": ["Chart file not found"]}

    # STAGE 1: Programmatic zone boundary validation (Sprint 8 Story 2)
    try:
        from visual_qa_zones import ZoneBoundaryValidator

        zone_validator = ZoneBoundaryValidator()
        zones_valid, zone_issues = zone_validator.validate_chart(image_path)

        if not zones_valid:
            print(f"   ❌ Zone validation: {len(zone_issues)} boundary violations")
            for issue in zone_issues[:3]:
                print(f"      • {issue}")
        else:
            print("   ✅ Zone validation: All boundaries correct")
    except ImportError:
        print("   ℹ  Zone validator unavailable (continuing with LLM-only validation)")
        zones_valid = True
        zone_issues = []

    # STAGE 2: LLM vision analysis
    # Load image as base64
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    # Visual QA requires provider-specific handling for images
    if client.provider == "anthropic":
        response_text = (
            client.client.messages.create(
                model=client.model,
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
                                    "media_type": "image/png",
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": "Review this chart for visual quality issues.",
                            },
                        ],
                    }
                ],
            )
            .content[0]
            .text
        )
    elif client.provider == "openai":
        response_text = (
            client.client.chat.completions.create(
                model=client.model,
                max_tokens=2000,
                messages=[
                    {"role": "system", "content": VISUAL_QA_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Review this chart for visual quality issues.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                },
                            },
                        ],
                    },
                ],
            )
            .choices[0]
            .message.content
        )
    else:
        response_text = '{"overall_pass": false, "critical_issues": ["Provider does not support image analysis"]}'

    try:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            result = json.loads(response_text[start:end])
        else:
            result = {
                "overall_pass": False,
                "critical_issues": ["Failed to parse QA response"],
            }
    except json.JSONDecodeError:
        result = {"overall_pass": False, "critical_issues": ["JSON parse error"]}

    gates = result.get("gates", {})
    passed = sum(1 for g in gates.values() if g.get("pass", False))
    total = len(gates) if gates else 5

    # Combine zone validation with LLM results
    if not zones_valid:
        result["zone_validation"] = {"pass": False, "issues": zone_issues}
        result["overall_pass"] = False
        if "critical_issues" not in result:
            result["critical_issues"] = []
        result["critical_issues"].extend(zone_issues)
    else:
        result["zone_validation"] = {"pass": True, "issues": []}

    print(f"   Visual gates: {passed}/{total} passed")
    print(f"   Zone boundaries: {'✓ PASS' if zones_valid else '✗ FAIL'}")

    if result.get("overall_pass"):
        print("   ✓ Chart PASSED visual QA")
    else:
        print("   ✗ Chart FAILED visual QA")
        for issue in result.get("critical_issues", [])[:3]:
            print(f"     • {issue}")

    # Record metrics if chart_record provided
    if chart_record is not None:
        metrics = get_metrics_collector()
        metrics.record_visual_qa(chart_record, result)

    return result


# ═══════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR (v3 - with governance)
# ═══════════════════════════════════════════════════════════════════════════


def generate_economist_post(
    topic: str,
    category: str = "quality-engineering",
    talking_points: str = "",
    output_dir: str = "output",
    interactive: bool = False,
    governance: GovernanceTracker = None,
) -> dict:
    """Generate Economist-style blog post with optional human review gates"""
    print("\n" + "=" * 70)
    print(f"🎯 GENERATING: {topic}")
    if interactive:
        print("🚦 INTERACTIVE MODE: Approval gates enabled")
    print("=" * 70 + "\n")

    client = create_client()
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(topic, max_length=50)

    # Use provided output_dir
    posts_dir = Path(output_dir)
    charts_dir = posts_dir / "charts"

    posts_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    # Create governance tracker if not provided
    if governance is None and interactive:
        governance = GovernanceTracker(f"{output_dir}/governance")

    # Initialize agent metrics tracking
    agent_metrics = AgentMetrics()

    # Sprint 14 Integration: Initialize ROI Tracker
    roi_tracker = None
    if ROI_TRACKER_AVAILABLE:
        roi_tracker = ROITracker(log_file=f"{output_dir}/execution_roi.json")
        _ = roi_tracker.start_execution("content_generation")  # Track execution
        print("📊 ROI Tracking: Enabled")

    skip_approvals = False  # Set by 'skip-all' response

    # Stage 1: Research
    research = run_research_agent(client, topic, talking_points, governance)

    # Track Research Agent metrics
    verified = sum(
        1 for dp in research.get("data_points", []) if dp.get("verified", False)
    )
    total_points = len(research.get("data_points", []))
    unverified = len(research.get("unverified_claims", []))
    agent_metrics.track_research_agent(
        data_points=total_points, verified=verified, unverified=unverified
    )

    # Approval Gate 1: Research
    if interactive and not skip_approvals:
        verified = sum(
            1 for dp in research.get("data_points", []) if dp.get("verified", False)
        )
        total = len(research.get("data_points", []))

        response = governance.request_approval(
            "Research Complete",
            f"Research agent gathered {total} data points ({verified} verified)",
            {
                "Unverified claims": len(research.get("unverified_claims", [])),
                "Has chart data": bool(research.get("chart_data")),
                "Review file": f"{governance.session_dir}/research_agent.json",
            },
        )

        if (
            response
            and hasattr(governance, "decisions")
            and governance.decisions[-1].get("skip_all")
        ):
            skip_approvals = True
        elif not response:
            print("❌ Research rejected. Exiting.")
            return {"status": "rejected", "stage": "research"}

    # Stage 2: Graphics (with regeneration on Visual QA failure)
    chart_path = None
    chart_record = None
    visual_qa_passed = True
    visual_qa_result = None
    max_chart_attempts = 2  # Try regeneration once if QA fails
    chart_attempts = 0

    if research.get("chart_data"):
        chart_filename = str(charts_dir / f"{slug}.png")

        while chart_attempts < max_chart_attempts:
            chart_attempts += 1

            # Generate chart
            if chart_attempts > 1:
                print(
                    f"   🔄 Regenerating chart (attempt {chart_attempts}/{max_chart_attempts})..."
                )
                # Add QA feedback to chart spec for regeneration
                if visual_qa_result and visual_qa_result.get("critical_issues"):
                    research["chart_data"]["_qa_feedback"] = visual_qa_result[
                        "critical_issues"
                    ]

            chart_path = run_graphics_agent(
                client, research["chart_data"], chart_filename
            )

            if not chart_path:
                break  # Chart generation failed entirely

            # Get the chart record for metrics tracking
            metrics = get_metrics_collector()
            if metrics.current_session["charts"]:
                chart_record = metrics.current_session["charts"][-1]

            # Stage 2b: Visual QA (runs for providers with vision support)
            if client.provider in ("anthropic", "openai"):
                visual_qa_result = run_visual_qa_agent(client, chart_path, chart_record)
                visual_qa_passed = visual_qa_result.get("overall_pass", False)

                if visual_qa_passed:
                    print("   ✓ Chart passed Visual QA")
                    break  # Success - exit loop
                else:
                    print(
                        f"   ⚠ Chart failed Visual QA (attempt {chart_attempts}/{max_chart_attempts})"
                    )
                    # Save QA report for debugging
                    qa_report_path = chart_path.replace(
                        ".png", f"-qa-report-{chart_attempts}.json"
                    )
                    with open(qa_report_path, "w") as f:
                        json.dump(visual_qa_result, f, indent=2)

                    if chart_attempts >= max_chart_attempts:
                        print(
                            "   ❌ Chart failed Visual QA after all attempts - BLOCKING publication"
                        )
            else:
                # No vision support - can't validate
                print("   ℹ Visual QA skipped (provider does not support vision)")
                visual_qa_passed = False
                break

        # Log to governance
        if governance and visual_qa_result:
            governance.log_agent_output(
                "graphics_agent",
                {"chart_path": chart_path, "visual_qa": visual_qa_result},
                metadata={"passed_qa": visual_qa_passed, "attempts": chart_attempts},
            )

        # Track Graphics Agent metrics
        zone_violations = (
            len(visual_qa_result.get("critical_issues", [])) if visual_qa_result else 0
        )
        agent_metrics.track_graphics_agent(
            charts_generated=chart_attempts,
            visual_qa_passed=1 if visual_qa_passed else 0,
            zone_violations=zone_violations,
            regenerations=chart_attempts - 1,
            validation_passed=visual_qa_passed,
        )

        # BLOCK publication if chart failed Visual QA
        if chart_path and not visual_qa_passed:
            print("\n" + "=" * 70)
            print("❌ BLOCKED: Chart failed Visual QA")
            print("   Critical issues:")
            for issue in (visual_qa_result or {}).get("critical_issues", ["Unknown"]):
                print(f"   • {issue}")
            print("=" * 70 + "\n")

            return {
                "status": "rejected",
                "reason": "visual_qa_failed",
                "chart_path": chart_path,
                "visual_qa_result": visual_qa_result,
                "attempts": chart_attempts,
            }

    # Stage 2c: Featured Image Generation (optional)
    featured_image_path = None
    featured_image_blog_path = None  # Path to use in frontmatter (blog destination)
    if os.environ.get("OPENAI_API_KEY"):
        featured_image_filename = str(posts_dir / "images" / f"{slug}.png")
        featured_image_path = generate_featured_image(
            topic=topic,
            article_summary=research.get("trend_narrative", topic),
            contrarian_angle=research.get("contrarian_angle", ""),
            output_path=featured_image_filename,
        )
        if featured_image_path:
            # Use blog path in frontmatter (where image will be deployed)
            featured_image_blog_path = f"/assets/images/{slug}.png"
        else:
            print("   ℹ Continuing without featured image")
    else:
        print("   ℹ OPENAI_API_KEY not set, skipping featured image generation")

    # Stage 3: Writing
    # Prepare chart filename if chart will be generated
    chart_filename = None
    if research.get("chart_data"):
        chart_filename = f"/assets/charts/{slug}.png"

    draft, writer_metadata = run_writer_agent(
        client, topic, research, date_str, chart_filename, featured_image_blog_path
    )

    # Track Writer Agent metrics
    word_count = len(draft.split())
    banned_phrases = sum(
        1
        for phrase in [
            "game-changer",
            "paradigm shift",
            "leverage",
            "at the end of the day",
        ]
        if phrase.lower() in draft.lower()
    )
    chart_embedded = bool(
        chart_filename and "![" in draft and chart_filename.split("/")[-1] in draft
    )

    agent_metrics.track_writer_agent(
        word_count=word_count,
        banned_phrases=banned_phrases,
        validation_passed=writer_metadata["is_valid"],
        regenerations=1 if writer_metadata["regenerated"] else 0,
        chart_embedded=chart_embedded,
    )

    # Log draft to governance
    if governance:
        governance.log_agent_output(
            "writer_agent",
            {"draft": draft, "word_count": len(draft.split())},
            metadata={"topic": topic, "length": len(draft)},
        )

    # Approval Gate 2: Draft Review
    if interactive and not skip_approvals:
        response = governance.request_approval(
            "Draft Complete",
            f"Writer agent produced {len(draft.split())}-word draft",
            {
                "Topic": topic,
                "Preview": draft[:200] + "...",
                "Review file": f"{governance.session_dir}/writer_agent.json",
            },
        )

        if (
            response
            and hasattr(governance, "decisions")
            and governance.decisions[-1].get("skip_all")
        ):
            skip_approvals = True
        elif not response:
            print("❌ Draft rejected. Exiting.")
            return {"status": "rejected", "stage": "draft"}

    # Stage 4: Editing
    # Sprint 14 Integration: Initialize and pass Style Memory to Editor
    style_memory = None
    if STYLE_MEMORY_AVAILABLE:
        try:
            style_memory = StyleMemoryTool()
        except Exception as e:
            print(f"   ⚠️  Style Memory initialization failed: {e}")

    edited_article, gates_passed, gates_failed = run_editor_agent(
        client, draft, style_memory_tool=style_memory, current_date=date_str
    )

    # Track Editor Agent metrics
    agent_metrics.track_editor_agent(
        gates_passed=gates_passed,
        gates_failed=gates_failed,
        edits_made=len(edited_article) - len(draft),  # Rough estimate
        quality_issues=[] if gates_failed == 0 else [f"{gates_failed} gates failed"],
    )

    # Stage 5: Final critique
    critique = None
    if gates_failed == 0:
        critique = run_critique_agent(client, edited_article)
    else:
        print(f"   ⚠ Skipping critique - {gates_failed} quality gates failed")

    # Stage 6: Publication Validation (CRITICAL - blocks bad articles)
    print("🔒 Publication Validator: Final quality gate...")
    validator = PublicationValidator(expected_date=date_str)
    is_valid, validation_issues = validator.validate(edited_article)

    if not is_valid:
        print("\n" + validator.format_report(is_valid, validation_issues))
        print("\n❌ PUBLICATION BLOCKED: Article failed validation")
        print("\n💡 These issues indicate agent prompts need strengthening.")
        print("   The agents should have prevented these issues.")

        # Save to quarantine directory
        quarantine_dir = posts_dir / "quarantine"
        quarantine_dir.mkdir(exist_ok=True)
        quarantine_path = quarantine_dir / f"{date_str}-{slug}.md"
        with open(quarantine_path, "w") as f:
            f.write(edited_article)

        # Save validation report
        report_path = quarantine_dir / f"{date_str}-{slug}-VALIDATION-FAILED.txt"
        with open(report_path, "w") as f:
            f.write(validator.format_report(is_valid, validation_issues))

        print(f"   Quarantined to: {quarantine_path}")
        print(f"   Report saved: {report_path}")

        return {
            "status": "rejected",
            "reason": "validation_failed",
            "article_path": str(quarantine_path),
            "validation_report": str(report_path),
            "issues": validation_issues,
        }
    else:
        print(f"   ✓ Validation PASSED ({len(validation_issues)} advisory notes)")

    # Save article (only if validated)
    article_path = str(posts_dir / f"{date_str}-{slug}.md")
    with open(article_path, "w") as f:
        f.write(edited_article)

    if critique:
        review_path = str(posts_dir / f"{date_str}-{slug}-review.md")
        with open(review_path, "w") as f:
            f.write(f"# Editorial Review: {topic}\n\n{critique}")

    print("\n" + "=" * 70)
    print("✅ COMPLETE")
    print(f"   Article: {article_path}")
    if chart_path:
        print(f"   Chart:   {chart_path}")
        print(
            f"   Visual QA: {'PASSED' if visual_qa_passed else 'FAILED - needs review'}"
        )
    print(f"   Editorial: {gates_passed}/5 gates passed")
    print("=" * 70 + "\n")

    # Finalize metrics session
    metrics = get_metrics_collector()
    metrics.end_session()

    # Save agent metrics
    agent_metrics.save()

    # Print metrics summary
    print("\n" + "=" * 70)
    print("📊 METRICS SUMMARY")
    print("=" * 70)
    summary = metrics.get_summary()
    print(f"   Charts Generated: {summary['total_charts_generated']}")
    print(f"   Visual QA Pass Rate: {summary['visual_qa_pass_rate']:.1f}%")
    if summary["total_zone_violations"] > 0:
        print(f"   Zone Violations: {summary['total_zone_violations']}")
    print("=" * 70 + "\n")

    return {
        "article_path": article_path,
        "chart_path": chart_path,
        "gates_passed": gates_passed,
        "gates_failed": gates_failed,
        "visual_qa_passed": visual_qa_passed,
        "word_count": len(edited_article.split()),
        "metrics_summary": summary,
    }


# ═══════════════════════════════════════════════════════════════════════════
# CONTENT QUEUE
# ═══════════════════════════════════════════════════════════════════════════

CONTENT_QUEUE = [
    {
        "topic": "The Agentic AI Testing Paradox",
        "category": "quality-engineering",
        "talking_points": "adoption rates vs productivity gains, maintenance costs, vendor claims vs reality",
    },
    {
        "topic": "Self-Healing Tests: Myth vs Reality",
        "category": "test-automation",
        "talking_points": "vendor promises, actual maintenance reduction, limitations",
    },
    {
        "topic": "The Economics of Flaky Tests",
        "category": "quality-engineering",
        "talking_points": "developer time costs, CI delays, trust erosion",
    },
    {
        "topic": "Quality Metrics Executives Actually Use",
        "category": "quality-engineering",
        "talking_points": "defect escape rate, cost of quality, vanity metrics",
    },
    {
        "topic": "The Death of the QA Department",
        "category": "quality-engineering",
        "talking_points": "embedded QE, job growth despite automation",
    },
    {
        "topic": "Technical Debt's Compound Interest",
        "category": "software-engineering",
        "talking_points": "velocity degradation, refactoring ROI",
    },
    {
        "topic": "Shift-Right: The Trend Nobody Budgeted For",
        "category": "quality-engineering",
        "talking_points": "production testing costs, observability spend",
    },
    {
        "topic": "No-Code Testing's Hidden Costs",
        "category": "test-automation",
        "talking_points": "creation vs maintenance, 2am debugging",
    },
]


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Generate Economist-style articles with AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Non-interactive (automated)
  python economist_agent.py

  # Interactive with human review gates
  python economist_agent.py --interactive

  # Custom topic
  export TOPIC="The Rise of AI Testing"
  python economist_agent.py --interactive
        """,
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Enable interactive mode with approval gates between stages",
    )
    parser.add_argument(
        "--governance-dir",
        default=None,
        help="Directory for governance logs (default: output/governance)",
    )

    args = parser.parse_args()

    # Get environment variables with defaults
    topic = os.environ.get("TOPIC", "").strip()
    talking_points = os.environ.get("TALKING_POINTS", "").strip()
    category = os.environ.get("CATEGORY", "quality-engineering").strip()

    # Set default output directory if not specified
    output_dir = os.environ.get("OUTPUT_DIR", "").strip()
    if not output_dir:
        output_dir = "output"
        print(f"   ℹ OUTPUT_DIR not set, using default: {output_dir}/")

    # Create output directories
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(output_dir).joinpath("charts").mkdir(parents=True, exist_ok=True)
    print(f"   ✓ Output directory: {Path(output_dir).absolute()}")

    if not topic:
        week_num = datetime.now().isocalendar()[1]
        queued = CONTENT_QUEUE[week_num % len(CONTENT_QUEUE)]
        topic = queued["topic"]
        category = queued["category"]
        talking_points = queued.get("talking_points", "")
        print(f"ℹ Using queued topic: {topic}")

    # Create governance tracker if interactive mode
    governance = None
    if args.interactive:
        governance_dir = args.governance_dir or f"{output_dir}/governance"
        governance = GovernanceTracker(governance_dir)
        print(f"   📋 Governance tracking enabled: {governance.session_dir}")

    result = generate_economist_post(
        topic,
        category,
        talking_points,
        output_dir,
        interactive=args.interactive,
        governance=governance,
    )

    # Generate governance report if interactive
    if governance and result.get("status") != "rejected":
        governance.generate_report()

    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"article_path={result.get('article_path', '')}\n")
            f.write(f"quality_score={result.get('gates_passed', 0)}/5\n")

    # Exit with error if article was rejected/quarantined
    if result.get("status") == "rejected":
        sys.exit(1)


if __name__ == "__main__":
    main()
