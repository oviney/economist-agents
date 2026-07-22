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
    --image-mode chart_only \
    --research-mode claude_web
```

- `--research-mode claude_web` — **use this.** Claude does its own live web
  research via built-in `WebSearch`/`WebFetch` (ADR-0013). The `deterministic`
  mode (arXiv + Semantic Scholar) is heavily rate-limited from most environments
  and frequently aborts the run with empty research (BUG-050); `claude_web`
  avoids those APIs entirely and is the reliable keyless default.
- `--image-mode chart_only` — no hero image; the data chart is the visual. Runs
  end-to-end with no image handshake and writes `output/posts/<slug>.md`.

Exit `0` = publication validator passed (publish-ready); `1` = validator issues;
`2` = research failed (retry, or you are on `deterministic` — switch to
`claude_web`).

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
| Writer + Graphics | Stage 3 `query()` | none (subscription) |
| Hero image | skipped in `chart_only` | none |
| Vision alt/caption | not invoked in `chart_only` (hero only) | none (subscription) |
| Quality gates + validator | deterministic Python | none |

## Honest limitations

- **`claude_web` research is non-deterministic** and puts an LLM in the research
  path — a deliberate, opt-in departure from the LLM-free default (ADR-0013).
  Source quality depends on the model's search behaviour; the
  `citation_verifier` / `publication_validator` citation gates still apply.
- **`chart_only` ships no hero image.** For a hero image, use the default
  `--image-mode hero` handshake flow and supply the PNG yourself (per CLAUDE.md
  #4). There is no DALL-E path — image generation was retired (ADR-0014).
- **Topic is manual.** `pipeline.py` takes the topic as an argument; there is no
  keyless auto-discovery. `EconomistContentFlow`'s Stage-1 discovery still needs
  `ANTHROPIC_API_KEY` (BUG-046), so this two-step is the keyless route.

## Deprecated path

`scripts/economist_agent.py` still requires a paid key and will exit with a
pointer here if run keyless. Use `python -m src.agent_sdk.pipeline` instead.
