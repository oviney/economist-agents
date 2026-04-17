import os

from crewai import Agent, Crew, Task


def _get_crewai_llm() -> str:
    """Return CrewAI LLM string, preferring Anthropic over OpenAI."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ.get(
            "CREWAI_LLM", "anthropic/claude-sonnet-4-20250514"
        )
    return os.environ.get("CREWAI_LLM", "gpt-4o")

# Default prompt for Graphics Agent
GRAPHICS_AGENT_PROMPT = """
You are a Data Visualization Specialist.
Your goal is to take complex data and describe how it should be visualized.

Create clear, accurate charts that follow Economist style guidelines:
- Clean, minimalist design
- Proper zone boundaries (red bar, title, chart, x-axis, source)
- Inline labels instead of legends
- High-quality export (PNG, 300 DPI)
"""


class Stage3Crew:
    def __init__(self, topic: str):
        self.topic = topic
        self._setup_agents()
        self._setup_tasks()

    def _setup_agents(self):
        # Create backstories without template variables (CrewAI requirement)
        research_backstory = """You are a Research Analyst preparing comprehensive briefing packs for Economist-style articles.

Mandatory skill reference: skills/research-sourcing/SKILL.md — your source quality standards.

Your expertise includes:
- Gathering and verifying data from authoritative sources, prioritising 2025-2026 publications
- Identifying compelling statistics with proper attribution
- Flagging unverified claims and data inconsistencies
- Structuring research into actionable insights

SOURCE FRESHNESS (non-negotiable):
- At least 3 of 5 references must come from 2025 or 2026
- No more than 1 reference from an analyst firm (Gartner, Forrester, Capgemini, McKinsey, BCG)
- Use arXiv, IEEE/ACM proceedings, and company engineering blogs for fresh, diverse sources
- Zero references from before 2022 unless citing an irreplaceable foundational study

SOURCE DIVERSITY:
Include at least 3 of: primary research, named company case study, academic/conference paper,
industry practitioner blog (Netflix/Google/Spotify/etc), analyst report (max 1).

You prioritize primary sources over secondary sources and always document the provenance of data."""

        writer_backstory = """You are an Economist-style Writer renowned for sharp, witty prose with British flair.
Your definitive style reference is skills/economist-writing/SKILL.md — every article must satisfy all 10 rules
defined there before submission.

STRUCTURE RULES (from skills/economist-writing/SKILL.md):
- State a specific, debatable THESIS in the first two paragraphs — not a topic, an argument
- Use 3-4 headings maximum (one per 250-350 words); headings must be noun phrases that advance the argument
- End with a vivid prediction, metaphor, or provocation — never a summary

TITLE RULES:
- Provocative and memorable; use a colon for a surprising twist
- BANNED title patterns: starting with "Why" or "How", "The Impact of", "The Role of", purely descriptive titles

BANNED OPENINGS (never start an article with these):
- "In today's world", "It's no secret", "The arrival/emergence/rise of", "When it comes to", "Amidst"
- Any sentence starting with "The" followed by an abstract noun

BANNED IN BODY — NO LISTS:
- Numbered lists (1., 2., 3.), bulleted lists (-, *), "The following steps", "Here are N ways"

BANNED HEDGING PHRASES:
- "it would be misguided", "one might", "it is worth noting", "it is not a minor footnote"
- "it should be noted", "it is important to", "further complicating matters"
- "invites closer scrutiny", "in practical terms"
- "game-changer", "paradigm shift", "leverage" (as verb)

BANNED GENERIC ATTRIBUTION — NAME NAMES:
- "organisations" (use the company name), "professionals" (use the role: "engineers at Google")
- "studies show" (name the study), "experts say" (name the expert), "research indicates" (cite the paper)
- Every article must include at least 2 named companies or individuals with specific anecdotes

BANNED CLOSINGS:
- "will rest on", "depends on", "the key is", "In conclusion", "To summarise"
- "Only time will tell", "remains to be seen"
- Any sentence that restates the thesis without adding new insight

VOICE (British, confident, witty):
- British spelling throughout: organisation, analyse, colour, favour
- Active voice: "Companies are racing" not "it is being observed that"
- Reads like a brilliant dinner companion, not a textbook

You validate your work against all 10 rules in skills/economist-writing/SKILL.md before submission."""

        graphics_backstory = """You are a Data Visualization Specialist creating Economist-style charts.

Your standards:
- Clean, minimalist design with clear zone boundaries
- Red bar at top (4% height)
- Title and subtitle below red bar
- Chart area with inline labels (no legends)
- X-axis zone with proper spacing
- Source attribution at bottom
- Navy (#17648d) and burgundy (#843844) color palette
- High-quality PNG export (300 DPI)"""

        editor_backstory = """You are a Quality Editor enforcing Economist editorial standards through 5 quality gates.

Your gates:
1. OPENING: Strong hook, no throat-clearing
2. EVIDENCE: All statistics properly sourced
3. VOICE: British spelling, active voice, banned phrases avoided
4. STRUCTURE: Logical flow, strong ending
5. CHART INTEGRATION: Charts naturally embedded and referenced

You provide explicit PASS/FAIL decisions with rationale for each gate."""

        llm = _get_crewai_llm()
        self.research_agent = Agent(
            role="Research Analyst",
            goal="Gather, verify, and compile researched facts and sources to support article creation",
            backstory=research_backstory,
            llm=llm,
        )
        self.writer_agent = Agent(
            role="Economist-style Writer",
            goal="Compose an Economist-style article based on researched data, following strict writing and style guidelines",
            backstory=writer_backstory,
            llm=llm,
        )
        self.graphics_agent = Agent(
            role="Data Visualization Specialist",
            goal="Generate charts and visuals that adhere to layout zones, styles and export integrity requirements",
            backstory=graphics_backstory,
            llm=llm,
        )
        self.editor_agent = Agent(
            role="Quality Editor",
            goal="Apply quality gates: review sourcing, voice, logical structure, and chart integration before approval",
            backstory=editor_backstory,
            llm=llm,
        )
        self.agents = [
            self.research_agent,
            self.writer_agent,
            self.graphics_agent,
            self.editor_agent,
        ]

    def _setup_tasks(self):
        # Research task - gather & verify facts
        self.research_task = Task(
            description="Gather, verify, and compile researched facts and sources to support article creation for the topic: {topic}",
            agent=self.research_agent,
            expected_output="A structured research report with verified facts, statistics, and properly attributed sources",
        )

        # Writing task - write Economist-style article
        self.writer_task = Task(
            description="""Write the complete, full-text Economist-style article following ALL rules in skills/economist-writing/SKILL.md.
Output the ENTIRE article text with YAML frontmatter at the top.

DO NOT describe the article or summarize what it contains.
DO NOT say "Above is..." or "Here is..." or reference the article.
OUTPUT the actual article text directly, starting with:
---
layout: post
title: "Your Title"
date: YYYY-MM-DD
author: "The Economist"
categories: ["quality-engineering"]
image: /assets/images/SLUG.png
summary: "One-sentence summary of the article"
---

IMPORTANT for categories: Choose 1-3 from: quality-engineering, software-engineering, test-automation, security. Categories MUST be kebab-case.
IMPORTANT for image: Replace SLUG with a lowercase-hyphenated version of the title (e.g., "ai-testing-costs").

Then the full article body (minimum 800 words) following these MANDATORY rules:

THESIS: State a specific, debatable argument in the first two paragraphs.
TITLE: Provocative and memorable — use a colon for a twist. No "Why/How/The Impact of" openings.
OPENING: Start with a striking concrete claim or surprising statistic. No abstract openings.
STRUCTURE: Use 3-4 headings maximum as noun phrases (e.g., "The maintenance trap"). No questions as headings.
LISTS: No numbered or bulleted lists anywhere in the body.
AUTHORITY: No hedging phrases ("one might", "it is worth noting", "it would be misguided").
NAMES: Include at least 2 named companies or individuals with specific anecdotes. No "organisations" or "experts say".
ENDING: Close with a vivid prediction, metaphor, or provocation. No summaries or "In conclusion".

MANDATORY: End with a "## References" section containing at least 3 numbered, properly cited sources.
Example:
## References
1. Author/Org, ["Report Title"](https://example.com), *Publication*, Year
2. ...
3. ...

Use British spelling, sharp wit, verified sources, and natural chart references.""",
            agent=self.writer_agent,
            expected_output="The complete article text in full, with YAML frontmatter header (---\ntitle:\ndate:\nauthor:\nsummary:\n---) followed by the entire article body (minimum 800 words) with thesis in first two paragraphs, 3-4 headings maximum, no lists, named companies/people, vivid ending, ending with a ## References section (minimum 3 sources)",
            context=[self.research_task],  # Access research findings
        )

        # Graphics task - generate structured chart dict
        self.graphics_task = Task(
            description="""Create a structured chart data dictionary with data points for visualization. Output ONLY a Python dict structure.

DO NOT create a text specification or markdown document.
DO NOT use headers like "**Chart Title:**" or tables.
DO NOT include explanatory text or formatting instructions.
OUTPUT a JSON-serializable dict with this structure:

{
    "title": "Chart title here",
    "subtitle": "Subtitle here",
    "data": [
        {"metric": "Market CAGR", "value": 23.2, "unit": "%", "color": "burgundy"},
        {"metric": "Adoption Outlook", "value": 30, "unit": "%", "color": "navy"},
        {"metric": "Time Reduction", "value": 70, "unit": "%", "color": "burgundy"},
        {"metric": "Flaky Test Reduction", "value": 78, "unit": "%", "color": "navy"}
    ],
    "colors": {"navy": "#17648d", "burgundy": "#843844"},
    "dimensions": {"width": 1200, "height": 675}
}

Include ALL data points from the research (Market CAGR 23.2%, Adoption 30%, Time Reduction 70%, Flaky Tests 78%). Use Economist color palette (navy #17648d, burgundy #843844).""",
            agent=self.graphics_agent,
            expected_output="A Python dictionary with 'title', 'subtitle', 'data' list of metric objects (each with metric/value/unit/color keys), 'colors' dict mapping color names to hex codes, and 'dimensions' dict with width/height",
            context=[
                self.research_task,
                self.writer_task,
            ],  # Access research and article content
        )

        # Editing task - quality gate review
        self.editor_task = Task(
            description="Apply quality gates: review sourcing, voice, logical structure, and chart integration before approval. Validate all statistics are properly sourced and British spelling is used throughout.",
            agent=self.editor_agent,
            expected_output="Final approved article with quality gate assessment indicating PASS/FAIL for each gate and publication decision",
            context=[
                self.writer_task,
                self.graphics_task,
            ],  # Access article and chart specs
        )

        self.tasks = [
            self.research_task,
            self.writer_task,
            self.graphics_task,
            self.editor_task,
        ]

    def kickoff(self) -> dict:
        from datetime import datetime

        # Initial input data with current_date for Writer Agent template
        inputs = {
            "topic": self.topic,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
        }

        # Execute the crew workflow with agents and tasks
        crew = Crew(agents=self.agents, tasks=self.tasks)
        crew_output = crew.kickoff(inputs=inputs)

        # CrewAI returns CrewOutput object - extract task outputs
        # Tasks execute in order: [0] research, [1] writer, [2] graphics, [3] editor
        # We need writer output (index 1) for article and graphics output (index 2) for chart_data
        if hasattr(crew_output, "tasks_output") and len(crew_output.tasks_output) >= 3:
            writer_output = crew_output.tasks_output[1].raw
            graphics_output = crew_output.tasks_output[2].raw

            # Parse graphics_output - if it's a JSON string, parse it to dict
            try:
                import json

                chart_data = (
                    json.loads(graphics_output)
                    if isinstance(graphics_output, str)
                    else graphics_output
                )
            except (json.JSONDecodeError, ValueError):
                # If parsing fails, wrap as specification
                chart_data = {"specification": graphics_output}

            return {"article": writer_output, "chart_data": chart_data}
        else:
            # Fallback: use raw output as article, empty chart_data
            return {
                "article": str(crew_output.raw)
                if hasattr(crew_output, "raw")
                else str(crew_output),
                "chart_data": {},
            }
