# Spec: B-021 · The next real run must not abort, hang, or default to a dead mode

Status: DRAFT — awaiting LGTM
Date: 2026-07-28
Depends on: B-020 (acceptance passed 2026-07-27)

## Objective

B-020 proved the pipeline can produce a publishable article end to end. It took
**five runs**, and three of the defects it exposed were deferred rather than
fixed. All three are latent traps on the *next* run, which costs ~$1 and ~35
minutes each:

| Defect | Severity | What it does to a real run |
|---|---|---|
| **BUG-061** | HIGH | The writer's cumulative budget cannot fund a retry. One malformed first draft — a normal, *handled* condition — aborts the whole run with `BudgetExceededError` after money is already spent. |
| **BUG-059** | HIGH | `_collect_text` bounds **cost** but not **wall clock**. Any Stage 3 call (writer, graphics, hero) can stall silently and forever. Hero draws already run 440–600s, so "slow" and "hung" are indistinguishable today. |
| **BUG-060** + `--image-mode` | LOW / HIGH-UX | `--image-mode hero` is the **default** and is dead: it takes the retired DALL·E-era handshake, prints "paste this prompt into chat.openai.com", and exits 10. `chart_only` is the only mode that runs end to end — and since B-016b it ships a Claude-drawn hero, so its name lies too. `image_gate.check_hero_image` is PNG-only and only reachable from that dead path. |

**Success looks like:** a fresh operator running the documented command gets an
article or a *clear, actionable* failure — never a silent stall, never an abort
caused by our own retry policy, never a default flag value that cannot work.

## Scope

Three independent slices, ordered by how early they break a run. Slices 1 and 2
are bounded bug fixes with one correct answer. Slice 3 carries a real decision
and is specced with its fork explicit.

### Slice 1 — BUG-061: the retry policy must be funded

**Root cause (confirmed in code).** `stage3_runner.run_stage3` gives each writer
attempt `writer_budget_usd - writer_cost` (stage3_runner.py:656-660). That
cumulative cap is *correct* — it is the runaway guard, and it must stay. The
defect is that the **default is incoherent with `_WRITER_MAX_ATTEMPTS = 3`**:
CLI default `--writer-budget 0.60` (pipeline.py:427) against a measured ~$0.42
per Sonnet attempt funds **one** attempt, so attempt 2 starts with ~$0.18 and
dies. The failure is also mute about the cause: the operator sees a budget error,
not "your budget cannot afford the retry you configured".

**Change:**
1. Derive the default from the policy instead of a hand-picked number: one
   documented per-attempt estimate × `_WRITER_MAX_ATTEMPTS`, as a named constant
   so the two can never drift apart again.
2. Before spending on an attempt, if the remaining budget is below one attempt's
   floor, raise a `BudgetExceededError` that names the flag and the arithmetic
   ("attempt 2 of 3 needs ~$0.42, $0.18 left of --writer-budget $0.60") rather
   than half-running an attempt and reporting the SDK's generic abort.

**Not doing:** making the budget per-attempt. That silently permits 3× overspend
and removes the only runaway guard on the writer.

### Slice 2 — BUG-059: every Stage 3 model call gets a wall-clock bound

**Root cause.** `_collect_text` (stage3_runner.py:380-455) `async for`s the Agent
SDK `query()` generator with no `asyncio` timeout. `max_budget_usd` stops
spending, not waiting.

**Change:** wrap the collection in `asyncio.timeout` with a per-call
`timeout_s` parameter, defaulted per call site from measured reality — the hero
draw is the long pole at 440–600s and must not be given the writer's bound. On
expiry, raise a typed error naming which call timed out and its bound, so the
retry loops (writer, graphics) can treat it as one more malformed-output-class
failure rather than a crash.

**Not doing:** a global pipeline timeout. It cannot say *what* hung, which is the
whole point.

### Slice 3 — BUG-060 + `--image-mode`: one decision, not two patches

**Root cause.** The handshake path predates B-016b. Stage 3 now draws its own
hero SVG, so the pause-for-human-art step, the PNG gate, and both exit codes
(`EXIT_HANDSHAKE_PENDING`, `EXIT_IMAGE_GATE_FAILED`) exist to receive art from a
raster image model that Operating Constraint #4 forbids.

**The fork — needs an owner call:**

- **(a) Delete the handshake path.** Remove `--image-mode`, `--resume`,
  `--no-image`, `image_gate.py`, both exit codes; the end-to-end path becomes the
  only path. Simplest, and matches what actually works. **Cost:** removes the
  documented route for the owner to supply hero art by hand (Constraint #4 keeps
  the prompt sidecar "available if the owner wants to supply art by hand"). The
  sidecar would still be written; hand-supply would mean editing frontmatter.
- **(b) Repair and rename.** Keep `--resume` as the hand-supply route, make the
  gate format-aware instead of PNG-only (BUG-060), rename the modes truthfully
  (the working one is not "chart_only"; the broken one is not "hero"). **Cost:**
  keeps a second path alive that has never been exercised since B-016b.

**Recommendation: (a).** The handshake's only consumer was a workflow the
constraints now forbid, its operator instructions point at ChatGPT, and a route
that is never run is a route that is never right. Hand-supply survives as
"overwrite the drawn SVG and re-run Stage 4".

Either way the default mode must be the one that runs end to end.

## Commands

```
Test:   .venv/bin/python -m pytest tests/ -q
Gate:   make ci-local          # ruff, mypy, tests + coverage, bandit — the merge gate (ADR-0015)
Run:    IS_SANDBOX=1 python -m src.agent_sdk.pipeline "<topic>" --research-mode claude_web
```

## Testing Strategy

pytest, `tests/`, mocked model calls only — **no test may reach a third party**
(BUG-058, BUG-062). Each slice lands RED-first with a regression test named for
its bug id:

- Slice 1: a writer whose first attempt is malformed and whose second succeeds
  must complete under the default budget. A budget genuinely too small must fail
  with the actionable message, not the SDK's generic abort.
- Slice 2: a `_collect_text` whose generator never yields must raise the typed
  timeout inside the bound, not hang. Assert with a fake clock / tiny bound —
  never a real sleep.
- Slice 3: the default `--image-mode` (or its replacement) must reach Stage 4
  without exiting 10.

## Boundaries

- **Always:** `make ci-local` green before merge; one slice per commit; update
  `defect_tracker.json` status + `BACKLOG.md` as each lands.
- **Ask first:** slice 3's fork (above). Any change to the cumulative-budget
  semantics rather than its default.
- **Never:** add a key or paid service (Constraints #1–#3); let a test reach a
  real model; delete `--resume` before the fork is answered.

## Success Criteria

1. Under default flags, a writer run whose first attempt is malformed completes.
2. A stalled model call fails with a typed, named timeout inside its bound.
3. The default `--image-mode` runs end to end; no reachable code instructs the
   operator to use a third-party image tool.
4. `make ci-local` green; BUG-059/060/061 marked resolved with verification notes.

## Open Questions

- **Q1 (slice 3):** fork (a) delete vs (b) repair-and-rename. Recommendation (a).
- **Q2:** the per-attempt cost estimate driving slice 1's default — measured
  ~$0.42 for Sonnet. Confirm before it becomes a constant.
