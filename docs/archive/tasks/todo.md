# TODO: Close-out before the MacBook hand-off (2026-07-28)

> Supersedes the B-009 task list that lived here (B-009 landed 2026-07-21 — see
> `BACKLOG.md` Done). `BACKLOG.md` remains the source of record; this file is the
> working checklist for the current session only.

Three items remain after B-021. All are independent — no shared files, no
dependency edges — so the order is by risk, not by need: cheapest and most
isolated first, largest deletion last. Each lands as its own commit.

- [x] **T1 — BUG-064: graphics retries must not spend 3× the cap** · **XS**
  - `_graphics_with_retry` hands every attempt the FULL `graphics_budget_usd`
    instead of the remaining balance, so `_GRAPHICS_MAX_ATTEMPTS=3` can spend 3×
    the operator's cap. The writer loop already accounts correctly (BUG-061);
    graphics simply never copied it.
  - Acceptance: each attempt receives the *remaining* balance; total graphics
    spend across all attempts never exceeds `graphics_budget_usd`.
  - Verify: RED-first regression asserting the caps handed to attempts 2 and 3
    shrink; `make ci-local`.
  - Depends: none. Files: `stage3_runner.py` + one new test.

- [x] **T2 — BUG-065: the hero-prompt comment must not reach the blog** · **S**
  - Production escape: the `<!-- HERO IMAGE … replace this whole comment -->`
    block published live. The validator cannot catch it —
    `_maybe_inject_hero_prompt` runs *after* Stage 4 by design — so the gate
    belongs at the **deploy boundary**, the last point before anything is public.
  - Decision: guard in `deploy_to_blog`, **not** a new `_check_placeholders`
    pattern. The comment is legitimate in the local artifact (it is the
    reviewer's brief) and illegitimate only on the blog. A validator pattern
    would be dead code — that check runs before the comment exists.
  - Decision: **reject, don't strip.** Silently deleting it hides that no hero
    was drawn, and a heroless article fails the blog's required `image:` anyway.
  - Acceptance: deploying an article containing the marker raises `DeployError`
    naming the file and the fix; a clean article deploys unchanged.
  - Verify: RED-first regression on both paths; `make ci-local`.
  - Depends: none. Files: `deploy_to_blog.py` + one new test.

- [x] **T3 — B-022: remove the DALL-E branch from `EconomistContentFlow`** · **M**
  - `image_mode="hero"` still calls `generate_featured_image`, warns about a
    missing `OPENAI_API_KEY`, and falls back to `blog-default.svg` — which the
    deploy path rejects as `default_image_fallback`. It violates Operating
    Constraints #1–#4 and ADR-0014 retired it. B-021 already stopped it changing
    what the pipeline produces, so it is provably dead weight.
  - Acceptance: `EconomistContentFlow` takes no `image_mode`; the flow always
    takes the keyless path; `generate_featured_image` unreferenced from `flow.py`.
  - Verify: hero cases removed from `test_flow_image_mode.py`, the rest green;
    `make ci-local`.
  - Depends: none. Files: `flow.py`, `test_flow_image_mode.py`, docs.

## Checkpoint — hand-off ready

- [x] `make ci-local` green — 2380 passed, 8 skipped
- [x] Everything committed **and pushed** — the MacBook can only see `origin`
- [x] `BACKLOG.md` + `defect_tracker.json` reflect reality
- [x] Hand-off note written — `docs/HANDOFF.md`

**All three landed 2026-07-28.** One item is not mine to close: `oviney/blog#1168`
needs Ouray's admin-bypass merge.
