#!/usr/bin/env python3
"""
Stage 4 Crew - Review and Final Editorial Polish

This crew represents the final review stage after Stage 3 (Research + Writing + Graphics + Initial Edit).
Stage 4 focuses on:
- Final editorial review with strict Economist standards
- Style compliance validation (no banned phrases, proper structure)
- Quality gate enforcement (>95% pass rate requirement)
- Publication readiness assessment

Architecture:
    Stage 3 Output (YAML/JSON) → Stage 4 Reviewer → Final Editor → Polished Article
"""

import re
from typing import Any

from crewai import Agent, Crew, Task
from crewai.tools import tool

from src.tools.style_memory_tool import create_style_memory_tool


# Initialize Style Memory Tool for Editor Agent
@tool("Style Memory Query")
def style_memory_query_tool(query: str) -> str:
    """
    Query Style Memory for relevant Economist style patterns from Gold Standard articles.

    Use this tool when evaluating GATE 3 (VOICE) to find concrete examples of:
    - Proper Economist voice and tone
    - British spelling patterns
    - Sentence structure examples
    - How to handle specific phrasings

    Args:
        query: Natural language query (e.g., "banned phrases examples", "British spelling patterns")

    Returns:
        Formatted string with top 3 relevant style examples from archived articles

    Example:
        result = style_memory_query_tool("how to write strong openings")
    """
    tool_func = create_style_memory_tool()
    return tool_func(query)


class Stage4Crew:
    """
    Stage 4: Final Review and Editorial Polish

    Agents:
        1. Reviewer Agent - Applies 5 quality gates to Stage 3 output
        2. Final Editor Agent - Polish and style enforcement

    Input: Stage 3 output dict with 'article' and 'chart_data'
    Output: dict with refined article, editorial score, and publication status
    """

    def __init__(self):
        """Initialize Stage 4 Crew with reviewer and editor agents"""
        self.reviewer_agent = self._create_reviewer_agent()
        self.final_editor_agent = self._create_final_editor_agent()
        self.review_task = self._create_review_task()
        self.polish_task = self._create_polish_task()

        self.crew = Crew(
            agents=[self.reviewer_agent, self.final_editor_agent],
            tasks=[self.review_task, self.polish_task],
            verbose=True,
        )

    def _create_reviewer_agent(self) -> Agent:
        """
        Reviewer Agent - Applies 5 quality gates from Economist editorial standards

        Quality Gates (extracted from agents/editor_agent.py):
        1. OPENING - Hook quality, no throat-clearing
        2. EVIDENCE - All statistics sourced, no weasel phrases
        3. VOICE - British spelling, active voice, Economist style
        4. STRUCTURE - Logical flow, strong ending (no "in conclusion")
        5. CHART INTEGRATION - Chart embedded and referenced naturally
        """
        return Agent(
            role="Editorial Reviewer",
            goal="Apply 5 quality gates to ensure article meets Economist standards with >95% pass rate",
            backstory="""You are a senior editorial reviewer at The Economist with 15 years experience.

You enforce the publication's strict quality standards through 5 quality gates:
1. **OPENING**: First sentence must hook with striking fact/data. No throat-clearing ("In today's world...")
2. **EVIDENCE**: Every statistic must have named source. No "studies show" without citation.
3. **VOICE**: British spelling (organisation, analyse). Active voice. No banned phrases (game-changer, leverage as verb).
4. **STRUCTURE**: Logical flow, ruthless cutting of redundancy. Ending must predict/imply, never summarize.
5. **CHART INTEGRATION**: If chart exists, must be embedded in markdown and referenced naturally.

Your pass rate must exceed 95% (4.75/5 gates minimum).

BANNED OPENINGS: "In today's world", "It's no secret", "When it comes to", "Amidst"
BANNED CLOSINGS: "In conclusion", "To conclude", "remains to be seen", "only time will tell"
BANNED PHRASES: "game-changer", "paradigm shift", "leverage" (as verb), "at the end of the day"

You are ruthlessly precise. Vague feedback is unacceptable.""",
            verbose=True,
            allow_delegation=False,
        )

    def _create_final_editor_agent(self) -> Agent:
        """
        Final Editor - Applies reviewer feedback and polishes for publication

        This agent:
        - Executes specific edits from reviewer feedback
        - Removes banned phrases/patterns
        - Strengthens weak verbs
        - Ensures British spelling throughout
        - Validates final article structure
        """
        return Agent(
            role="Final Editor",
            goal="Polish article to publication-ready state by applying reviewer feedback and enforcing style guide",
            backstory="""You are The Economist's final copy editor before publication.

Your responsibilities:
- Execute ALL edits from the reviewer's quality gate feedback
- Remove banned phrases: "game-changer", "paradigm

**TOOL AVAILABLE**: You have access to Style Memory Tool via style_memory_query_tool(query).
Use this to find concrete style examples when applying edits:
- Query relevant patterns for specific edits
- Reference Gold Standard examples for style consistency
- Validate editorial choices against archived articles""",
            verbose=True,
            allow_delegation=False,
            tools=[style_memory_query_tool],
        )

        # Create Editor Agent
        self.editor_agent = Agent(
            role="Chief Editor",
            goal="""Edit articles to meet The Economist's exacting standards while preserving author voice and data integrity.""",
            backstory="""You are the Chief Editor at The Economist with 20 years experience.
You enforce house style ruthlessly but fairly, improving clarity without sacrificing substance.

CRITICAL EDITS (ALWAYS CHECK):
- Cut banned closings: "In conclusion", "To conclude", "In summary", "remains to be seen"
- Strengthen weak verbs: "is experiencing growth" → "is growing"
- Apply British spelling: organization → organisation, analyze → analyse
- Remove exclamation points
- Ensure chart embedding if chart_data present

You catch what others miss. No article goes to print without your approval.

Quality standard: Editorial score must be ≥95/100.""",
            verbose=True,
            allow_delegation=False,
        )

    def _create_review_task(self) -> Task:
        """Create review task for quality gate assessment"""
        return Task(
            description="""Review article from Stage 3 against 5 quality gates.

INPUT: Article with YAML frontmatter and chart_data

QUALITY GATES TO CHECK:
1. OPENING - First sentence hooks? No throat-clearing?
2. EVIDENCE - All statistics sourced? No [NEEDS SOURCE] flags?
3. VOICE - British spelling? No banned phrases? Active voice?
4. STRUCTURE - Logical flow? Strong ending (no "in conclusion")?
5. CHART INTEGRATION - Chart embedded if chart_data exists? Referenced naturally?

OUTPUT FORMAT (JSON):
{
    "gates_passed": <number 0-5>,
    "gate_1_opening": {"pass": true/false, "issue": "..."},
    "gate_2_evidence": {"pass": true/false, "issue": "..."},
    "gate_3_voice": {"pass": true/false, "issue": "..."},
    "gate_4_structure": {"pass": true/false, "issue": "..."},
    "gate_5_chart": {"pass": true/false, "issue": "..."},
    "editorial_score": <number 0-100>,
    "specific_edits": ["Edit 1", "Edit 2", ...]
}

CRITICAL: gates_passed must be ≥4.75 (95% pass rate)""",
            expected_output="JSON object with gate results and specific edit recommendations",
            agent=self.reviewer_agent,
        )

    def _create_polish_task(self) -> Task:
        """Create polish task for final editorial refinement"""
        return Task(
            description="""Apply reviewer feedback to polish article to publication standard.

INPUTS:
- Original article from Stage 3
- Reviewer's gate assessment with specific_edits list

ACTIONS:
1. Execute ALL edits from reviewer's specific_edits list
2. Remove banned phrases: "game-changer", "paradigm shift", "leverage" (verb)
3. Remove banned openings: "In today's", "It's no secret", "When it comes"
4. Remove banned closings: "In conclusion", "To conclude", "remains to be seen"
5. Apply British spelling: -ize → -ise, -or → -our where appropriate
6. Remove all exclamation points
7. Strengthen weak verbs: "is experiencing" → present tense
8. Ensure chart markdown present if chart_data exists
9. Validate YAML frontmatter intact

OUTPUT FORMAT (JSON):
{
    "article": "<polished article with YAML frontmatter>",
    "editorial_score": <number 0-100>,
    "gates_passed": <number 0-5>,
    "publication_ready": true/false,
    "reviewer_feedback": "<summary of what was changed>"
}

CRITICAL: editorial_score must be ≥95 for publication_ready=true""",
            expected_output="JSON object with polished article and quality metrics",
            agent=self.final_editor_agent,
        )

    def kickoff(self, stage3_input: dict[str, Any]) -> dict[str, Any]:
        """
        Execute Stage 4 review and polish pipeline

        Args:
            stage3_input: dict with 'article' (str) and 'chart_data' (dict)

        Returns:
            dict with refined article, editorial_score, gates_passed, publication_ready
        """
        # Validate Stage 3 input structure
        if not isinstance(stage3_input, dict):
            raise ValueError("stage3_input must be a dictionary")
        if "article" not in stage3_input:
            raise ValueError("stage3_input must contain 'article' key")

        article = stage3_input["article"]
        chart_data = stage3_input.get("chart_data", {})

        # Store context for agents
        self.review_task.context = {"article": article, "chart_data": chart_data}
        self.polish_task.context = {"article": article, "chart_data": chart_data}

        # Execute crew (review → polish)
        crew_output = self.crew.kickoff()

        # Parse result - CrewOutput object has .raw attribute with final output
        import json

        result_str = (
            str(crew_output.raw) if hasattr(crew_output, "raw") else str(crew_output)
        )

        try:
            # Try direct JSON parse
            parsed_result = json.loads(result_str)
        except (json.JSONDecodeError, ValueError):
            # Fallback: extract JSON from text if wrapped
            json_match = re.search(r"\{.*\}", result_str, re.DOTALL)
            if json_match:
                try:
                    parsed_result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    # Emergency fallback: return original with metadata
                    parsed_result = {
                        "article": article,
                        "editorial_score": 0,
                        "gates_passed": 0,
                        "publication_ready": False,
                        "reviewer_feedback": "Failed to parse crew output",
                    }
            else:
                # Emergency fallback
                parsed_result = {
                    "article": article,
                    "editorial_score": 0,
                    "gates_passed": 0,
                    "publication_ready": False,
                    "reviewer_feedback": "Failed to extract JSON from crew output",
                }

        return parsed_result


if __name__ == "__main__":
    # Quick test
    print("Stage4Crew initialized")
    crew = Stage4Crew()
    print(f"Agents: {len(crew.crew.agents)}")
    print(f"Tasks: {len(crew.crew.tasks)}")
