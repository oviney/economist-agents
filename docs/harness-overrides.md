# Harness overrides — accepted complexity

**Owner:** Ouray Viney · **Sensor:** `scripts/complexity_sensor.py` (B-032)
**Spec:** `docs/specs/harness-engineering.md` · **Audit:** `docs/reviews/harness-engineering-assessment-2026-07-29.md`

---

## What this file is

The complexity sensor does not silently pass or silently suppress. When it fires, the agent
has exactly two legitimate responses:

1. **Refactor** — split the function, hoist a guard clause, name a helper.
2. **Record an override here**, with a one-line justification.

A bare `# noqa: C901` is **not** a legitimate response. The whole point of the register is
that accepted complexity is *visible at review time*. Boeckeler's framing (SE Radio 730):
the reason nobody tunes a static-analysis baseline by hand is that it is too tedious, and
the reason the resulting noise gets ignored is that the exceptions are invisible. An agent
will happily do the tedious part — so the exceptions become a short, reviewable list
instead of a scatter of suppressions nobody reads.

**Read this file as the owner's review queue.** Every line is a decision to re-examine.

## Format

One bullet per override. The backticked key must be exactly `path::function` — that is what
the sensor matches on, so a typo silently grants no exemption (fail-closed by design).

```markdown
- `scripts/foo.py::bar` — dispatch table; splitting it would obscure the mapping
```

## Active overrides

- `scripts/sync_copilot_context.py::format_anti_patterns_section` — three parallel
  group-by-and-emit blocks (defects, QA skills, architecture); pre-existing and untouched by
  B-035 Task 3(b), which changed only `update_copilot_instructions`. Splitting it is a
  worthwhile cleanup but is not this bug fix's scope. **Review queue: pay down when this
  formatter is next edited for its own sake.**
- `scripts/sync_copilot_context.py::extract_architecture_patterns` — a line-oriented
  markdown parser; the branch count is the grammar. Same provenance as above: pre-existing,
  not touched by Task 3(b).

## Day-one baseline (NOT overrides)

The audit measured the following on `src/` + `scripts/` at the time the sensor landed.
These are **not** exempted: the sensor is scoped to files an agent touches, so this backlog
is *recorded* rather than retroactively enforced. Each entry becomes live the first time
something edits that file — which is the right moment to pay it down.

```
41  C901     complex-structure         worst: generate_economist_post (33 > 10),
                                       validate (28), review_writer_output (24),
                                       apply_editorial_fixes (21), run_editorial_board (20)
28  PLR0912  too-many-branches
21  PLR0913  too-many-arguments
18  PLR0915  too-many-statements
 8  PLR0911  too-many-return-statements
```

Reproduce with:

```bash
.venv/bin/ruff check --select C901,PLR0911,PLR0912,PLR0913,PLR0915 \
  --no-fix --statistics src scripts
```

## Raising the threshold

`max-complexity` lives in `ruff.toml` under `[lint.mccabe]` — one number, one place.
Raising it is an **ask-first** decision per the spec's Boundaries: it weakens the sensor for
every file at once, which is precisely the move that turns a gate into decoration.
