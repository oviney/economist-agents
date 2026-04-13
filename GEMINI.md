# Gemini CLI Project Rules for Economist-Agents

## Coexistence with Claude Code
- **Primary Agent**: Claude Code is used extensively in this repo.
- **Shared Memory**: Gemini and Claude do not share internal state. Document all architectural changes in `docs/` or commit messages so both agents stay synchronized.
- **Ignore State**: Both `.claude/` and `.gemini/` are ignored in `.gitignore`. Do not modify files inside `.claude/`.

## Coding Standards (Inherited from CLAUDE.md)
- **Type Hints**: Mandatory for all new Python functions.
- **Docstrings**: Required for all classes and functions.
- **JSON**: Use `orjson` instead of `json` for performance and consistency.
- **Logging**: Use a logger (`import logging`), never use `print()`.
- **Testing**: Mock all external APIs. Maintain >80% code coverage.

## Project Conventions (from copilot-instructions.md)
- **Prompts as Code**: Prompts are stored as large constant strings at the top of Python files. Edit these first when changing agent behavior.
- **Economist Voice**: 
  - Use British spelling (organisation, favour, etc.).
  - Avoid introductory filler ("In today's world...").
  - Data-first: Always cite sources for claims.
- **Visual Styles**: See `scripts/generate_chart.py` for matplotlib constraints (background: `#f1f0e9`).

## Development Workflow
- **Validation**: Always run tests after making changes (`pytest`).
- **Commits**: Follow the project's strict commit style (review `git log -n 5`).
  - **Format**: `<type>: <summary>` (e.g., `feat: Story #123 — add new feature`).
  - **Body**: Provide a detailed explanation of "why" and "what", including test results and any out-of-scope items.
  - **Footer**: Include `Co-Authored-By: Gemini CLI <noreply@google.com>`.
- **Security**: Never commit or log API keys (`ANTHROPIC_API_KEY`, etc.).
