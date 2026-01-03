#!/usr/bin/env python3
"""
Writer Agent Module

Extracts writer agent functionality from economist_agent.py
for improved modularity and testability.
"""

import sys
from pathlib import Path
from typing import Any

try:
    import orjson  # noqa: F401

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

import json as json_stdlib  # Always have standard json for formatting

# Add scripts directory to path for imports
_scripts_dir = Path(__file__).parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from agent_reviewer import review_agent_output  # type: ignore  # noqa: E402
from governance import GovernanceTracker  # type: ignore  # noqa: E402
from llm_client import call_llm  # type: ignore  # noqa: E402

# ═══════════════════════════════════════════════════════════════════════════
# WRITER AGENT PROMPT
# ═══════════════════════════════════════════════════════════════════════════

WRITER_AGENT_PROMPT = """⚠️  CRITICAL: Today's date is {current_date}. You MUST use this exact date in the YAML front matter.

You are a senior writer at The Economist, crafting an article on quality engineering.

═══════════════════════════════════════════════════════════════════════════
ECONOMIST VOICE - MANDATORY RULES
═══════════════════════════════════════════════════════════════════════════

STRUCTURE (800-1200 words):
1. OPENING: Lead with most striking fact. NO throat-clearing. NO "In today's world..."
2. BODY: 3-4 sections, each advancing the argument. Use ## headers (noun phrases, not questions)
3. CHART EMBEDDING (MANDATORY if chart_data provided):
   ⚠️  CRITICAL VALIDATION CHECKLIST:
   □ Chart markdown ![...](path) MUST appear in article body
   □ Chart MUST be referenced in surrounding text ("As the chart shows...")
   □ Chart placement: After the section discussing the data
   □ DO NOT use "See figure 1" or "The chart below" - reference naturally

   CHART EMBEDDING PATTERN:
   ```markdown
   [Paragraph discussing data...]

   ![Chart title](chart_filename.png)

   As the chart shows, [insight from visualization].
   ```

   ❌ WRONG: Writing article without embedding chart when chart_data provided
   ✅ CORRECT: Chart embedded with natural text reference

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
PRE-OUTPUT SELF-VALIDATION (GREEN SOFTWARE: AVOID REWORK)
═══════════════════════════════════════════════════════════════════════════

⚠️  CRITICAL: Validate BEFORE returning output to avoid wasteful regeneration.
Every regeneration = unnecessary compute, token waste, carbon footprint.

**VALIDATION CHECKLIST** (Run this mental check NOW, before outputting):

**Chart Validation** (if chart_data provided):
□ 1. Chart markdown ![...](filename.png) appears in article body?
□ 2. Chart referenced in text ("As the chart shows...") not just embedded?
□ 3. Chart filename matches research brief?

**Opening Validation**:
□ 4. First sentence contains striking DATA/FACT (not context)?
□ 5. NO banned openings ("In today's world", "It's no secret", "Amidst")?

**Style Validation**:
□ 6. British spelling (organisation, favour, analyse) throughout?
□ 7. NO banned phrases ("game-changer", "leverage", "paradigm shift")?
□ 8. NO exclamation points anywhere?

**Closing Validation**:
□ 9. Closing makes PREDICTION/IMPLICATION (not summary)?
□ 10. NO banned closings ("In conclusion", "remains to be seen")?

**Format Validation**:
□ 11. YAML uses --- delimiters (NOT ```yaml)?
□ 12. Date is {current_date} (NOT dates from research sources)?

═══════════════════════════════════════════════════════════════════════════
⚠️  GREEN SOFTWARE COMMITMENT:
If ANY checkbox above fails → FIX IT NOW before returning output.
Do NOT return flawed output that requires regeneration.
First-time-right = zero token waste = sustainable AI.
═══════════════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════════════════
YOUR RESEARCH BRIEF:
{research_brief}
═══════════════════════════════════════════════════════════════════════════

Write the article now. Return complete Markdown with YAML frontmatter.

⚠️  CRITICAL FORMAT REQUIREMENTS:

1. DATE: Use TODAY'S DATE ({current_date}), NOT dates from research sources
2. YAML: Use --- delimiters, NOT ```yaml code fences
3. TITLE: Must be specific with context, NOT generic
4. LAYOUT: MUST include "layout: post" for Jekyll rendering

Correct format:
---
layout: post
title: "Self-Healing Tests: Myth vs Reality"
date: {current_date}
author: "The Economist"
---

[Article content here]

WRONG formats (DO NOT USE):
```yaml          ← NO code fences
title: "Myth vs Reality"  ← Too generic
date: 2023-11-09          ← Wrong date
---
title: "Article"  ← MISSING layout field - page won't render properly!
date: {current_date}
---
```

═══════════════════════════════════════════════════════════════════════════
REFERENCES SECTION - MANDATORY
═══════════════════════════════════════════════════════════════════════════

All articles MUST include a "## References" section before the closing paragraph.

**Reference Format** (Economist style):
- Author/Organization, "Title", *Publication*, Date
- Links use descriptive anchor text (NOT "click here" or bare URLs)
- Minimum 3 authoritative sources required
- List references in order of appearance in article

**Example References Section**:
```markdown
## References

1. Gartner, ["World Quality Report 2024"](https://www.gartner.com/report), *Gartner Research*, November 2024
2. Forrester, ["The State of Test Automation"](https://www.forrester.com/report), *Forrester Research*, September 2024
3. IEEE, ["Software Testing Best Practices"](https://www.ieee.org/testing), *IEEE Computer Society*, August 2024
```

**Critical Validation**:
□ References section present before closing
□ All statistics in article have corresponding reference
□ Links use descriptive anchor text
□ Minimum 3 sources cited

⚠️  Articles without references section will be REJECTED by Publication Validator.

═══════════════════════════════════════════════════════════════════════════

⚠️  REMINDER: Run the 12-point validation checklist above BEFORE outputting.
Green software = first-time-right quality = zero regeneration waste.

Now write the article:"""


# ═══════════════════════════════════════════════════════════════════════════
# WRITER AGENT CLASS
# ═══════════════════════════════════════════════════════════════════════════


class WriterAgent:
    """Writer agent for drafting Economist-style articles.

    This agent focuses on:
    - Writing engaging, data-driven articles
    - Following Economist style guidelines
    - Embedding charts naturally
    - Self-validation before returning drafts

    Args:
        client: LLM client instance (from llm_client.create_llm_client())
        governance: Optional governance tracker for audit logging

    Example:
        >>> from llm_client import create_llm_client
        >>> client = create_llm_client()
        >>> agent = WriterAgent(client)
        >>> draft, metadata = agent.write(
        ...     topic="AI Testing Trends",
        ...     research_brief={...},
        ...     current_date="2026-01-02"
        ... )
    """

    def __init__(self, client: Any, governance: GovernanceTracker | None = None):
        """Initialize the writer agent.

        Args:
            client: LLM client for generating articles
            governance: Optional governance tracker for logging
        """
        self.client = client
        self.governance = governance

    def write(
        self,
        topic: str,
        research_brief: dict[str, Any],
        current_date: str,
        chart_filename: str | None = None,
        featured_image: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Write an Economist-style article based on research brief.

        Args:
            topic: Article topic
            research_brief: Research data from research agent
            current_date: Date to use in YAML frontmatter (YYYY-MM-DD)
            chart_filename: Optional chart filename to embed
            featured_image: Optional featured image path

        Returns:
            Tuple of (article_text, metadata_dict)
            - article_text: Complete markdown with YAML frontmatter
            - metadata_dict: Validation results
                * is_valid: Whether draft passed validation
                * regenerated: Whether draft was regenerated
                * critical_issues: Count of critical issues found

        Raises:
            ValueError: If inputs are invalid

        Example:
            >>> draft, metadata = agent.write(
            ...     topic="Self-Healing Tests",
            ...     research_brief={"headline_stat": {...}, ...},
            ...     current_date="2026-01-02",
            ...     chart_filename="/assets/charts/testing.png"
            ... )
            >>> print(f"Valid: {metadata['is_valid']}")
            >>> print(f"Word count: {len(draft.split())}")
        """
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

        # Build system prompt by replacing placeholders
        system_prompt = WRITER_AGENT_PROMPT.replace("{current_date}", current_date)

        # Add chart information if available
        if chart_filename and research_brief.get("chart_data"):
            chart_title = research_brief["chart_data"].get("title", "Chart")
            chart_info = f"""

═══════════════════════════════════════════════════════════════════════════
⚠️  CHART EMBEDDING REQUIRED ⚠️
═══════════════════════════════════════════════════════════════════════════

A chart has been generated for this article. You MUST include it using this EXACT markdown:

![{chart_title}]({chart_filename})

Place this markdown in the article body after discussing the relevant data.
Add a sentence referencing it: "As the chart shows, [observation]..."

Failure to include the chart will result in article rejection.
═══════════════════════════════════════════════════════════════════════════
"""
            system_prompt = system_prompt.replace(
                "{research_brief}",
                json_stdlib.dumps(research_brief, indent=2) + chart_info,
            )
        else:
            system_prompt = system_prompt.replace(
                "{research_brief}", json_stdlib.dumps(research_brief, indent=2)
            )

        # Add references information from research data
        references_info = self._format_references_guidance(research_brief)
        if references_info:
            system_prompt += references_info

        # Add featured image to front matter if available
        if featured_image:
            featured_image_note = f"""

⚠️  FEATURED IMAGE AVAILABLE ⚠️
Add this line to the YAML front matter:
image: {featured_image}

Example:
---
layout: post
title: "Article Title"
date: {current_date}
author: "The Economist"
image: {featured_image}
---
"""
            system_prompt += featured_image_note

        # Generate initial draft
        draft = call_llm(
            self.client,
            system_prompt,
            f"⚠️  REMEMBER: Use date: {current_date} in YAML front matter.\n\nWrite an Economist-style article on: {topic}",
            max_tokens=3000,
        )
        word_count = len(draft.split())
        print(f"   ✓ Draft complete ({word_count} words)")

        # SELF-VALIDATION: Review draft before returning
        print("   🔍 Self-validating draft...")
        is_valid, issues = review_agent_output(
            "writer_agent", draft, context={"chart_filename": chart_filename}
        )

        critical_issues = []
        # If validation fails and issues are critical, attempt one regeneration
        if not is_valid:
            critical_issues = [i for i in issues if "CRITICAL" in i or "BANNED" in i]
            if critical_issues:
                print(
                    f"   ⚠️  {len(critical_issues)} critical issues found, regenerating..."
                )

                # Create fix instructions from issues
                fix_instructions = "\n".join(
                    [
                        "CRITICAL FIXES REQUIRED:",
                        *[
                            f"- {issue}" for issue in critical_issues[:5]
                        ],  # Top 5 issues
                        "\nRegenerate the article with these fixes applied.",
                    ]
                )

                # Regenerate with fix instructions
                draft = call_llm(
                    self.client,
                    system_prompt + "\n\n" + fix_instructions,
                    f"Fix the issues and regenerate: {topic}",
                    max_tokens=3000,
                )

                # Re-validate
                is_valid, issues = review_agent_output(
                    "writer_agent", draft, context={"chart_filename": chart_filename}
                )

                if not is_valid:
                    print(
                        f"   ⚠️  Draft still has {len(issues)} issues after regeneration"
                    )
                else:
                    print("   ✅ Regenerated draft passed validation")
            else:
                print(f"   ⚠️  Draft has {len(issues)} warnings (non-critical)")
        else:
            print("   ✅ Draft passed self-validation")

        # Log to governance if available
        if self.governance:
            self.governance.log_agent_output(
                "writer_agent",
                {"draft": draft, "word_count": len(draft.split())},
                metadata={
                    "topic": topic,
                    "length": len(draft),
                    "is_valid": is_valid,
                    "regenerated": bool(not is_valid and critical_issues),
                },
            )

        # Return draft with validation metadata
        return draft, {
            "is_valid": is_valid,
            "regenerated": bool(not is_valid and critical_issues),
            "critical_issues": len(critical_issues) if not is_valid else 0,
        }

    def _format_references_guidance(self, research_brief: dict[str, Any]) -> str:
        """Format references guidance from research data sources.

        Extracts sources from research brief and formats them as
        reference examples for the Writer Agent to follow.

        Args:
            research_brief: Research data with data_points containing sources

        Returns:
            Formatted guidance string or empty string if no sources
        """
        sources = []

        # Extract sources from data_points
        for dp in research_brief.get("data_points", []):
            if dp.get("source") and dp.get("verified", False):
                source_entry = {
                    "source": dp["source"],
                    "year": dp.get("year", "2024"),
                    "url": dp.get("url", ""),
                }
                # Avoid duplicates
                if source_entry not in sources:
                    sources.append(source_entry)

        # Extract source from headline_stat
        if research_brief.get("headline_stat"):
            hs = research_brief["headline_stat"]
            if hs.get("source") and hs.get("verified", False):
                source_entry = {
                    "source": hs["source"],
                    "year": hs.get("year", "2024"),
                    "url": "",
                }
                if source_entry not in sources:
                    sources.insert(0, source_entry)  # Headline source first

        if not sources:
            return ""

        # Format references guidance
        guidance = [
            "\n",
            "═══════════════════════════════════════════════════════════════════════════",
            "⚠️  REFERENCES SOURCES AVAILABLE ⚠️",
            "═══════════════════════════════════════════════════════════════════════════",
            "",
            "The Research Agent has verified these sources. Include them in your References section:",
            "",
        ]

        for i, src in enumerate(sources[:5], 1):  # Max 5 sources
            source_name = src["source"]
            year = src["year"]
            url = src.get("url", "")

            if url:
                guidance.append(
                    f"{i}. {source_name}, [source title/report name], *Publication*, {year}"
                )
                guidance.append(f"   URL: {url}")
            else:
                guidance.append(
                    f"{i}. {source_name}, [report/study name], *Publication*, {year}"
                )

        guidance.extend(
            [
                "",
                "Format these as proper references in your '## References' section.",
                "Use descriptive link text, not generic 'click here'.",
                "═══════════════════════════════════════════════════════════════════════════",
            ]
        )

        return "\n".join(guidance)


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════


def run_writer_agent(
    client: Any,
    topic: str,
    research_brief: dict[str, Any],
    current_date: str,
    chart_filename: str | None = None,
    featured_image: str | None = None,
    governance: GovernanceTracker | None = None,
) -> tuple[str, dict[str, Any]]:
    """Run the writer agent (backward compatibility wrapper).

    This function maintains 100% backward compatibility with the original
    economist_agent.py implementation.

    Args:
        client: LLM client instance
        topic: Article topic
        research_brief: Research data dictionary
        current_date: Date for YAML frontmatter
        chart_filename: Optional chart filename to embed
        featured_image: Optional featured image path
        governance: Optional governance tracker

    Returns:
        Tuple of (article_text, metadata_dict)

    Example:
        >>> from llm_client import create_llm_client
        >>> client = create_llm_client()
        >>> draft, metadata = run_writer_agent(
        ...     client,
        ...     "AI Testing",
        ...     {"headline_stat": {...}},
        ...     "2026-01-02"
        ... )
    """
    agent = WriterAgent(client, governance)
    return agent.write(
        topic=topic,
        research_brief=research_brief,
        current_date=current_date,
        chart_filename=chart_filename,
        featured_image=featured_image,
    )
