# Economist Agents — AI Assistant Instructions

> The former Copilot instruction file under `.github/` described the CrewAI-era architecture and was
> archived by B-048 slice 1 (`docs/archive/github-copilot-instructions-2026-09.md`). This file
> is the only Copilot instruction file.
> This root file is a short human-readable orientation; for the authoritative operating
> mode and coding standards, read [`CLAUDE.md`](CLAUDE.md).

## Project purpose

A multi-agent content pipeline that produces publication-quality articles in *The
Economist*'s style, backed by verifiable sources. It is a content factory, not a blog:
specialised agents handle topic discovery, editorial voting, research, writing, editing,
and chart generation.

## Architecture & data flow

One path: `python -m src.agent_sdk.pipeline "<topic>" --research-mode claude_web`
(B-048 deleted the Stage 1/2 topic scout and editorial board):

1. **Research** — `claude_web`, Claude's own WebSearch on the subscription; no search API.
2. **Write** (`src/agent_sdk/stage3_runner.py`) — one Claude call via the Agent SDK from the
   brief; a stat audit strips unsourced numbers. The pipeline draws no images (constraint #4).
3. **Review gates** (`src/agent_sdk/stage4_runner.py`) — deterministic post-processing, then
   `scripts/publication_validator.py`.
4. **Publish** — the owner adds art (`make art`), deploys with `deploy_to_blog --mode review`,
   reads the live page, then `make publish SLUG=<slug>`. Nothing auto-publishes.

## Key files

- `src/agent_sdk/stage3_runner.py`, `stage4_runner.py`, `pipeline.py`, `_shared.py`
- `src/agent_sdk/chart_renderer.py` — renders an owner-approved chart spec (`make art`)
- `scripts/publication_validator.py` — final publication gate

## Coding conventions

- **Prompts as code**: agent prompts are large constant strings at the top of their Python
  files. When changing behaviour, edit the prompt first.
- **Economist voice** (mandatory): British spelling; no throat-clearing ("In today's
  world..."); data-first, always cite sources; the writer must not use unverified claims.
- **Standards**: type hints + docstrings mandatory; `orjson` not `json`; `logger` not
  `print()`; mock APIs in tests; >80% coverage. Python 3.13.x.
- **Chart style**: background `#f1f0e9`; primary `#17648d`, secondary `#843844`;
  DejaVu Sans; horizontal gridlines only.

## Governance & human oversight

- **Manual checkpoints**: topic review → editorial decision → article review → publication approval.
- **No auto-publishing**: articles are drafts until a human deploys them.
- **Quality gates** are deterministic Python (stat audit, British spelling, hedging removal,
  frontmatter/ending validation, chart embedding) — not an LLM judge.
- **Backlog**: `BACKLOG.md` is the source of record (`B-NNN`); PRs go through the `gh` CLI.
