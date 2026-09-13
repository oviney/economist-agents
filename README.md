# Economist Agents

**Multi-agent content pipeline that generates Economist-style articles with verified sources.**

![Verification](https://img.shields.io/badge/verification-local--first-blue)
![Python](https://img.shields.io/badge/Python-3.12-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> **No CI badge, by design.** [ADR-0015](docs/adr/0015-local-first-verification.md) retired
> GitHub Actions CI: `make ci-local` is the merge gate and `main` is unprotected. The `CI`
> and `Quality Tests` badges that used to sit here pointed at workflows deleted with it —
> stale for months. `tests/test_python_version_consistency.py` keeps the Python badge in
> step with `.python-version`; there is no workflow badge left to go stale.

A pipeline of specialised AI agents that discovers topics, votes on them editorially,
researches them against verifiable sources, writes them in *The Economist*'s house
style, generates charts, and runs the result through deterministic quality gates
before it is published. Claude (Anthropic) does the writing and editing; the research
path is deterministic (no LLM); the quality gates are plain Python.

---

## How it works

One command, one path (ADR-0016; B-048 deleted the Stage 1/2 topic scout and editorial
board — the owner chooses what to write):

```bash
python -m src.agent_sdk.pipeline "<topic>" --research-mode claude_web
```

1. **Research** — `claude_web` (ADR-0013): Claude's own WebSearch/WebFetch on the
   subscription, no search API key. A `deterministic` arXiv + Semantic Scholar mode exists
   but is rate-limited from most environments (BUG-050).
2. **Write** (`src/agent_sdk/stage3_runner.py`) — one Claude call via the Agent SDK, from
   the research brief only. A **stat audit** strips any sentence whose statistics are not in
   the brief. The pipeline draws nothing (constraint #4): it extracts candidate chart
   figures with provenance and writes the hero *brief* the owner draws from.
3. **Review gates** (`src/agent_sdk/stage4_runner.py`) — deterministic post-processing, then
   `scripts/publication_validator.py`. A review packet lands beside the article.
4. **Publish** — the owner adds art (`make art`), deploys to an unlisted review URL with
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
> **quality score**. B-048 D4 deleted the 5-dimension evaluator: style is the owner's
> judgment, and the validator rules only on reader-protecting invariants.

---

## Installation

**Requires Python 3.12.x** (see [ADR-0004](docs/adr/0004-python-version-constraint.md);
3.14+ is untested).

```bash
git clone https://github.com/oviney/economist-agents.git
cd economist-agents

python3.12 -m venv .venv
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

The run, review and publish steps are in `CLAUDE.md` (Publishing workflow); the exit
codes are in `python -m src.agent_sdk.pipeline --help`.

---

## Development

We follow a strict, quality-first workflow. Full details are in
`CLAUDE.md`; the essentials:

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
- **Bugs / defects → `BACKLOG.md`** as `BUG-NNN` entries.

The GitHub-issues MCP was retired as a token drain; the spec is archived at
`docs/archive/specs/local-backlog-migration.md`.

---

## Agents & skills

- **Agents** — there is one: the Stage 3 writer, prompted in
  `src/agent_sdk/stage3_runner.py`. The YAML agent library and the topic-scout /
  editorial-board personas were deleted by B-048 slice 2.
- **Skills** — four `SKILL.md` files under `skills/`: the writing rules, the code standards,
  the skill-routing contract and ADR governance. The six lifecycle skills come from the
  `agent-skills` plugin ([addyosmani/agent-skills](https://github.com/addyosmani/agent-skills))
  and govern all work. Fourteen retired domain skills sit in `docs/archive/skills/`.

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
├── src/quality/              # Quality gates, governance, validators, metrics
├── src/telemetry/, src/tools/, src/utils/
├── tests/                    # pytest suite (2,400+ tests)
├── BACKLOG.md                # Source of record for planning items
├── CLAUDE.md                 # Operating mode + code standards for AI agents
└── README.md                 # This file
```

---

## Documentation

- **[Archive](docs/archive/README.md)** — every retired doc, kept whole (B-048 slice 3)
- **[ADRs](docs/adr/)** — architecture decision records (single MADR numbering sequence)
- **[Backlog](BACKLOG.md)** — current planning items

---

## Glossary

- **Editorial board** — seven AI personas that vote (weighted) on which topics to write.
- **Stat audit** — deterministic gate removing statistics not grounded in the research brief.
- **Quality gates** — the deterministic post-processing checks a draft must pass before publication.
- **Source of record** — `BACKLOG.md` for planning, GitHub for PRs, `defect_tracker.json` for bugs.

## License

[MIT](LICENSE) © 2026 Ouray Viney.
