# Runbook: Keyless pipeline on the Claude subscription (B-006 / B-009 / B-010)

Generate **and publish** an article with **no paid API keys** — no
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `SERPER_API_KEY`. All LLM work
(writer, graphics, research, vision) runs on your Claude subscription through
the Agent SDK (`claude_agent_sdk.query()` → the authenticated `claude` CLI).
Publishing opens a PR on the blog repo using a **free** GitHub token.

This is the canonical, verified path (B-010 acceptance run: keyless generate +
blog PR on 2026-07-21).

## One-time setup

The pipeline has historically only run in GitHub Actions, so a local checkout
needs provisioning. On a stock Debian/Ubuntu python, `ensurepip` is stripped, so
`python3 -m venv` produces a venv without pip — bootstrap it with `get-pip.py`:

```bash
python3 -m venv .venv                                   # .venv is gitignored
curl -sS https://bootstrap.pypa.io/get-pip.py | .venv/bin/python   # ensurepip is stripped
.venv/bin/pip install -r requirements.txt               # ~100 packages
```

The `claude` CLI must be installed and logged in to your subscription (`claude`
on PATH; credentials in `~/.claude/`).

## 1. Generate (keyless)

```bash
# IS_SANDBOX=1 is required ONLY when running as root — the SDK otherwise refuses
# --dangerously-skip-permissions. Drop it if you run as a normal user.
IS_SANDBOX=1 .venv/bin/python -m src.agent_sdk.pipeline "your topic here" \
    --research-mode claude_web
```

- `--research-mode claude_web` — **use this.** Claude does its own live web
  research via built-in `WebSearch`/`WebFetch` (ADR-0013). The `deterministic`
  mode (arXiv + Semantic Scholar) is heavily rate-limited from most environments
  and frequently aborts the run with empty research (BUG-050); `claude_web`
  avoids those APIs entirely and is the reliable keyless default.
- There are no image modes any more (B-021). The run goes end to end and writes
  `output/posts/<slug>.md`.
- **It produces no images (B-042).** The owner draws every hero and makes every
  chart. The run ends with a review packet at `output/posts/<slug>.review.md`
  and a desktop banner; finish the art, then `make art SLUG=<slug>`.

Exit `0` = every gate passed — **the prose is ready, the post is not complete**;
`1` = validator issues;
`2` = research failed (retry, or you are on `deterministic` — switch to
`claude_web`).

### Opt-in: `--brief` for flagship posts (B-012)

For a cornerstone post where sourcing quality matters most, run the
`deep-research` harness first to produce a verified, cited brief
(`docs/research/<slug>.md`), then hand it to the writer:

```bash
IS_SANDBOX=1 python -m src.agent_sdk.pipeline "<topic>" \
    --brief docs/research/<slug>.md
```

`--brief` skips the research step and uses that file (refuted claims are
stripped automatically). **This is opt-in and heavy** — one deep-research run is
~2M tokens and can hit your session limit — so `claude_web` stays the everyday
default; reserve `--brief` for the pieces that warrant it.

### ⚠ `--brief` with an uncited artifact will manufacture citations

**Measured 2026-08-01, on the first real B-038 run.** The brief was converted from an owner
research artifact that contained **zero `<a href>` and one unsourced statistic**. `--brief`
skips the research step, so the writer received an argument with no evidence — and filled the
gap itself. The article came back with:

- a chart carrying **four invented percentages** (62/46/28/12%) presented with an axis and a
  measured-sounding subtitle, where the brief had contained exactly one number;
- prose describing that chart as showing accumulation and a threshold it does not plot —
  ADR-0018's chart finding reproduced exactly, one day after that ADR was accepted;
- a **named real executive** given a motive the cited annual report cannot support;
- a fabricated ratio ("cuts two sprints … *typically* surrenders six to eight");
- three references, **zero URLs**.

`article_evaluator` scored it **76** and the publication validator **passed** it, because
counting checks can see "chart embedded: yes" and "3 references cited" and nothing further.
That is the 88%-vs-51 gap of ADR-0018, live.

**The tool did what it was asked.** The defect is upstream: an artifact with no evidence is
not a research brief, it is an argument. Before running `--brief`:

```bash
grep -c 'href=' <artifact>.html      # zero links is the warning sign
grep -c '](http' docs/research/<slug>.md   # and in the converted brief
```

If that returns 0, either add sources to the artifact first — `docs/research/artifact-sourcing-prompt.md`
is a prompt to paste back into the conversation that produced it — or expect to review the
output as fabrication-until-proven-otherwise. **Never publish such a run without the
`blog-post-review` gate.** The eight labelled defects from this run are now calibration cases
in `docs/evals/review-gate/cases/` (B-040).

### What a run actually costs — read the ledger, do not quote a remembered figure

`logs/agent_sdk_costs.jsonl` records `wall_seconds`, `stage3_seconds` and per-stage cost for
every run, and has since 2026-04-26. Across the five recorded runs:

| | Wall clock | Total cost | Research share |
|---|---|---|---|
| Range | **3.4 – 15.4 min** | **$0.25 – $1.31** | $0.00 – $0.88 |
| Typical (`--brief`, research skipped) | 3.4 – 4.8 min | $0.25 – $0.49 | $0.00 |
| The one live-research run | 15.4 min | $1.31 | $0.88 |

```bash
.venv/bin/python -c "import json;[print(r['timestamp'][:10], round(r['wall_seconds']/60,1),'min', '\$'+str(round(r['total_cost_usd'],2))) for r in map(json.loads, open('logs/agent_sdk_costs.jsonl'))]"
```

`docs/HANDOFF.md` and this runbook used to say "~$1 and ~35 minutes". No recorded run has
ever come close to 35 minutes. A 2026-08-01 session quoted that number back to the owner and
defended it before checking the ledger sitting in `logs/`. **The instrument existed; nobody
read it.** That is a worse failure than not measuring, because the folklore number is the one
everybody repeats. If a run feels slow, add its row and compare — do not estimate.

## 2. Publish (keyless — free GitHub token, opens a PR you review)

```bash
BLOG_REPO_TOKEN=<free GitHub PAT with push to oviney/blog> \
  .venv/bin/python -m scripts.deploy_to_blog --blog-owner oviney --blog-repo blog
# add --dry-run first to validate without pushing.
```

This clones the blog repo, commits the latest `output/posts/*` article + chart
on a `content/<slug>-<ts>` branch, and opens a PR on `oviney/blog`. **You review
and merge that PR to go live** — the human publication gate is unchanged. The
token needs only `Contents` + `Pull requests` write on `oviney/blog` — no AI key.

## What runs, and on what auth

| Stage | Mechanism | Key needed |
|-------|-----------|------------|
| Research | `claude_web` → `query()` + WebSearch/WebFetch | none (subscription) |
| Writer | Stage 3 `query()` | none (subscription) |
| Chart figures | `propose_chart_spec` — regex extraction from the brief, **no LLM** | none |
| Chart render | `make art` → `chart_renderer.py` (matplotlib), from a spec you framed | none |
| Hero image | **you draw it** (B-042) | none |
| Quality gates + validator | deterministic Python | none |

## Honest limitations

- **`claude_web` research is non-deterministic** and puts an LLM in the research
  path — a deliberate, opt-in departure from the LLM-free default (ADR-0013).
  Source quality depends on the model's search behaviour; the
  `citation_verifier` / `publication_validator` citation gates still apply.
- **The pipeline draws nothing (B-042, ADR-0019).** Every image is the owner's:
  drop the hero at `output/posts/images/<slug>-hero.svg` (the `.image_prompt.md`
  sidecar and the review packet carry the brief). There is no DALL-E path either
  — raster generation was retired (ADR-0014) and CLAUDE.md #4 forbids pixel
  models. **Art presence is enforced at deploy, not by the validator**, so a
  green run says nothing about whether the art exists.
- **Topic is manual on this route.** `pipeline.py` takes the topic as an argument.
  This used to be forced: `EconomistContentFlow`'s Stage-1 discovery required
  `ANTHROPIC_API_KEY` (BUG-046). **That is fixed as of 2026-07-31** —
  `create_llm_client` now defaults to a keyless `agent_sdk` provider, so the flow's
  discovery and editorial-review stages run on the subscription too. This single
  command remains the simplest route, not the only one.

## Deprecated path

`scripts/economist_agent.py` still requires a paid key and will exit with a
pointer here if run keyless. Use `python -m src.agent_sdk.pipeline` instead.
