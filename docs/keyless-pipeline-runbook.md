# Runbook: Keyless pipeline on the Claude subscription (B-006)

Generate a publish-ready article with **no paid API keys** — no
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `SERPER_API_KEY`. All LLM work
(writer, graphics, research, vision) runs on your Claude subscription through
the Agent SDK (`claude_agent_sdk.query()` → the authenticated `claude` CLI).

## One-time setup

```bash
# The Agent SDK is the runtime. If the full requirements install aborts on an
# unrelated wheel (sgmllib3k / feedparser), install the SDK directly:
pip install --ignore-installed PyJWT "claude-agent-sdk>=0.1.68,<1.0.0"
```

The `claude` CLI must be installed and logged in to your subscription
(`claude` on PATH; credentials in `~/.claude/`). This session already is.

## Run it

```bash
# IS_SANDBOX=1 is required ONLY when running as root — the SDK otherwise refuses
# --dangerously-skip-permissions. Drop it if you run as a normal user.
IS_SANDBOX=1 python -m src.agent_sdk.pipeline "your topic here" \
    --image-mode chart_only \
    --research-mode claude_web
```

- `--image-mode chart_only` — no DALL-E hero image; the data chart is the
  visual. Runs end-to-end with no image handshake and writes the finished
  article to `output/posts/<slug>.md`.
- `--research-mode claude_web` — Claude does its own live web research via the
  built-in `WebSearch`/`WebFetch` tools (no Serper). See ADR-0012.

Exit code `0` = the publication validator passed (article is publish-ready);
`1` = validator found issues (printed to stderr); `2` = research failed.

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
  path — a deliberate, opt-in departure from the LLM-free default (ADR-0012).
  Source quality depends on the model's search behaviour; the
  `citation_verifier` / `publication_validator` citation gates still apply.
- **`chart_only` ships no hero image.** For a hero image, use the default
  `--image-mode hero` handshake flow (which needs a human-supplied PNG, or
  `OPENAI_API_KEY` for DALL-E in the legacy path).

## Deprecated path

`scripts/economist_agent.py` still requires a paid key and will exit with a
pointer here if run keyless. Use `python -m src.agent_sdk.pipeline` instead.
