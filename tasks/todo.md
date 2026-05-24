# TODO: Path A — chart-rendered hero, human-in-the-loop featured image

**Plan**: [`tasks/plan.md`](./plan.md)
**Spec**: [`docs/specs/featured-image-handshake.md`](../docs/specs/featured-image-handshake.md)

## In Progress

- **Slice 4** — deterministic image gate

## Slice 1 — chart actually renders ✅ (commit aaf56f3)

- [x] **Task 1.1**: create `src/agent_sdk/chart_renderer.py` + `tests/test_chart_renderer.py` (15 tests)
- [x] **Task 1.2**: wire `chart_renderer` into `stage3_runner.run_stage3`; `Stage3Result.chart_path` exposed (+6 wire-up tests)
- [x] **Checkpoint A**: pytest 2166 green; manual eyeball confirms Economist-style chart on real spec

## Slice 2 — validator accepts chart-only articles ✅ (commit 0f36289)

- [x] **Task 2.1**: `publication_validator.py` — `image:` optional, file-must-exist via `require_image_file=True`
- [x] **Task 2.2**: BUG-017 false-positive fix (path comparison); closes #402
- [x] **Checkpoint B**: pytest 2183 green; yesterday's article minus image: validates cleanly

## Slice 3 — image prompt handshake ✅

- [x] **Task 3.1**: `src/agent_sdk/image_prompt_synth.py` + 12 tests
- [x] **Task 3.2**: slug-keyed output dirs (`output/posts/<slug>.md`, `output/charts/<slug>.png`, `output/state/<slug>.json`)
- [x] **Task 3.3**: `pipeline.py` `--resume <slug>` + `--no-image` + exit code 10
- [x] **Task 3.4**: `stage3_runner` writes `output/posts/<slug>.image_prompt.md` + verbose handoff message
- [x] **Checkpoint C**: pytest 2207 green (+12 handshake tests, +12 prompt synth tests)

## Slice 2 — validator accepts chart-only articles

- [ ] **Task 2.1**: `publication_validator.py` — `image:` becomes optional, file-must-exist when present
- [ ] **Task 2.2**: BUG-017 false-positive fix (path comparison; closes #402)
- [ ] **Checkpoint B**: pytest green; manual re-validate yesterday's article

## Slice 3 — image prompt handshake

- [ ] **Task 3.1**: `src/agent_sdk/image_prompt_synth.py` + tests
- [ ] **Task 3.2**: slug-keyed output dirs (`output/posts/<slug>.md`, `output/charts/<slug>.png`, `output/state/<slug>.json`)
- [ ] **Task 3.3**: `pipeline.py` `--resume <slug>` + `--no-image` + exit code 10
- [ ] **Task 3.4**: `stage3_runner` writes `output/posts/<slug>.image_prompt.md` + verbose handoff message
- [ ] **Checkpoint C**: pytest green; manual run-pipeline → exit 10 → resume --no-image → article finalised

## Slice 4 — deterministic image gate

- [ ] **Task 4.1**: dims/format/size/exists check in `--resume`; exit 11 on fail
- [ ] **Checkpoint D**: pytest green; manual wrong-dims rejection + correct-image acceptance

## Slice 5 — docs + smoke

- [ ] **Task 5.1**: `docs/CONTRIBUTING.md` — "Generating a featured image" section
- [ ] **Task 5.2**: end-to-end smoke via deploy `--dry-run`
- [ ] **Checkpoint E**: PR opened, #402 closed in same PR, human approves merge

## Done

_(none yet — implementation has not started)_

## Blocked / Deferred

_(none)_
