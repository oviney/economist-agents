# TODO: Path A — chart-rendered hero, human-in-the-loop featured image

**Plan**: [`tasks/plan.md`](./plan.md)
**Spec**: [`docs/specs/featured-image-handshake.md`](../docs/specs/featured-image-handshake.md)

## In Progress

- [ ] **Task 5.2**: end-to-end smoke (deferred to human verification; requires a live pipeline run + image generation in ChatGPT)
- [ ] **Checkpoint E**: human approves PR #404 for merge

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

## Slice 4 — deterministic image gate ✅

- [x] **Task 4.1**: `src/agent_sdk/image_gate.py` + wired into `_run_resume` (exits 11 on fail)
- [x] **Checkpoint D**: pytest 2218 green (+11 gate tests covering missing/too-small/wrong-magic/wrong-dims + 4 wire-up cases)

## Slice 5 — docs + smoke

- [x] **Task 5.1**: `CONTRIBUTING.md` — "Generating an article — the image handshake (#403)" section with exit codes table + workflow steps
- [ ] **Task 5.2**: end-to-end smoke (deferred to human verification post-merge; requires ~$0.30 pipeline run + image generation in ChatGPT)
- [x] **Checkpoint E**: PR #404 opened; closes #402 in same PR

## Done

- [x] Slices 1-5 implementation complete in PR #404
- [x] Automated regression coverage complete

## Blocked / Deferred

- [ ] Live end-to-end smoke: requires a paid Stage 3 run and human-generated hero image
- [ ] `run_flow()` handshake migration: tracked separately in #410
