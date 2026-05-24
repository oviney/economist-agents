# Plan: Path A — chart-rendered hero, human-in-the-loop featured image

**Spec**: [`docs/specs/featured-image-handshake.md`](../docs/specs/featured-image-handshake.md)
**GitHub issue**: oviney/economist-agents#403
**Date**: 2026-05-19

## Decisions locked in from spec open questions

- **Q1 (multimodal validation):** pipeline.py runs deterministic checks only (dimensions = 1792×1024 ±5%, file exists, file is PNG, file size > 50 KB). The visual-quality grade is done by the operator reading the file via the Read tool after `--resume` returns, before deploy is called. Keeps pipeline non-interactive.
- **Q2 (handoff message):** verbose — full prompt embedded inline + exact drop-path + next command, so the user can copy-paste without context-switching back to chat.
- **Q3 (timeout):** none. `--resume <slug>` is open-ended. State lives on disk; multiple pipelines can coexist identified by slug.

## Structural change

Articles move from `logs/spike/pipeline_article.md` (singleton) to `output/posts/<slug>.md` (slug-keyed). `logs/spike/pipeline_*` becomes telemetry-only. Enables `--resume <slug>` to address a specific in-flight article and matches `deploy_to_blog.py`'s mental model.

## Dependency graph

```
Task 1.1: chart_renderer module ──┐
                                  │
Task 1.2: wire chart_renderer ────┼──► Slice 1 done
into stage3                       │     (chart PNGs render)
                                  │
Task 2.1: validator image:        │
optional + file-must-exist        ├──► Slice 2 done
                                  │     (text-only / chart-only articles ship)
Task 2.2: BUG-017 false-pos fix ──┘
(#402 root-cause)

                ▼ Slice 1+2 prereq

Task 3.1: image_prompt_synth module
        │
        ▼
Task 3.2: slug-keyed output dirs + state file
        │
        ▼
Task 3.3: pipeline --resume / --no-image / exit code 10
        │
        ▼
Task 3.4: stage3_runner emits prompt artefact + handshake docs
        │
        └──► Slice 3 done (handshake works end-to-end)

                ▼ Slice 3 prereq

Task 4.1: deterministic image gate (dims, format, size, exists)
        │
        └──► Slice 4 done (--resume rejects malformed images)

                ▼ Slice 4 prereq

Task 5.1: docs/CONTRIBUTING.md update — handoff workflow
Task 5.2: full end-to-end smoke against last-merged main
```

## Task list

### Phase 1: Chart actually renders (no API path; slice 1)

- **Task 1.1**: Create `src/agent_sdk/chart_renderer.py` with `render_chart(spec: dict, output_path: Path) -> Path`
  - Acceptance: malformed spec raises `ChartRenderError`; valid spec produces a 1200×800 PNG matching Economist style (navy + accent red, single horizontal-bar layout)
  - Verify: `pytest tests/test_chart_renderer.py -v` (new file), 5+ tests covering: valid render, dimensions, malformed spec, missing data field, output dir auto-created
  - Files: `src/agent_sdk/chart_renderer.py` (new), `tests/test_chart_renderer.py` (new)
  - Estimated scope: **S** (1-2 files, ~150 LOC + ~80 LOC tests)

- **Task 1.2**: Wire `chart_renderer` into `stage3_runner.run_stage3`
  - Acceptance: after Stage 3, `output/charts/<slug>.png` exists. `Stage3Result` exposes `chart_path: Path`.
  - Verify: existing `tests/test_stage3_*.py` still pass; new integration test asserts PNG file presence after run
  - Files: `src/agent_sdk/stage3_runner.py`, `tests/test_stage3_runner.py` (new or extended)
  - Estimated scope: **S** (1 file modified, 1 test file touched)

### Checkpoint A — after Slice 1
- [ ] `pytest tests/ -q` green
- [ ] Manual: run pipeline on a topic, confirm `output/charts/<slug>.png` exists and looks reasonable (eyeball chart visual)
- [ ] Human reviews

### Phase 2: Validator accepts chart-only articles (slice 2)

- **Task 2.1**: `scripts/publication_validator.py` — `image:` becomes optional; when present, file must exist on disk
  - Acceptance: article without `image:` line passes; article with `image: /assets/images/X.png` passes IFF file at expected resolved path exists; missing file → CRITICAL FAIL with file path in message
  - Verify: new test file `tests/test_publication_validator_image_optional.py` with 4 cases (no-image-line, image-line-file-exists, image-line-file-missing, image-line-malformed-path); existing validator tests still pass
  - Files: `scripts/publication_validator.py`, `tests/test_publication_validator_image_optional.py` (new)
  - Estimated scope: **S**

- **Task 2.2**: Fix BUG-017 false positive (closes #402)
  - Acceptance: rule only fires when `image:` path and chart embed path resolve to the same basename; rule does NOT fire when hero is `/assets/images/X.png` and chart is `/assets/charts/X.png`
  - Verify: new test `tests/test_defect_prevention_bug017.py` (or extend existing), 3 cases: same-basename (fires), different-dir-same-name (does not fire), different-name (does not fire)
  - Files: `scripts/defect_prevention_rules.py`, test file
  - Estimated scope: **S**

### Checkpoint B — after Slice 2
- [ ] `pytest tests/ -q` green
- [ ] Manual: re-run validator on `logs/spike/pipeline_article.md` from yesterday with image: REMOVED — should pass cleanly (no BUG-017 false positive, no MISSING_IMAGE)
- [ ] Human reviews

### Phase 3: Image prompt handshake (slice 3)

- **Task 3.1**: Create `src/agent_sdk/image_prompt_synth.py` with `compose_prompt(title: str, summary: str, themes: list[str]) -> str`
  - Acceptance: returned prompt is non-empty; includes hard constraints (no-text, aspect ratio 1792×1024, Economist palette); does not include code-fence or markdown
  - Verify: `tests/test_image_prompt_synth.py`, 4 tests (constraints present, no markdown, empty inputs raise, long titles truncated)
  - Files: new module + new test file
  - Estimated scope: **S**

- **Task 3.2**: Slug-keyed output dirs + state file
  - Acceptance: pipeline writes article to `output/posts/<slug>.md`, chart to `output/charts/<slug>.png`, state JSON to `output/state/<slug>.json` (contains topic, stage-3 timestamp, chart path, prompt path)
  - Verify: integration test confirms file layout; existing tests that read `logs/spike/pipeline_article.md` updated
  - Files: `src/agent_sdk/pipeline.py`, `src/agent_sdk/stage3_runner.py`, several test files
  - Estimated scope: **M** (3-5 files)

- **Task 3.3**: `pipeline.py` flags `--resume <slug>` and `--no-image`; exit code 10 from default Stage 3 completion
  - Acceptance: bare `pipeline "topic"` does Stage 3, writes artefacts, prints handoff message, exits 10. `--resume <slug>` reads state, runs Stage 4. `--no-image` strips `image:` from frontmatter and runs Stage 4 without expecting a file.
  - Verify: `tests/test_pipeline_handshake.py` with 3 cases (default-exits-10, resume-with-image, resume-no-image)
  - Files: `src/agent_sdk/pipeline.py`, new test file
  - Estimated scope: **M**

- **Task 3.4**: stage3_runner writes prompt artefact + handoff message text
  - Acceptance: after Stage 3, `output/posts/<slug>.image_prompt.md` exists with the full prompt; handoff message printed to stdout contains the prompt, the drop path, and the resume command
  - Verify: existing tests still pass; new assertion checks file presence + content
  - Files: `src/agent_sdk/stage3_runner.py`
  - Estimated scope: **S**

### Checkpoint C — after Slice 3
- [ ] `pytest tests/ -q` green
- [ ] Manual: run pipeline on a topic. Confirm exit 10. Confirm prompt artefact exists. Run `--resume <slug> --no-image`. Confirm article finalised without `image:`.
- [ ] Human reviews

### Phase 4: Deterministic image gate (slice 4)

- **Task 4.1**: Deterministic image validation in `--resume <slug>` (no `--no-image`)
  - Acceptance: when image at `output/posts/images/<slug>.png` is missing or not 1792×1024 (±5%) or not PNG or <50 KB, `--resume` exits with code 11 and a clear message (separate from research errors 2/3 and handoff 10)
  - Verify: `tests/test_image_gate.py` with 4 cases (passes, missing, wrong-dims, wrong-format)
  - Files: `src/agent_sdk/pipeline.py` (or new `image_gate.py`), test file
  - Estimated scope: **S**

### Checkpoint D — after Slice 4
- [ ] `pytest tests/ -q` green
- [ ] Manual: drop a non-1792×1024 image, confirm exit 11. Drop a correct one, confirm Stage 4 completes.
- [ ] Human reviews

### Phase 5: Docs + smoke (slice 5)

- **Task 5.1**: `docs/CONTRIBUTING.md` — handoff workflow section (3-paragraph + example commands)
  - Acceptance: section "Generating a featured image" with the exact paste-prompt-into-ChatGPT workflow, drop path, and resume command
  - Verify: manual review
  - Files: `docs/CONTRIBUTING.md`
  - Estimated scope: **XS**

- **Task 5.2**: End-to-end smoke against last-merged main
  - Acceptance: run pipeline on a topic; do handshake; deploy to blog repo (dry-run); confirm no broken-image regressions
  - Verify: deploy `--dry-run` exits 0 and the validation report inside it shows no MISSING_IMAGE or BUG-017
  - Files: none — orchestration step
  - Estimated scope: **XS**

### Checkpoint E — done
- [ ] All slices verified
- [ ] PR opened (one branch, multiple commits per slice — matches the #388 / #395 pattern from this session)
- [ ] Issue #402 closed in same PR
- [ ] Human approves merge

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Chart spec schema varies across topics | Medium | Task 1.1 raises `ChartRenderError` with clear field-by-field validation; test with 3 real captured spec JSONs |
| Slug derivation differs from existing deploy script | High | Verify existing slug logic before Task 3.2; reuse the same function |
| `output/posts/<slug>.md` collides across runs | Low | State file includes timestamp; same slug overwrites (current single-pipeline behaviour) |
| Image-gate `±5% dimension tolerance` is wrong target | Low | Make tolerance configurable via env var; default 5% |
| User runs `--resume` without ever running default | Low | State file absent → clear error: "no state for slug X; run pipeline 'topic' first" |

## Parallelization

- Tasks 1.1 + 2.1 + 2.2 + 3.1 are **independent** — could run in parallel if the workforce allowed. I will do them sequentially since I am the workforce.
- Tasks 1.2 and 3.2 both touch `stage3_runner.py` — must be sequential.

## Open questions

None — Q1/Q2/Q3 from the spec are now locked. Will surface anything new in implementation.
