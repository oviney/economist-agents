# Hand-off — 2026-07-28

Written for a fresh session on a different machine. `BACKLOG.md` stays the source
of record; this file is the "where were we" note that a new session should read
first, then delete or overwrite when it goes stale.

## State

`main` is green and pushed. `make ci-local` passes (2380 tests, 8 skipped).
There are **no open defects and no blockers.**

The pipeline generated a publishable article end to end in B-020, and everything
since has been closing the traps that run exposed.

## What landed today

| Item | What it was |
|---|---|
| **B-021** | Three deferred B-020 defects. Writer budget couldn't fund its own retry (BUG-061); no call had a wall-clock bound (BUG-059); `--image-mode hero` was the default and was dead (BUG-060) — the whole human-image handshake was deleted, **−773 lines**. |
| **B-022** | The flow's DALL-E branch, provably dead after B-021, removed. |
| **BUG-064** | Graphics retries could spend 3× the stated cap. |
| **BUG-065** | Production escape — the hero-prompt comment reached the live blog. Now gated at the deploy boundary. |
| `oviney/blog#1168` | Prose-only edit clearing all four B-017 slop tells from the published flaky-tests post. **Open, needs your admin-bypass merge.** |

## The one thing waiting on you

**`oviney/blog#1168`** — it cannot merge itself. `🔒 Security Audit` and
`🖼️ Visual Regression` fail blog-side for pre-existing reasons (npm CVEs; stale
visual baselines), both are required checks, and GitHub forbids self-approval.
Same bypass every article PR needs.

## Next up: article two

There is no blocker. Two generated drafts from the B-020 runs are sitting in
`output/posts/` on the "code review queue" topic — regenerate rather than reuse
them, since they predate today's fixes.

```bash
IS_SANDBOX=1 python -m src.agent_sdk.pipeline "<topic>" --research-mode claude_web
```

Budget ~$1 and ~35 minutes. Then `deploy_to_blog` opens the PR.

## Things that will bite a fresh session

- **A green `make ci-local` says nothing about what the blog accepts.** Four
  consecutive defects were green locally and rejected by the blog. The oracle is
  running the blog's own scripts against a clone: `scripts/validate-posts.sh` and
  `scripts/validate-post-quality.sh`. Measured contract:
  `docs/blog-integration-constraints.md`.
- **The blog repo is `oviney/blog`.** `scripts/deploy_to_blog.py` still shows
  `viney-blog` in its usage docstring — that is the example, not the repo.
- **`image:` is required and there are no redirects.** A published slug is
  permanent; get it right before publishing.
- **System python has no pip** — work in `.venv`. `make ci-local` needs
  `.venv/bin` on `PATH` or `ruff` is not found.
- **Exit codes 10 and 11 are retired, not reused.** Old notes still mention them.

## Not done, on purpose

- **B-012** — deep-research mode is built; only a live acceptance run remains
  (~2M tokens). Parked as an owner cost decision, not a defect.
- **`_check_placeholders` still cannot catch the hero-prompt comment.** That is
  correct — the comment does not exist when the validator runs. The deploy gate
  is the fix. Do not "helpfully" add a pattern there; it would be dead code.
