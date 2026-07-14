# Gemini CLI — Project Rules for Economist-Agents

**This file is intentionally thin.** To avoid the drift that comes from restating the
same rules in several places, all project conventions live in a single source of truth and
this file only points at it.

## Single source of truth

- **`CLAUDE.md`** — operating mode, lifecycle discipline, coding standards (type hints,
  docstrings, `orjson`, `logger` not `print`, mock APIs in tests, >80% coverage), quality
  gates, and the backlog model. Read it first; it governs every assistant working in this repo.
  When this file and `CLAUDE.md` diverge, **`CLAUDE.md` wins.**
- **`skills/*/SKILL.md`** — the authoritative, detailed workflows:
  - `skills/python-quality/SKILL.md` — full code standards
  - `skills/economist-writing/SKILL.md` — the Economist voice rules (British spelling, no
    throat-clearing, data-first / cite every claim)
  - `skills/test-driven-development/SKILL.md` — the RED → GREEN → REFACTOR cycle
  - `skills/using-agent-skills/SKILL.md` — how to pick the right skill for a task

## Architecture (quick orientation)

- **Runtime**: Anthropic Agent SDK (`src/agent_sdk/`). The earlier CrewAI runtime was
  removed (ADR-0006). Do not add CrewAI back.
- **Pipeline**: `src/economist_agents/flow.py` orchestrates `src.agent_sdk.pipeline.run_pipeline`
  (Stage 3 content generation → Stage 4 deterministic quality gates).
- **Research** is deterministic (arXiv + Google Scholar via Serper) — no LLM in that path.
- **Python**: 3.13.x (3.14+ untested — see ADR-0004).
- **Backlog**: `BACKLOG.md` is the source of record (`B-NNN`); PRs go through the `gh` CLI.

## Gemini-specific notes

- **Shared memory:** Gemini and Claude do not share internal state. Record architectural
  decisions in `docs/` (or an ADR) and in commit messages so both stay synchronized.
- **Ignored state:** `.claude/` and `.gemini/` are git-ignored. Do not modify files under `.claude/`.
- **Commit footer:** `Co-Authored-By: Gemini CLI <noreply@google.com>`.
