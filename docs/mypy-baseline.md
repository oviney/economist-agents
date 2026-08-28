# mypy baseline — grandfathered type errors

**Owner:** Ouray Viney · **Gate:** `scripts/mypy_baseline.py` (B-035 Task 2)
**Spec:** `docs/specs/b035-harness-decisions.md` · **Sibling register:** `docs/harness-overrides.md`

---

## What this file is

B-031 took mypy off `stages: [manual]`, making it able to fail for the first time. The
measurement then showed what that cost:

| Measurement (2026-07-30) | Value |
|---|---|
| `scripts/*.py` files | 48 |
| mypy-clean under `--follow-imports=silent` | 36 |
| Would block a commit **merely by being touched** | **12 (25%)** |

One commit in four blocked by errors it did not introduce — including
`publication_validator.py`, `editorial_board.py` and, pointedly,
`destructive_change_guard.py`. That is the noise-overload failure mode that gets a gate
reverted to `manual`, which is how mypy went inert in the first place.

**The answer is not a weaker guide.** `CLAUDE.md` keeps "Type hints mandatory". This file
records what each known-dirty file is grandfathered at, and the gate blocks only on errors
*beyond* that count. A new error in a baselined file still blocks — **the baseline is a
per-file count, not a mute.** With it, the guide becomes *true for all new code* instead of
aspirational.

B-032 built this exact mechanism for complexity. One mechanism, two sensors.

## The baseline can only shrink

`tests/test_mypy_baseline.py` fails if:

- any file's measured count **exceeds** its entry here (a new error), **or**
- any file **improved** but kept its old allowance (a stale entry), **or**
- an entry names a file that no longer exists.

So raising a number to unblock a commit does not work: it fails the suite instead of the
commit. The only way out is down. Remove the entry entirely when a file reaches zero.

## Format

One bullet per file. The backticked path is repo-relative; the number is the error count
the file is grandfathered at.

```markdown
- `scripts/foo.py` — 8
```

## Baseline

Measured 2026-08-27 with:

```bash
.venv/bin/python -m mypy --config-file=mypy.ini --follow-imports=silent \
  --no-error-summary scripts/*.py
```

*(No grandfathered errors — all 48 scripts/ files are mypy-clean).*

## Read this as the owner's review queue

Every line is debt with a name on it. The list is currently empty because all grandfathered errors have been resolved.
