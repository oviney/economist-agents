# Spec — No sensor ships without a proof it can fail (B-043)

**Status:** DRAFT — awaiting owner LGTM · **Opened:** 2026-08-01
**Absorbs:** B-040 (review-gate calibration) as the inferential-sensor arm
**Framework:** `docs/reviews/harness-engineering-assessment-2026-07-29.md` (SE Radio 730,
Birgitta Boeckeler on harness engineering)

## Objective

The 2026-07-29 assessment graded this repo *guide-maximal, sensor-disconnected* and B-030…
B-035 fixed the wiring. Sensors now fire in the agent's loop. **The next failure mode is that
nothing validates the sensors themselves**, and 2026-08-01 produced four independent proofs of
it in a single day.

Make it structurally impossible to add a sensor that cannot fail, by requiring every sensor to
ship with a test that **deliberately breaks something and asserts the sensor notices**.

### The evidence, all measured on 2026-08-01

| Finding | What kind of sensor failure |
|---|---|
| **B-039** — `(mypy \|\| echo "advisory")` returned **exit 0** against a stub `mypy` exiting 127; `make ci-local` ran homebrew's ruff 0.15.9 while `requirements-dev.txt` pins 0.14.10 | A **fifth** inert sensor, found *after* B-031 fixed four |
| **B-040** — the `blog-post-review` gate has run once, by hand, and has no ground truth | A sensor that **never runs** |
| **B-041** — `agent_sdk_costs.jsonl` recorded only runs where the hero succeeded, hiding a 10× duration swing | A **biased** sensor — worse than none, because it looked authoritative |
| **B-042** — `missing_chart` is CRITICAL, so a brief with one number still required a chart; the writer invented four percentages, then `orphaned_chart` required prose describing them | A sensor whose **setpoint manufactured the defect** it exists to prevent |

**B-031 fixed four named sensors. It did not fix the class**, which is why B-039 was still
there to find. That is the whole argument for a standing check rather than another audit.

### The technique already exists — three times, at a terminal, unrecorded

Every one of those findings was settled the same way: mutate something, then check whether the
sensor notices.

```
added `table` to CHROME_TAGS          → no-drop invariant reported 48 lost words   ✓ teeth
old `(mypy || echo advisory)` vs a
  stub mypy exiting 127               → exit 0                                     ✗ no teeth
`export PATH := .venv/bin:$(PATH)`
  vs a stub `ruff` printing a marker  → the ambient ruff still ran                 ✗ the fix was wrong
```

The third one matters most: it caught a fix that was **wrong and looked right**. `make showpath`
confirmed the exported PATH; GNU make 3.81 direct-execs metacharacter-free recipe lines and
resolves them against its own startup PATH. Only running a recipe against a stub binary showed
it. A grep of the Makefile would have passed on a change that fixed nothing.

Two of the three survive only because they happened to land in tests being written anyway.
The technique is real, repeatable, and currently depends on whoever is at the keyboard
remembering to use it.

### Measured baseline

Thirteen sensor scripts in `scripts/`. `lint_adrs.py` and `check_bare_name_imports.py` have
**zero tests**. The rest have unit tests — *does the code work* — not efficacy tests — *does it
fire on a real defect*. Only `tests/test_ci_gate_is_reproducible.py` and the budget tests in
`tests/test_hero_author.py`, both written 2026-08-01, assert efficacy.

## The design constraint that decides everything

**The fix must be a sensor, not a guide.**

Writing *"every sensor must have a teeth test"* into `skills/defect-prevention/SKILL.md` would
reproduce the exact failure this repo was graded down for. The strongest guide in the codebase
— `CLAUDE.md` constraint #1, *"NO new API keys. Ever."* — had **zero computational backing**
until B-030 gave it a `PreToolUse` deny. B-028 is the same story: the review stage existed as
prose while `deploy_to_blog.py` defaulted to `post`, and the default won.

A rule nothing enforces gets skipped. So B-043 ships as a check in `make ci-local` that fails
when a sensor has no proof — and it is itself a sensor, so it needs its own proof.

## Design

### A register, a proof per entry, a check that both exist

```
docs/sensors/register.yaml        # one entry per sensor
scripts/check_sensor_proofs.py    # the sensor: register ↔ reality ↔ proofs
tests/test_check_sensor_proofs.py # its own proof, plus unit tests
```

Register entry:

```yaml
- id: destructive_change_guard
  script: scripts/destructive_change_guard.py
  regulates: >-
    Critical files being gutted — a large deletion that passes tests because the
    tests went with it.
  proof: tests/test_destructive_change_guard.py::test_gutting_a_critical_file_is_caught
  mutation: >-
    Truncate a file listed as critical to a stub, run the guard, assert non-zero.
```

`check_sensor_proofs.py` fails when:

1. A `scripts/*.py` matching the sensor pattern is **absent from the register** — the case that
   catches a *new* sensor added without a proof, which is the whole point.
2. A register entry names a `proof` that **does not exist**, is skipped, or is xfail.
3. An entry is missing `regulates` or `mutation` — a proof whose reasoning is not written down
   cannot be re-adjudicated when the sensor changes.

### The inferential arm — B-040 folds in here

B-040 specced calibrating `blog-post-review` and produced eight labelled cases in
`docs/evals/review-gate/cases/`. That is the same idea in the other half of Boeckeler's
taxonomy: computational sensors are proved by mutation, **inferential sensors are proved by
labelled cases with known verdicts**. Both answer "does this sensor notice a real defect?"

Keeping them as one item means the register covers both kinds and there is one answer to
"which sensors are proved?" rather than two. `docs/specs/review-gate-calibration.md` stays as
the detailed design for the inferential runner; its sequencing is unchanged — **build after
n≈5 real reviews**, which accrue free from the B-013 review stage.

### Deliberately weak where it should be

The checker verifies a proof **exists and runs**. It cannot verify the proof is *genuine* — a
test named `test_gutting_a_critical_file_is_caught` that asserts `True` would pass. Making it
gameable-proof would mean mutation-testing the mutation tests, which is where the value curve
goes flat.

**Stating the limit is the honest design.** Genuineness is a review-time concern, and the
`mutation:` field exists so a reviewer can check the claim against the test in one glance
without reading the whole file.

## Commands

```bash
python scripts/check_sensor_proofs.py            # the gate; exits non-zero on any of the three
python scripts/check_sensor_proofs.py --list     # what is registered, what is proved
make ci-local                                    # runs it as a gate step
```

## Testing strategy

TDD per `agent-skills:test-driven-development`. Deterministic, keyless, no network:

- **Its own proof of teeth**, which is the load-bearing test: point the checker at a fixture
  tree containing a sensor script absent from the register, and assert it fails. A checker that
  cannot fail is the joke this item exists to prevent.
- A register entry naming a nonexistent proof fails
- A register entry whose proof is `@pytest.mark.skip` fails — skipping is how a proof rots
  quietly
- An entry missing `regulates` or `mutation` fails
- A complete, honest register passes
- The real register in the repo passes (so the gate is green on `main` from the first commit)

## Boundaries

- **Always:** ship the register with every sensor already in it, so the gate is green
  immediately rather than after a backfill sprint; state the genuineness limit in the script's
  own docstring, not just here.
- **Ask first:** adding a sensor to the register with `proof: none` and a documented reason —
  that is an override, and per the harness-override convention it belongs in
  `docs/harness-overrides.md` where a reviewer sees it.
- **Never:** satisfy the checker with a proof that does not mutate anything; make the checker
  advisory (`|| true` is the exact defect B-031 removed from `validate_badges`); write the rule
  into a `SKILL.md` and call it done.

## Success criteria

- [ ] `scripts/check_sensor_proofs.py` runs in `make ci-local` and fails on an unregistered sensor
- [ ] Every sensor script in `scripts/` appears in `docs/sensors/register.yaml`
- [ ] `lint_adrs.py` and `check_bare_name_imports.py` — the two with **zero** tests — get proofs first
- [ ] The three mutation proofs run by hand on 2026-08-01 exist as tests, not as shell history
- [ ] The checker has its own proof of teeth
- [ ] `make ci-local` green; ≥80% coverage on the new module; no new dependency, no key, no network

## Implementation order

1. **The checker plus its own proof of teeth**, register empty. Proves the mechanism fails
   correctly before anything depends on it.
2. **Backfill the register** with all thirteen sensors. Entries may start `proof: none` with a
   recorded reason so the gate goes green on a true baseline rather than a fictional one.
3. **`lint_adrs` and `check_bare_name_imports`** — zero tests today, so the largest real gap.
4. **Publication-path sensors** — `publication_validator`, `destructive_change_guard`. Highest
   blast radius: these are what stand between a fabricated article and the live blog.
5. **Retire the `proof: none` entries** one at a time. The count is the burndown, and it is
   visible in `--list` rather than in someone's head.

## Not in scope for v1

- **Mutation-testing the whole codebase** (`mutmut`, `cosmic-ray`). This is about sensors
  proving they fire, not about coverage quality, and a repo-wide mutation run is a different
  cost class entirely.
- **Auto-generating proofs.** A generated proof measures the generator.
- **The inferential runner.** Specced in `review-gate-calibration.md`, still waiting on n≈5.
- **Fixing B-042.** Its own item; a proof-of-teeth would not have caught it, because
  `missing_chart` fires *correctly* — the defect is the setpoint, not the sensor.

## Open questions

1. **What counts as a sensor?** Proposed: anything whose non-zero exit or emitted issue can
   block a commit, a push, `ci-local`, or a publish. That includes `publication_validator` and
   excludes `article_evaluator` (it scores, it does not gate). Worth the owner's ruling, because
   it sets the register's boundary and therefore the gate's scope.
2. **Do pre-commit hooks count separately from the scripts they invoke?** A hook can be inert
   while its script is fine — `validate_badges` was `|| true` for exactly that reason. Leaning
   yes, as register entries with the hook id as `id`.
3. **B-042 has no home in this taxonomy.** A sensor with the wrong setpoint is neither inert nor
   inaccurate; it works, and the system is worse for it. Boeckeler's framework does not name it.
   Worth an ADR on its own, separate from this spec.
