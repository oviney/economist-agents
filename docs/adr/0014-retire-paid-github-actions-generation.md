# ADR-0014: Retire Paid GitHub Actions Generation — Keyless Local/Subscription Runs Only

**Status:** Accepted
**Date:** 2026-07-21
**Decision Maker:** Ouray Viney (Engineering Lead)
**Supersedes:** —
**Superseded by:**

## Context

Two prior decisions already commit this project to keyless, subscription-only
operation:

- **CLAUDE.md constraint #5** (non-negotiable): *"No github.com-only workflows
  for running the pipeline. It must run locally / in the session on the
  subscription."*
- **ADR-0013** (Accepted, 2026-07-14): keyless `claude_web` research on the
  Claude subscription, explicitly for *"an owner who has a Claude subscription
  but will not provision or pay for per-token API keys."*

The repository's automation contradicts both. Four GitHub Actions workflows
still carry paid-AI secrets:

| Workflow | Paid secrets injected | Notes |
|----------|----------------------|-------|
| `content-pipeline.yml` | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SERPER_API_KEY` | Weekly cron (`0 9 * * 1`); calls `EconomistContentFlow(image_mode='hero')` |
| `regenerate-image.yml` | `OPENAI_API_KEY` | Generates featured images via **DALL-E 3** — violates CLAUDE.md #1 and #4 outright |
| `ci.yml` | `OPENAI_API_KEY` | Passed to the pytest step; tests mock APIs per CLAUDE.md, so it is expected vestigial |
| `blog-quality-audit.yml` | API key(s) | Reads the live blog; key usage to be confirmed during execution |

Beyond the policy breach, the scheduled path does not work: the weekly
`content-pipeline.yml` run has **failed 8 consecutive times** (2026-06-01
through 2026-07-20), aborting on `Serper API 400` errors before writing a
single article. The last article to reach the live blog is dated
**2026-04-27** — roughly three months of zero output.

The owner will not provision or pay for per-token API keys. The only sanctioned
credential is the Claude subscription (via `claude_agent_sdk` / the
authenticated `claude` CLI). The generation code already supports this: after
the removal of the pay-per-use providers (#438/#440), the `deterministic`
research path runs on free, keyless academic sources (arXiv + Semantic Scholar),
and `--research-mode claude_web` (ADR-0013) is a second keyless option. The gap
is no longer in the code — it is that the *execution environment* (scheduled
GitHub Actions with injected paid keys) still exists and is the only wired-up
way the pipeline is triggered.

## Decision

We will retire every GitHub Actions workflow that requires a paid-AI key, and
make a keyless local/in-session run on the Claude subscription the **only**
path that generates and publishes articles.

Concretely:

1. **Delete** `content-pipeline.yml` (scheduled paid generation) and
   `regenerate-image.yml` (DALL-E image generation, a standing violation of
   CLAUDE.md #1/#4).
2. **Strip** `OPENAI_API_KEY` / any paid-AI secret from `ci.yml`; CI runs tests,
   which mock external APIs, so it must not depend on a paid key. Do the same
   for `blog-quality-audit.yml`, or retire it if it cannot run without paid AI.
3. **Generation** is a keyless local/session run on the subscription. Publishing
   is handled by `scripts/deploy_to_blog.py`, which opens a pull request against
   the `oviney/blog` repository using a **free GitHub token**
   (`BLOG_REPO_TOKEN`) — no AI key involved. The owner reviews and merges that
   blog PR to go live; the human publication gate is unchanged.

GitHub Actions may still run **key-free** jobs (tests, linting, doc builds,
GitHub-token-only publishing). The decision retires *paid-AI* automation, not
CI as a concept.

## Alternatives Considered

1. **Provision the paid keys properly and keep the weekly cron** — Rejected. It
   is the exact thing CLAUDE.md #1, #2, and #5 forbid: recurring per-token
   spend plus API-key provisioning and maintenance the owner has repeatedly
   declined. It also keeps the DALL-E path alive.
2. **Drop the schedule but keep `content-pipeline.yml`'s `workflow_dispatch` as
   a manual break-glass** — Rejected. A manual trigger still injects paid keys
   when invoked, so it preserves the forbidden coupling and leaves dead,
   key-dependent YAML in the tree. "Break-glass" here would break the same
   non-negotiable it is meant to respect.
3. **Self-hosted GitHub Actions runner authenticated with the Claude
   subscription** — Rejected. The subscription CLI's auth is interactive and not
   designed for unattended CI; wiring it into a runner is brittle and, per
   constraint #5, the pipeline is meant to run *locally / in the session*
   regardless. The complexity buys nothing the local run does not already give.

## Consequences

- **Positive:** Zero recurring AI spend and no API-key maintenance. Policy
  (CLAUDE.md #5, ADR-0013) finally matches reality. Removes the DALL-E
  violation. Ends the weekly silent-failure noise (8 red runs and counting).
  Publishing stays automatable through a *free* GitHub token, so "generate
  locally → PR to blog" remains one flow, not a manual copy-paste.
- **Negative:** Generation is no longer unattended. Cadence now depends on the
  owner actively running the pipeline; there is no scheduled trigger to produce
  a weekly article. This is an accepted trade — an unattended cadence is exactly
  what required the paid keys.
- **Follow-up (B-009):**
  - Delete `content-pipeline.yml` and `regenerate-image.yml`; strip paid keys
    from `ci.yml`; triage/strip `blog-quality-audit.yml`.
  - Reconcile the two entrypoints: the documented keyless command
    (`python -m src.agent_sdk.pipeline … --research-mode claude_web`) generates
    and validates but does **not** publish, while `_deploy_to_blog` lives only
    in `EconomistContentFlow.kickoff()` (`src/economist_agents/flow.py`). Make
    "local run opens the blog PR" reachable from a single canonical, keyless,
    `chart_only` command.
  - Promote `docs/keyless-pipeline-runbook.md` to the canonical run doc and
    point README / CLAUDE.md at it.
- **Revisit if:** the Claude subscription becomes usable for unattended CI
  authentication (making a keyless scheduled runner viable), or the owner
  chooses to opt into paid keys for a specific need.

## References

- [ADR-0013](0013-keyless-claude-web-research.md) — Keyless `claude_web`
  Research (the research half of keyless operation)
- [ADR-0011](0011-opt-in-recursive-deep-research.md) — Opt-In Recursive Deep
  Research (the Serper-era deep-research path this operating model leaves behind)
- CLAUDE.md — Operating Constraints #1, #2, #4, #5
- `.github/workflows/content-pipeline.yml`, `.github/workflows/regenerate-image.yml`
- `docs/keyless-pipeline-runbook.md` — the existing keyless local command
- PRs #438 / #440 (removed the pay-per-use research providers), #439 (hardened
  the free replacements) — the code-side prerequisites that make this operating
  model viable
- BACKLOG.md · B-009 — execution of this decision
