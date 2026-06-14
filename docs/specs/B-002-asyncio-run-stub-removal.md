# Spec: B-002 — Remove `asyncio.run` stub in `test_flow_agent_sdk.py`

> Slice 2 of the 2026-06-14 backlog sprint (see `BACKLOG.md` → Sprint Goal).
> Source item: `BACKLOG.md` B-002 (was GitHub #425). `type:refactor`, test-only.

## Objective

`tests/test_flow_agent_sdk.py` patches `flow.asyncio.run` to a stub. Because the
real `asyncio.run` is replaced, the `run_pipeline(...)` / `refine_image_metadata(...)`
**coroutines that `flow.generate_content` constructs are never awaited**, so each
test emits `RuntimeWarning: coroutine '...' was never awaited`. That warning class
is noise that would **mask a real future un-awaited-coroutine leak**.

`tests/test_flow_image_mode.py` (PR #424) already solved this: it patches
`run_pipeline` / `refine_image_metadata` as `AsyncMock` and lets the **real**
`asyncio.run` drive them — no warnings.

**Success = the migrated tests assert the same behaviour as today, emit zero
`coroutine ... was never awaited` warnings, and the suite passes with
`-W error::RuntimeWarning` on the touched tests.**

## Root cause (verified 2026-06-14)

`flow.generate_content` (`src/economist_agents/flow.py:276`, `:398`) and
`flow.request_revision` (`:634`) call `asyncio.run(run_pipeline(...))` and
`asyncio.run(refine_image_metadata(...))`. When a test does
`@patch("src.economist_agents.flow.asyncio.run")`, Python still **evaluates the
argument** — i.e. constructs the coroutine — before handing it to the mock, which
returns a fake result without awaiting it. The orphaned coroutine triggers the
`RuntimeWarning` at GC time. Patching the awaited callables as `AsyncMock` instead
means no real coroutine is ever constructed, so there is nothing to leak.

Per-mode call shape (confirmed by reading `flow.py:268-407`):

| Flow path | `asyncio.run` calls today | Awaited callables to mock |
|-----------|---------------------------|---------------------------|
| `generate_content`, `chart_only` (default) | **1** (`run_pipeline`) | `run_pipeline` only |
| `generate_content`, `hero` | **2** (`run_pipeline`, then `refine_image_metadata`) | both |
| `request_revision` | **1** (`run_pipeline`) | `run_pipeline` only |

Note: in `chart_only`, `refine_image_metadata` is **never called** — so the second
`side_effect` value in `test_calls_pipeline_and_returns_article` is dead code today.

## Scope decision (needs LGTM)

B-002's title scopes to `TestGenerateContent`. But **two other test classes in the
same file patch `flow.asyncio.run` and leak the identical warning**:
`TestRequestRevision` (2 tests) and `TestKickoffResultFile` (4 tests).

**Recommendation — migrate all `asyncio.run`-patching tests in this one file (9
tests across 3 classes).** Rationale: B-002's stated *goal* is "stop the
un-awaited-coroutine warnings so they don't mask a future real leak." Migrating only
`TestGenerateContent` leaves 6 tests in the same file emitting the same warning,
which defeats that goal — the warning class survives and a future `-W error` gate
can't be turned on cleanly. The fix is mechanical, identical per test, test-only, and
the reference pattern (`test_flow_image_mode.py`) already proves it. Staying strictly
within the title would be scope discipline at the cost of the actual objective.

*Alternative if you'd rather keep the slice literal:* migrate `TestGenerateContent`
(3 tests) only and open a B-NNN follow-up for the other six. I do not recommend this —
it splits one mechanical change across two sessions for no risk reduction.

→ **Please pick the scope before I build.** Spec below assumes the recommended
(whole-file) scope.

## The one design change beyond mechanical substitution

`test_refine_image_metadata_called_via_asyncio_run` (`:211-236`) asserts directly on
`mock_asyncio_run.call_count == 2` and that the 2nd positional arg
`iscoroutine(...)`. Those assertions are **coupled to the `asyncio.run` seam we are
removing** — they cannot survive the migration verbatim.

Rewrite to assert the intent-preserving equivalent against the `AsyncMock`:

```python
mock_refine.assert_awaited_once()
assert mock_refine.await_args.args[0] == image_path  # or .kwargs, per call site
```

This is strictly *better*: it verifies `refine_image_metadata` was actually awaited
with the right argument, instead of asserting an implementation detail of how the
flow reaches the event loop. It mirrors `test_flow_image_mode.py`'s
`mock_run_pipeline.await_args.kwargs` style. The test will be renamed to
`test_hero_mode_awaits_refine_image_metadata` to reflect what it now proves.

## Migration pattern (from `test_flow_image_mode.py:80-116`)

Before:
```python
@patch("src.economist_agents.flow.generate_featured_image", return_value=False)
@patch("src.economist_agents.flow.asyncio.run")
def test_calls_pipeline_and_returns_article(self, mock_asyncio_run, mock_image):
    mock_asyncio_run.side_effect = [_passing_pipeline_result(), {...}]
```

After:
```python
@patch("src.economist_agents.flow.generate_featured_image", return_value=False)
@patch("src.economist_agents.flow.run_pipeline", new_callable=AsyncMock)
def test_calls_pipeline_and_returns_article(self, mock_run_pipeline, mock_image):
    mock_run_pipeline.return_value = _passing_pipeline_result()
```

Hero-mode tests additionally patch
`@patch("src.economist_agents.flow.refine_image_metadata", new_callable=AsyncMock)`
and set `mock_refine.return_value = {"image_alt": ..., "image_caption": ...}`.

`TestKickoffResultFile` uses a shared `_run_kickoff` helper plus per-test decorator
stacks — both the helper's `mock_asyncio_run.side_effect = [...]` wiring and the
decorator stacks migrate to the two `AsyncMock` patches. The revision-path test
(`:937`) sets two pipeline results because it triggers generate **and** revision;
both become `mock_run_pipeline.side_effect = [failing, failing]`.

## Commands

```
Run touched file:   .venv/bin/pytest tests/test_flow_agent_sdk.py -q
Prove no warnings:  .venv/bin/pytest tests/test_flow_agent_sdk.py -q -W error::RuntimeWarning
Full regression:    .venv/bin/pytest -q
Lint:               .venv/bin/ruff check tests/test_flow_agent_sdk.py
```

## Scope of changes (1 file)

| File | Change |
|------|--------|
| `tests/test_flow_agent_sdk.py` | Replace `@patch(...asyncio.run)` with `AsyncMock` patches of `run_pipeline` / `refine_image_metadata` across `TestGenerateContent`, `TestRequestRevision`, `TestKickoffResultFile`; rewrite the one `asyncio.run`-introspecting test to assert `await`; add `AsyncMock` to the imports. No production code changes. |

The `from unittest.mock import Mock, patch` import gains `AsyncMock`.
`flow.py` is **not** touched — this is test-only.

## Testing Strategy

This *is* a test refactor, so verification is behavioural-equivalence + warning-free:

1. Each migrated test asserts the **same** observable outcomes it asserts today
   (article content, `featured_image`, scores, deploy routing, result-JSON fields).
   No assertion is weakened; the one introspection test is strengthened (see above).
2. `pytest tests/test_flow_agent_sdk.py -W error::RuntimeWarning` must pass — this is
   the regression guard that proves the warning class is gone.
3. Full-suite `pytest -q` stays green (no collateral).

## Boundaries

- **Always:** keep every existing assertion's intent; run the `-W error` check.
- **Ask first:** widening scope beyond this file; touching `flow.py`.
- **Never:** delete a test to silence a warning; weaken an assertion; patch
  `asyncio.run` again anywhere in this file.

## Success Criteria

- [ ] No `@patch("src.economist_agents.flow.asyncio.run")` remains in the file.
- [ ] `pytest tests/test_flow_agent_sdk.py -q -W error::RuntimeWarning` exits 0.
- [ ] `pytest -q` (full suite) stays green.
- [ ] `ruff check tests/test_flow_agent_sdk.py` clean.
- [ ] Every migrated test preserves its original observable assertions; the
      `asyncio.run`-introspection test is rewritten to assert `await` instead.
- [ ] `BACKLOG.md` B-002 moved to Done; PR merged to `main`.

## Open Questions

1. **Scope** (above): whole-file (recommended) vs. `TestGenerateContent`-only? Need LGTM.
2. Should `-W error::RuntimeWarning` be wired into the project's pytest config as a
   permanent gate, or just run as a one-off verification for this PR? (Default: one-off
   for this PR; a permanent gate is a separate, larger backlog item since it would need
   the whole suite to be warning-clean first.)
