# Economist Blog Agent Instructions

## Project Overview
This is a multi-agent AI system designed to produce publication-quality blog posts in the style of *The Economist*. It uses a pipeline of specialized agents (Topic Scout, Editorial Board, Researcher, Writer, Editor, Graphics) to ensure high-quality, rigorous, and stylistically consistent output.

## Architecture & Data Flow
The system operates in a 3-stage pipeline:
1.  **Discovery**: `topic_scout.py` scans for topics and outputs candidates.
2.  **Editorial Board**: `editorial_board.py` uses a swarm of personas (VP of Eng, Data Skeptic, etc.) to vote on and select the best topics.
3.  **Generation**: `economist_agent.py` orchestrates the creation of the article, including research, writing, and editing.
    *   **Charts**: `generate_chart.py` produces "Economist-style" visualizations using `matplotlib`.
    *   **Output**: Final articles are saved as Markdown files in `_posts/` for Jekyll processing.

## Key Components & Files
*   `scripts/economist_agent.py`: Main orchestrator. Contains `RESEARCH_AGENT_PROMPT` and `WRITER_AGENT_PROMPT`.
*   `scripts/editorial_board.py`: Implements the voting swarm with `BOARD_MEMBERS` personas.
*   `scripts/generate_chart.py`: Chart generation logic with specific style constraints.
*   `_posts/`: Directory for generated blog posts.
*   `assets/charts/`: Directory for generated chart images.

## Developer Workflow
*   **Environment**: Ensure `ANTHROPIC_API_KEY` is set in the environment.
*   **Dependencies**: Python 3.x with `anthropic`, `matplotlib`, `numpy`, `python-slugify`.
*   **Running Agents**: Scripts are standalone executables.
    ```bash
    python3 scripts/editorial_board.py
    python3 scripts/economist_agent.py
    ```
*   **Chart Testing**: Run `scripts/generate_chart.py` to verify visual styles before integrating.

## Coding Conventions
*   **Prompts as Code**: Prompts are defined as large constant strings at the top of Python files. When modifying agent behavior, edit these prompts first.
*   **Strict Style Enforcment**: The "Economist Voice" is mandatory.
    *   British spelling (organisation, favour).
    *   No throat-clearing ("In today's world...").
    *   Data-first approach (always cite sources).
*   **Visual Style**:
    *   Background color: `#f1f0e9`
    *   Line colors: `#17648d` (primary), `#843844` (secondary)
    *   Font: `DejaVu Sans`
    *   No vertical gridlines, only horizontal.

## Integration Points
*   **Anthropic API**: The system relies heavily on Anthropic's models. Handle API errors and rate limits gracefully.
*   **Jekyll**: The output format must be compatible with Jekyll front matter and markdown structure.

## Common Patterns
*   **Persona Definitions**: Agents are defined with specific personas and "What makes you click/scroll past" criteria (see `editorial_board.py`).
*   **Verification Loop**: The research agent must flag unverified claims. The writer must not use unverified claims.

## Governance & Human Oversight
*   **4 Manual Checkpoints**: Topic review → Editorial decision → Article review → Publication approval
*   **No Auto-Publishing**: Articles are saved as drafts, require explicit git push
*   **Quality Gates**: Editor agent enforces Economist voice, British spelling, sourced data, no unverified claims
*   **Transparency**: All agent reasoning is logged and auditable
*   **Override Capability**: Humans can reject, edit, or force specific topics at any stage
*   **Review Mode**: Run `python3 scripts/economist_agent.py` to see output without committing
