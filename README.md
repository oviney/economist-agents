# Economist Agents

**Multi-agent content pipeline that generates Economist-style articles with verified sources.**

[![Docs](https://github.com/oviney/economist-agents/actions/workflows/docs.yml/badge.svg)](https://github.com/oviney/economist-agents/actions/workflows/docs.yml)
![Verification](https://img.shields.io/badge/verification-local--first-blue)
![Python](https://img.shields.io/badge/Python-3.12-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> **No CI badge, by design.** [ADR-0015](docs/adr/0015-local-first-verification.md) retired
> GitHub Actions CI: `make ci-local` is the merge gate and `main` is unprotected. The `CI`
> and `Quality Tests` badges that used to sit here pointed at workflows deleted with it —
> stale for months, because the hook meant to catch that (BUG-023) had no implementation.
> See B-036; `scripts/validate_badges.py` now fails on a badge that references a workflow
> which does not exist, or a Python version that disagrees with `.python-version`.

A pipeline of specialised AI agents that discovers topics, votes on them editorially,
researches them against verifiable sources, writes them in *The Economist*'s house
style, generates charts, and runs the result through deterministic quality gates
before it is published. Claude (Anthropic) does the writing and editing; the research
path is deterministic (no LLM); the quality gates are plain Python.

---

## How it works

The pipeline runs in stages, orchestrated by `src/economist_agents/flow.py` over
`src.agent_sdk.pipeline.run_pipeline`:

1. **Discovery** — `scripts/topic_scout.py` surfaces candidate topics.
2. **Editorial board** — `scripts/editorial_board.py` runs a weighted vote across
   seven personas (VP Engineering, Senior QE Lead, Data Skeptic, Career Climber,
   Economist Editor, Busy Reader, Performance Analyst) to pick what is worth writing.
3. **Stage 3 — content generation** (`src/agent_sdk/stage3_runner.py`): research →
   write → charts → edit.
   - **Research** is deterministic academic search over free, keyless providers
     (arXiv + Semantic Scholar). There is **no LLM in the research path**, so
     sources are reproducible, and **no paid search API** (Serper/Google, Brave,
     Tavily were removed by #438).
   - **Writer → Graphics → Editor** all run on Claude via the Anthropic Agent SDK.
   - A **stat audit** strips any sentence whose statistics are not present in the
     research brief.
4. **Stage 4 — editorial review** (`src/agent_sdk/stage4_runner.py`): deterministic
   post-processing quality gates (see below), then `scripts/publication_validator.py`.
5. **Publish or revise** — articles are written to `output/` (configurable via
   `OUTPUT_DIR`). Nothing auto-publishes. A human deploys to an unlisted review URL with
   `deploy_to_blog --mode review`, reads the live page, then runs `make publish SLUG=<slug>`.
   `--mode` is required — there is no default, because the old default skipped review
   (B-028).

### Quality gates (enforced deterministically)

Post-processing in `src/agent_sdk/_shared.py` and `scripts/publication_validator.py`:

1. **Stat audit** — removes sentences citing stats absent from the research brief.
2. **Category normalisation** — normalises categories to Title Case.
3. **Description truncation** — caps meta descriptions at 160 characters.
4. **Heading limit** — merges sections when there are more than four headings.
5. **Hedging removal** — strips "One suspects", "it is worth noting", and similar filler.
6. **Ending validation** — flags summary endings (HIGH severity).
7. **Chart auto-embed** — inserts the chart before the References if it is missing.
8. **British spelling** — applies American → British replacements.
9. **Publication validator** — checks frontmatter, categories, word count, author,
   image metadata, and placeholders.

> These nine deterministic checks are separate from the article's `gates_passed/N`
> **quality score**, which Stage 4 derives from the 5-dimension `ArticleEvaluator`
> (`scripts/article_evaluator.py`).

---

## Installation

**Requires Python 3.13.x** (see [ADR-0004](docs/adr/0004-python-version-constraint.md);
3.14+ is untested).

```bash
git clone https://github.com/oviney/economist-agents.git
cd economist-agents

python3.13 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

cp .env.example .env               # then edit in your API keys
```

### Environment variables

The keyless path uses **no paid AI keys** — writing/graphics run on the Claude
subscription via the Agent SDK, research on free keyless providers.

| Variable | Required | Purpose |
|----------|----------|---------|
| `BLOG_REPO_TOKEN` | To publish | Free GitHub token with push to `oviney/blog`, so the deploy step can open a PR. No AI key. |
| `OUTPUT_DIR` | No | Output directory for generated articles (default `output/`) |
| `GOOGLE_APPLICATION_CREDENTIALS`, `GA4_PROPERTY_ID`, `GSC_PROPERTY_URL` | For analytics ETL | Google Analytics 4 / Search Console content-intelligence pipeline |

> **No `SERPER_API_KEY`/`OPENAI_API_KEY`.** Serper and the other pay-per-use
> search APIs were removed (#438); DALL·E image generation was retired
> (ADR-0014 / B-009) — Claude draws the hero itself, as SVG (B-016b).
> A legacy paid path remains (`EconomistContentFlow` topic discovery needs
> `ANTHROPIC_API_KEY` — BUG-046); making the full flow keyless is **B-010**.

---

## Usage

The keyless generator runs on the Claude subscription — **no paid AI key**. It
takes a topic argument (there is no keyless auto-discovery yet — see B-010) and
runs **end to end in one command**: Stage 3 researches, writes, charts, and draws
the hero SVG; Stage 4 polishes and validates.

```bash
# Writes output/posts/<slug>.md + chart + hero SVG, then validates. Exits 0 when
# the article is publish-ready.
python3 -m src.agent_sdk.pipeline "<topic>" --research-mode claude_web
```

> There used to be a two-step image handshake here — Stage 3 paused on exit 10
> for a human-supplied hero and `--resume` finished the job. B-016b made Claude
> draw the hero itself, so B-021 removed the pause, `--image-mode`, `--resume`,
> and `--no-image`. To supply art by hand, overwrite the drawn SVG at
> `output/posts/images/<slug>-hero.svg` and re-run.

> This generates + validates but does **not** publish. Publishing (open a PR on
> `oviney/blog` via the free `BLOG_REPO_TOKEN`) currently lives only in
> `EconomistContentFlow`, whose topic-discovery is not yet keyless (BUG-046). A
> single keyless generate→publish command is tracked in **B-010**. See
> [`docs/keyless-pipeline-runbook.md`](docs/keyless-pipeline-runbook.md) for the
> current keyless run + setup steps.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the run + deploy steps and exit codes,
and [`docs/FLOW_ARCHITECTURE.md`](docs/FLOW_ARCHITECTURE.md) for the orchestration
design.

---

## Development

We follow a strict, quality-first workflow. Full details are in
[`CONTRIBUTING.md`](CONTRIBUTING.md); the essentials:

```bash
make quality        # format + lint + type-check + test (the full gate)
make test           # pytest only
make lint           # ruff check
make format         # ruff format
make type-check     # pyright
```

Git hooks keep commits fast and pushes safe:

- **`git commit`** runs `ruff format` + `ruff check` only (fast).
- **`git push`** runs the pytest suite via a pre-push hook.
- Emergency bypass: `git push --no-verify` (hotfixes only).

Re-enable hooks after a fresh clone:

```bash
pre-commit install --install-hooks
pre-commit install --hook-type pre-push
```

### Code standards

Type hints and docstrings are mandatory. Use `orjson`, not `json`. Use a `logger`,
never `print()`. Mock external APIs in tests; keep coverage above 80%. The full
standard lives in [`skills/python-quality/SKILL.md`](skills/python-quality/SKILL.md).

### How work is tracked

The backlog is **local-first**:

- **Planning / work items → [`BACKLOG.md`](BACKLOG.md)** (`B-NNN` ids). This is the
  source of record — edit the file directly.
- **PRs + code review → GitHub via the `gh` CLI.**
- **Bugs / defects → `data/skills_state/defect_tracker.json`**, then graduate to a
  `BACKLOG.md` item if they need scheduling.

See [`docs/specs/local-backlog-migration.md`](docs/specs/local-backlog-migration.md)
for why the GitHub-issues MCP was retired.

---

## Agents & skills

- **Content-pipeline agents** — YAML configs under `agents/` (topic scout, the
  seven-persona editorial board, and the researcher / writer / editor / graphics
  quartet). Reusable public templates live in `agents/skills_configs/`. See
  [`agents/README.md`](agents/README.md).
- **Skills** — 39 `SKILL.md` workflow definitions under `skills/`. The six
  lifecycle skills (`spec-driven-development`, `planning-and-task-breakdown`,
  `incremental-implementation`, `test-driven-development`, `code-review-and-quality`,
  `shipping-and-launch`) come from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)
  and govern all work; the rest are domain skills. See [`skills/README.md`](skills/README.md).

---

## Architecture notes

- **LLM**: Claude (Anthropic) via the Agent SDK on the Claude subscription — no
  paid AI key on the keyless path. No DALL·E / `OPENAI_API_KEY` (image generation
  retired, ADR-0014); hero images are human-supplied.
- **Framework**: The Anthropic Agent SDK is the runtime. The earlier CrewAI runtime
  was removed in Phase 2 (see [ADR-0006](docs/adr/0006-agent-framework-selection.md)).
- **Research**: Deterministic, LLM-free, and reproducible (arXiv + Semantic Scholar,
  keyless).
- **Quality**: Enforced in plain Python, not by an LLM judge.

---

## Project structure

```
economist-agents/
├── agents/                   # Content-pipeline agent YAML + reusable templates (skills_configs/)
├── data/skills_state/        # Runtime state JSON (metrics, defect tracker, trackers)
├── docs/                     # Architecture, ADRs, guides, and historical archive
├── scripts/                  # Standalone tools (validators, search, ETL, orchestration)
├── skills/*/SKILL.md         # 39 skill workflow definitions
├── src/agent_sdk/            # Anthropic Agent SDK runners (stage3, stage4, pipeline, _shared)
├── src/economist_agents/     # Flow orchestration and adapters
├── src/quality/              # Quality gates, governance, validators, metrics
├── src/telemetry/, src/tools/, src/utils/
├── tests/                    # pytest suite (2,400+ tests)
├── BACKLOG.md                # Source of record for planning items
├── CLAUDE.md                 # Operating mode + code standards for AI agents
└── README.md                 # This file
```

---

## Documentation

- **[Documentation hub](docs/README.md)** — navigation to all guides, architecture, and references
- **[Contributing](CONTRIBUTING.md)** — workflow, TDD, quality gates, article generation
- **[ADRs](docs/adr/)** — architecture decision records (single MADR numbering sequence)
- **[Flow architecture](docs/FLOW_ARCHITECTURE.md)** — orchestration design
- **[Backlog](BACKLOG.md)** — current planning items

---

## Glossary

- **Editorial board** — seven AI personas that vote (weighted) on which topics to write.
- **Stat audit** — deterministic gate removing statistics not grounded in the research brief.
- **Quality gates** — the deterministic post-processing checks a draft must pass before publication.
- **Source of record** — `BACKLOG.md` for planning, GitHub for PRs, `defect_tracker.json` for bugs.

## License

[MIT](LICENSE) © 2026 Ouray Viney.
