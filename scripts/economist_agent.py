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

import os
import json
import base64
from datetime import datetime
from slugify import slugify
from pathlib import Path
import subprocess
import sys
import re
import argparse

# Import unified LLM client
from llm_client import create_llm_client, call_llm

# Import governance system
from governance import GovernanceTracker, InteractiveMode

# Import publication validator
from publication_validator import PublicationValidator

# ═══════════════════════════════════════════════════════════════════════════
# AGENT SYSTEM PROMPTS (v2 - with codified editorial lessons)
# ═══════════════════════════════════════════════════════════════════════════

RESEARCH_AGENT_PROMPT = """You are a Research Analyst preparing a briefing pack for an Economist-style article.

YOUR TASK:
Given a topic, produce a comprehensive research brief with VERIFIED data.

CRITICAL RULES:
1. Every statistic MUST have a named source (organization, report, date)
2. If you cannot verify a claim, mark it as [UNVERIFIED] 
3. Prefer primary sources (surveys, reports) over secondary (blog posts, articles)
4. Flag any numbers that appear in multiple sources with different values

OUTPUT STRUCTURE:
{
  "headline_stat": {
    "value": "The single most compelling statistic",
    "source": "Exact source name",
    "year": "2024",
    "verified": true
  },
  "data_points": [
    {
      "stat": "Specific number or percentage",
      "source": "Organization/Report name",
      "year": "2024",
      "url": "Source URL if available",
      "verified": true
    }
  ],
  "trend_narrative": "2-3 sentences on the bigger picture with source references",
  "chart_data": {
    "title": "Economist-style chart title (noun phrase, not sentence)",
    "subtitle": "What the chart shows, units",
    "type": "line|bar|scatter",
    "x_label": "Years|Categories|etc",
    "y_label": "Units (%, $bn, etc)",
    "data": [{"label": "2020", "series1": 45, "series2": 12}],
    "source_line": "Sources: Name1; Name2"
  },
  "contrarian_angle": "What surprising or counterintuitive finding challenges conventional wisdom?",
  "unverified_claims": ["Any claims we couldn't source - DO NOT USE THESE"]
}

Be rigorous. Unsourced claims damage credibility."""

WRITER_AGENT_PROMPT = """⚠️  CRITICAL: Today's date is {current_date}. You MUST use this exact date in the YAML front matter.

You are a senior writer at The Economist, crafting an article on quality engineering.

═══════════════════════════════════════════════════════════════════════════
ECONOMIST VOICE - MANDATORY RULES
═══════════════════════════════════════════════════════════════════════════

STRUCTURE (800-1200 words):
1. OPENING: Lead with most striking fact. NO throat-clearing. NO "In today's world..."
2. BODY: 3-4 sections, each advancing the argument. Use ## headers (noun phrases, not questions)
3. CHART: Reference naturally with "As the chart shows..." - never "See figure 1"
4. CLOSE: Implication or forward look. NOT a summary. NOT "In conclusion..."

VOICE:
- Confident and direct. State views, don't hedge.
- British spelling: organisation, favour, analyse, sceptical
- Active voice: "Teams use AI" not "AI is used by teams"
- Concrete nouns, strong verbs: "surged" not "experienced significant growth"
- One analogy maximum per article. Make it count.

═══════════════════════════════════════════════════════════════════════════
LINES TO AVOID - These will be cut by the editor
═══════════════════════════════════════════════════════════════════════════

BANNED OPENINGS:
- "In today's fast-paced world..."
- "It's no secret that..."
- "When it comes to..."
- "In recent years..."
- "[Topic] is more important than ever..."
- "Amidst the [noun] surrounding..."
- "As [topic] continues to evolve..."
- "The world of [topic] is changing..."

CORRECT OPENING PATTERN:
Lead with the most striking DATA POINT from your research.

Example:
✅ GOOD: "Self-healing tests promise an 80% cut in maintenance costs. Only 10% of companies achieve it."
❌ BAD: "Amidst the fervour surrounding automation in software development, self-healing tests have emerged..."

BANNED PHRASES:
- "game-changer" / "paradigm shift" / "revolutionary"
- "leverage" (as a verb)
- "it could be argued that" / "some might say"
- "in the wild" / "at the end of the day"
- "This is unsexy work" / "Let's be honest"
- "First, ... Second, ... Third, ..." (listicle energy)

BANNED CLOSINGS:
- "Only time will tell..."
- "The future remains to be seen..."
- "In conclusion..."
- "...will depend largely on..."
- "Whether [X] becomes a reality..."
- "The journey ahead..."
- "remains to be seen"
- Any summary of what was already said

CORRECT CLOSING PATTERN:
State a clear IMPLICATION or PREDICTION. Be definitive, not wishy-washy.

Example:
✅ GOOD: "Self-healing tests will remain niche until vendors stop overselling and start delivering."
❌ BAD: "Whether the promise becomes a reality will depend largely on how companies navigate the transition."

TONE VIOLATIONS:
- Exclamation points (never use these)
- Rhetorical questions as section headers
- Snarky asides that try too hard to be clever
- "Dear reader" or any direct address

═══════════════════════════════════════════════════════════════════════════
TITLE STYLE
═══════════════════════════════════════════════════════════════════════════

Economist titles are:
- Short (2-4 words ideal)
- Often puns or wordplay on common phrases
- Followed by a factual subtitle

Examples:
- "Testing times" (about QA challenges)
- "The long and short of it" (about technical debt)
- "Broken promises" (about vendor claims)
- "Quality time" (about QE investment)

BAD titles:
- "The Ultimate Guide to..."
- "Everything You Need to Know About..."
- "X Tips for Y"
- Questions as titles

═══════════════════════════════════════════════════════════════════════════
YOUR RESEARCH BRIEF:
{research_brief}
═══════════════════════════════════════════════════════════════════════════

Write the article now. Return complete Markdown with YAML frontmatter.

⚠️  CRITICAL FORMAT REQUIREMENTS:

1. DATE: Use TODAY'S DATE (2026-01-01), NOT dates from research sources
2. YAML: Use --- delimiters, NOT ```yaml code fences
3. TITLE: Must be specific with context, NOT generic

Correct format:
---
title: "Self-Healing Tests: Myth vs Reality"
date: 2026-01-01
author: "The Economist"
---

[Article content here]

WRONG formats (DO NOT USE):
```yaml          ← NO code fences
title: "Myth vs Reality"  ← Too generic
date: 2023-11-09          ← Wrong date
```

Now write the article:"""

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

EDITOR_AGENT_PROMPT = """You are the chief editor at The Economist reviewing a draft article.

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

GATE 5: CHART INTEGRATION
□ Is the chart referenced naturally in the text?
□ Does the text add insight beyond what the chart shows?

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

Format:
## Quality Gate Results
[Gate evaluations]

## Edited Article
---
title: "Specific Title with Context"
date: 2026-01-01
---

[Full article content]"""


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


def run_research_agent(client, topic: str, talking_points: str = "", governance: GovernanceTracker = None) -> dict:
    # Input validation
    if not topic or not isinstance(topic, str):
        raise ValueError(
            "[RESEARCH_AGENT] Invalid topic. Expected non-empty string, "
            f"got: {type(topic).__name__}"
        )
    
    if len(topic.strip()) < 5:
        raise ValueError(
            f"[RESEARCH_AGENT] Topic too short: '{topic}'. "
            "Must be at least 5 characters."
        )
    
    print(f"📊 Research Agent: Gathering verified data for '{topic[:50]}...'")
    
    user_prompt = f"""Research this topic for an Economist-style article:

TOPIC: {topic}
FOCUS AREAS: {talking_points if talking_points else 'General coverage'}

Find specific, VERIFIABLE data with exact sources. Flag anything you cannot verify."""

    response_text = call_llm(
        client,
        RESEARCH_AGENT_PROMPT,
        user_prompt,
        max_tokens=2500
    )
    
    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            research_data = json.loads(response_text[start:end])
        else:
            research_data = {"raw_research": response_text, "chart_data": None}
    except json.JSONDecodeError:
        research_data = {"raw_research": response_text, "chart_data": None}
    
    verified = sum(1 for dp in research_data.get('data_points', []) if dp.get('verified', False))
    total = len(research_data.get('data_points', []))
    print(f"   ✓ Found {total} data points ({verified} verified)")
    
    if research_data.get('unverified_claims'):
        print(f"   ⚠ {len(research_data['unverified_claims'])} unverified claims flagged")
    
    # Log to governance
    if governance:
        governance.log_agent_output(
            "research_agent",
            research_data,
            metadata={
                "topic": topic,
                "data_points": total,
                "verified": verified,
                "unverified": len(research_data.get('unverified_claims', []))
            }
        )
    
    return research_data


def run_writer_agent(client, topic: str, research_brief: dict, current_date: str) -> str:
    # Input validation
    if not topic or not isinstance(topic, str):
        raise ValueError(
            "[WRITER_AGENT] Invalid topic. Expected non-empty string, "
            f"got: {type(topic).__name__}"
        )
    
    if not isinstance(research_brief, dict):
        raise ValueError(
            "[WRITER_AGENT] Invalid research_brief. Expected dict, "
            f"got: {type(research_brief).__name__}"
        )
    
    if not research_brief:
        raise ValueError(
            "[WRITER_AGENT] Empty research_brief. Cannot write without research data."
        )
    
    print(f"✍️  Writer Agent: Drafting article on '{topic[:50]}...'")
    
    # Build system prompt by replacing placeholders one at a time
    system_prompt = WRITER_AGENT_PROMPT.replace("{current_date}", current_date)
    system_prompt = system_prompt.replace("{research_brief}", json.dumps(research_brief, indent=2))
    
    draft = call_llm(
        client,
        system_prompt,
        f"⚠️  REMEMBER: Use date: {current_date} in YAML front matter.\n\nWrite an Economist-style article on: {topic}",
        max_tokens=3000
    )
    word_count = len(draft.split())
    print(f"   ✓ Draft complete ({word_count} words)")
    return draft


def run_graphics_agent(client, chart_spec: dict, output_path: str) -> str:
    if not chart_spec:
        print("📈 Graphics Agent: No chart data provided, skipping...")
        return None
    
    # Input validation
    if not isinstance(chart_spec, dict):
        raise ValueError(
            "[GRAPHICS_AGENT] Invalid chart_spec. Expected dict, "
            f"got: {type(chart_spec).__name__}"
        )
    
    required_fields = ['title', 'data']
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
    
    print(f"📈 Graphics Agent: Creating visualization '{chart_spec.get('title', 'Untitled')[:40]}...'")
    
    code = call_llm(
        client,
        GRAPHICS_AGENT_PROMPT.format(chart_spec=json.dumps(chart_spec, indent=2)),
        "Generate the matplotlib code.",
        max_tokens=2500
    )
    
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0]
    elif "```" in code:
        code = code.split("```")[1].split("```")[0]
    
    if "plt.savefig" not in code:
        code += f"\nplt.savefig('{output_path}', dpi=300, bbox_inches='tight', facecolor='#f1f0e9')"
    else:
        code = re.sub(r"plt\.savefig\([^)]+\)", f"plt.savefig('{output_path}', dpi=300, bbox_inches='tight', facecolor='#f1f0e9')", code)
    
    try:
        temp_script = "/tmp/chart_gen.py"
        with open(temp_script, 'w') as f:
            f.write("import matplotlib\nmatplotlib.use('Agg')\n")
            f.write("import matplotlib.pyplot as plt\nimport matplotlib.patches as mpatches\nimport numpy as np\n")
            f.write(code)
        
        result = subprocess.run([sys.executable, temp_script], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✓ Chart saved to {output_path}")
            return output_path
        else:
            print(f"   ⚠ Chart generation failed: {result.stderr[:200]}")
            return None
    except Exception as e:
        print(f"   ⚠ Chart generation error: {e}")
        return None


def run_editor_agent(client, draft: str) -> tuple:
    # Input validation
    if not draft or not isinstance(draft, str):
        raise ValueError(
            "[EDITOR_AGENT] Invalid draft. Expected non-empty string, "
            f"got: {type(draft).__name__}"
        )
    
    if len(draft.strip()) < 100:
        raise ValueError(
            f"[EDITOR_AGENT] Draft too short ({len(draft)} chars). "
            "Expected substantial article content (>100 chars)."
        )
    
    word_count = len(draft.split())
    print(f"📝 Editor Agent: Reviewing {word_count}-word draft against quality gates...")
    
    response = call_llm(
        client,
        EDITOR_AGENT_PROMPT.format(draft=draft),
        "Review and edit this article.",
        max_tokens=4000
    )
    
    gates_passed = response.upper().count("PASS")
    gates_failed = response.upper().count("FAIL")
    
    print(f"   Quality gates: {gates_passed} passed, {gates_failed} failed")
    
    if "## Edited Article" in response:
        edited = response.split("## Edited Article")[1].strip()
    else:
        edited = response
    
    return edited, gates_passed, gates_failed


def run_critique_agent(client, article: str) -> str:
    print("🔍 Critique Agent: Final hostile review...")
    
    critique = call_llm(
        client,
        CRITIQUE_AGENT_PROMPT.format(article=article),
        "Find any remaining flaws.",
        max_tokens=1500
    )
    issues_found = critique.lower().count("issue") + critique.lower().count("problem") + critique.lower().count("flag")
    
    if issues_found > 0:
        print(f"   ⚠ {issues_found} potential issues flagged for review")
    else:
        print("   ✓ No major issues found")
    
    return critique


def run_visual_qa_agent(client, image_path: str) -> dict:
    """Visual QA Agent: Validates chart rendering quality."""
    print("🎨 Visual QA Agent: Inspecting chart...")
    
    if not os.path.exists(image_path):
        print(f"   ⚠ Chart not found: {image_path}")
        return {"overall_pass": False, "critical_issues": ["Chart file not found"]}
    
    # Load image as base64
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    # Visual QA requires provider-specific handling for images
    if client.provider == 'anthropic':
        response_text = client.client.messages.create(
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
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": "Review this chart for visual quality issues."
                        }
                    ]
                }
            ]
        ).content[0].text
    elif client.provider == 'openai':
        response_text = client.client.chat.completions.create(
            model=client.model,
            max_tokens=2000,
            messages=[
                {
                    "role": "system",
                    "content": VISUAL_QA_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Review this chart for visual quality issues."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        }
                    ]
                }
            ]
        ).choices[0].message.content
    else:
        response_text = "{\"overall_pass\": false, \"critical_issues\": [\"Provider does not support image analysis\"]}"
    
    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            result = json.loads(response_text[start:end])
        else:
            result = {"overall_pass": False, "critical_issues": ["Failed to parse QA response"]}
    except json.JSONDecodeError:
        result = {"overall_pass": False, "critical_issues": ["JSON parse error"]}
    
    gates = result.get("gates", {})
    passed = sum(1 for g in gates.values() if g.get("pass", False))
    total = len(gates) if gates else 5
    
    print(f"   Visual gates: {passed}/{total} passed")
    
    if result.get("overall_pass"):
        print("   ✓ Chart PASSED visual QA")
    else:
        print("   ✗ Chart FAILED visual QA")
        for issue in result.get("critical_issues", [])[:3]:
            print(f"     • {issue}")
    
    return result


# ═══════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR (v3 - with governance)
# ═══════════════════════════════════════════════════════════════════════════

def generate_economist_post(topic: str, category: str = "quality-engineering", 
                            talking_points: str = "", output_dir: str = "output",
                            interactive: bool = False, governance: GovernanceTracker = None) -> dict:
    """Generate Economist-style blog post with optional human review gates"""
    print("\n" + "="*70)
    print(f"🎯 GENERATING: {topic}")
    if interactive:
        print("🚦 INTERACTIVE MODE: Approval gates enabled")
    print("="*70 + "\n")
    
    client = create_client()
    date_str = datetime.now().strftime('%Y-%m-%d')
    slug = slugify(topic, max_length=50)
    
    # Use provided output_dir
    posts_dir = Path(output_dir)
    charts_dir = posts_dir / "charts"
    
    posts_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    # Create governance tracker if not provided
    if governance is None and interactive:
        governance = GovernanceTracker(f"{output_dir}/governance")
    
    skip_approvals = False  # Set by 'skip-all' response
    
    # Stage 1: Research
    research = run_research_agent(client, topic, talking_points, governance)
    
    # Approval Gate 1: Research
    if interactive and not skip_approvals:
        verified = sum(1 for dp in research.get('data_points', []) if dp.get('verified', False))
        total = len(research.get('data_points', []))
        
        response = governance.request_approval(
            "Research Complete",
            f"Research agent gathered {total} data points ({verified} verified)",
            {
                "Unverified claims": len(research.get('unverified_claims', [])),
                "Has chart data": bool(research.get('chart_data')),
                "Review file": f"{governance.session_dir}/research_agent.json"
            }
        )
        
        if response and hasattr(governance, 'decisions') and governance.decisions[-1].get('skip_all'):
            skip_approvals = True
        elif not response:
            print("❌ Research rejected. Exiting.")
            return {"status": "rejected", "stage": "research"}
    
    # Stage 2: Graphics
    chart_path = None
    visual_qa_passed = True
    if research.get("chart_data"):
        chart_filename = str(charts_dir / f"{slug}.png")
        chart_path = run_graphics_agent(client, research["chart_data"], chart_filename)
        
        # Stage 2b: Visual QA (optional - only if vision supported)
        if chart_path and client.provider == 'anthropic':
            # Only Anthropic Claude has good vision support
            visual_qa_result = run_visual_qa_agent(client, chart_path)
            visual_qa_passed = visual_qa_result.get("overall_pass", False)
            
            if not visual_qa_passed:
                print("   ⚠ Chart failed Visual QA - flagging for manual review")
                # Save QA report for debugging
                qa_report_path = chart_path.replace('.png', '-qa-report.json')
                with open(qa_report_path, 'w') as f:
                    json.dump(visual_qa_result, f, indent=2)
            
            # Log to governance
            if governance:
                governance.log_agent_output(
                    "graphics_agent",
                    {"chart_path": chart_path, "visual_qa": visual_qa_result},
                    metadata={"passed_qa": visual_qa_passed}
                )
        elif chart_path:
            print("   ℹ Visual QA skipped (requires Anthropic Claude)")
    
    # Stage 3: Writing
    draft = run_writer_agent(client, topic, research, date_str)
    
    # Log draft to governance
    if governance:
        governance.log_agent_output(
            "writer_agent",
            {"draft": draft, "word_count": len(draft.split())},
            metadata={"topic": topic, "length": len(draft)}
        )
    
    # Approval Gate 2: Draft Review
    if interactive and not skip_approvals:
        response = governance.request_approval(
            "Draft Complete",
            f"Writer agent produced {len(draft.split())}-word draft",
            {
                "Topic": topic,
                "Preview": draft[:200] + "...",
                "Review file": f"{governance.session_dir}/writer_agent.json"
            }
        )
        
        if response and hasattr(governance, 'decisions') and governance.decisions[-1].get('skip_all'):
            skip_approvals = True
        elif not response:
            print("❌ Draft rejected. Exiting.")
            return {"status": "rejected", "stage": "draft"}
    
    # Stage 4: Editing
    
    # Stage 4: Editing
    edited_article, gates_passed, gates_failed = run_editor_agent(client, draft)
    
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
        with open(quarantine_path, 'w') as f:
            f.write(edited_article)
        
        # Save validation report
        report_path = quarantine_dir / f"{date_str}-{slug}-VALIDATION-FAILED.txt"
        with open(report_path, 'w') as f:
            f.write(validator.format_report(is_valid, validation_issues))
        
        print(f"   Quarantined to: {quarantine_path}")
        print(f"   Report saved: {report_path}")
        
        return {
            "status": "rejected",
            "reason": "validation_failed",
            "article_path": str(quarantine_path),
            "validation_report": str(report_path),
            "issues": validation_issues
        }
    else:
        print(f"   ✓ Validation PASSED ({len(validation_issues)} advisory notes)")
    
    # Save article (only if validated)
    article_path = str(posts_dir / f"{date_str}-{slug}.md")
    with open(article_path, 'w') as f:
        f.write(edited_article)
    
    if critique:
        review_path = str(posts_dir / f"{date_str}-{slug}-review.md")
        with open(review_path, 'w') as f:
            f.write(f"# Editorial Review: {topic}\n\n{critique}")
    
    print("\n" + "="*70)
    print("✅ COMPLETE")
    print(f"   Article: {article_path}")
    if chart_path:
        print(f"   Chart:   {chart_path}")
        print(f"   Visual QA: {'PASSED' if visual_qa_passed else 'FAILED - needs review'}")
    print(f"   Editorial: {gates_passed}/5 gates passed")
    print("="*70 + "\n")
    
    return {
        "article_path": article_path,
        "chart_path": chart_path,
        "gates_passed": gates_passed,
        "gates_failed": gates_failed,
        "visual_qa_passed": visual_qa_passed,
        "word_count": len(edited_article.split())
    }


# ═══════════════════════════════════════════════════════════════════════════
# CONTENT QUEUE
# ═══════════════════════════════════════════════════════════════════════════

CONTENT_QUEUE = [
    {"topic": "The Agentic AI Testing Paradox", "category": "quality-engineering", "talking_points": "adoption rates vs productivity gains, maintenance costs, vendor claims vs reality"},
    {"topic": "Self-Healing Tests: Myth vs Reality", "category": "test-automation", "talking_points": "vendor promises, actual maintenance reduction, limitations"},
    {"topic": "The Economics of Flaky Tests", "category": "quality-engineering", "talking_points": "developer time costs, CI delays, trust erosion"},
    {"topic": "Quality Metrics Executives Actually Use", "category": "quality-engineering", "talking_points": "defect escape rate, cost of quality, vanity metrics"},
    {"topic": "The Death of the QA Department", "category": "quality-engineering", "talking_points": "embedded QE, job growth despite automation"},
    {"topic": "Technical Debt's Compound Interest", "category": "software-engineering", "talking_points": "velocity degradation, refactoring ROI"},
    {"topic": "Shift-Right: The Trend Nobody Budgeted For", "category": "quality-engineering", "talking_points": "production testing costs, observability spend"},
    {"topic": "No-Code Testing's Hidden Costs", "category": "test-automation", "talking_points": "creation vs maintenance, 2am debugging"},
]


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Generate Economist-style articles with AI agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Non-interactive (automated)
  python economist_agent.py
  
  # Interactive with human review gates
  python economist_agent.py --interactive
  
  # Custom topic
  export TOPIC="The Rise of AI Testing"
  python economist_agent.py --interactive
        '''
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Enable interactive mode with approval gates between stages'
    )
    parser.add_argument(
        '--governance-dir',
        default=None,
        help='Directory for governance logs (default: output/governance)'
    )
    
    args = parser.parse_args()
    
    # Get environment variables with defaults
    topic = os.environ.get('TOPIC', '').strip()
    talking_points = os.environ.get('TALKING_POINTS', '').strip()
    category = os.environ.get('CATEGORY', 'quality-engineering').strip()
    
    # Set default output directory if not specified
    output_dir = os.environ.get('OUTPUT_DIR', '').strip()
    if not output_dir:
        output_dir = 'output'
        print(f"   ℹ OUTPUT_DIR not set, using default: {output_dir}/")
    
    # Create output directories
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(output_dir).joinpath('charts').mkdir(parents=True, exist_ok=True)
    print(f"   ✓ Output directory: {Path(output_dir).absolute()}")
    
    if not topic:
        week_num = datetime.now().isocalendar()[1]
        queued = CONTENT_QUEUE[week_num % len(CONTENT_QUEUE)]
        topic = queued['topic']
        category = queued['category']
        talking_points = queued.get('talking_points', '')
        print(f"ℹ Using queued topic: {topic}")
    
    # Create governance tracker if interactive mode
    governance = None
    if args.interactive:
        governance_dir = args.governance_dir or f"{output_dir}/governance"
        governance = GovernanceTracker(governance_dir)
        print(f"   📋 Governance tracking enabled: {governance.session_dir}")
    
    result = generate_economist_post(
        topic, category, talking_points, output_dir,
        interactive=args.interactive,
        governance=governance
    )
    
    # Generate governance report if interactive
    if governance and result.get('status') != 'rejected':
        governance.generate_report()
    
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"article_path={result.get('article_path', '')}\n")
            f.write(f"quality_score={result.get('gates_passed', 0)}/5\n")


if __name__ == "__main__":
    main()
