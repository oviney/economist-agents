# Gemini CLI — Project Rules for Economist-Agents

**This file is intentionally thin.** To avoid the drift that comes from restating the
same rules in several places, all project conventions live in a single source of truth and
this file only points at it.

## Single source of truth

- **`CLAUDE.md`** — operating mode, lifecycle discipline, coding standards (type hints,
  docstrings, `orjson`, `logger` not `print`, mock APIs in tests, >80% coverage), quality
  gates, and the backlog model. Read it first; it governs every assistant working in this repo.
- **`skills/*/SKILL.md`** — the authoritative, detailed workflows:
  - `skills/python-quality/SKILL.md` — full code standards
  - `skills/economist-writing/SKILL.md` — the Economist voice rules (British spelling, no
    throat-clearing, data-first / cite every claim)
  - `skills/test-driven-development/SKILL.md` — the RED → GREEN → REFACTOR cycle
  - `skills/using-agent-skills/SKILL.md` — how to pick the right skill for a task

## Gemini-specific notes (the only non-duplicated content)

- **Shared memory:** Gemini and Claude do not share internal state. Record architectural
  decisions in `docs/` (or an ADR) and in commit messages so both stay synchronized.
- **Ignored state:** `.claude/` and `.gemini/` are git-ignored. Do not modify files under `.claude/`.
- **Commit footer:** `Co-Authored-By: Gemini CLI <noreply@google.com>`.
