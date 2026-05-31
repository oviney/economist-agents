# SPEC: Path A — chart-rendered hero, human-in-the-loop featured image

**Status**: IMPLEMENTED in PR #404 (end-to-end human smoke pending)
**GitHub issue**: oviney/economist-agents#403
**Date**: 2026-05-19
**Supersedes for default path**: `scripts/featured_image_agent.py` (DALL-E auto path remains opt-in for users with `OPENAI_API_KEY`)

---

## 1. Objective

Today the pipeline emits an article whose YAML frontmatter promises a hero image and a chart PNG that were never rendered. Deploy ships broken `<img>` tags. Two distinct defects:

- **Defect A — chart never rendered.** Stage 3 produces `pipeline_chart.json` (a spec) and never converts it to a PNG. No matplotlib step exists.
- **Defect B — featured image never generated.** `featured_image_agent.py` exists but is not wired; the writer prompt still emits an `image:` line that points to a nonexistent file.

This spec defines a fix that:

1. Always renders the chart locally via matplotlib (no API, no key, deterministic).
2. Replaces the DALL-E auto-call with a **prompt-handoff handshake**: the pipeline generates an editorial illustration prompt, pauses, the human runs that prompt in ChatGPT web, drops the resulting PNG at a known path, then resumes Stage 4 which validates the image via multimodal Read.
3. Lets the article ship without a hero image when the human declines the handshake — chart becomes the sole visual.

## 2. Tech Stack

- matplotlib (already in `requirements.txt`) for chart rendering
- `claude_agent_sdk` for prompt synthesis (already wired)
- Multimodal `Read` tool for image validation (Claude Code built-in; human-orchestrated, not pipeline-orchestrated — see Decision Q1)
- No new dependencies, no new API keys

## 3. Commands

```bash
# Stage 1-3 (research + writer + chart-spec + chart-render + prompt-synth):
python -m src.agent_sdk.pipeline "topic"

# After Stage 3 the pipeline pauses with a clear handoff message and exits 10
# (new exit code). Output includes:
#   - output/posts/<slug>.md             (article draft)
#   - output/charts/<slug>.png           (rendered chart)
#   - output/posts/<slug>.image_prompt.md (prompt to paste into ChatGPT)
# Expected drop path: output/posts/images/<slug>.png

# After dropping the image, OR choosing to skip:
python -m src.agent_sdk.pipeline --resume <slug>              # with image
python -m src.agent_sdk.pipeline --resume <slug> --no-image   # chart-only
```

## 4. Project Structure

```
src/agent_sdk/
  pipeline.py              ← +--resume, +--no-image, +exit-code 10/11
  stage3_runner.py         ← +chart_renderer call; +prompt-synth call
  image_prompt_synth.py    ← NEW — composes editorial illustration prompt
  chart_renderer.py        ← NEW — chart.json -> PNG via matplotlib

scripts/
  featured_image_agent.py  ← unchanged; remains opt-in for DALL-E path
  publication_validator.py ← image: required -> image: optional-but-must-exist
  defect_prevention_rules.py ← BUG-017 false-positive fix (path comparison)

output/
  posts/<slug>.md                 ← article (canonical location)
  posts/<slug>.image_prompt.md    ← handoff artefact
  posts/images/<slug>.png         ← human drops file here
  charts/<slug>.png               ← chart renderer output
  state/<slug>.json               ← stage-3 state file for --resume

logs/spike/
  pipeline_metrics.json    ← telemetry only (no longer canonical artefacts)

docs/specs/
  featured-image-handshake.md     ← THIS FILE

CONTRIBUTING.md            ← +handoff workflow section

tasks/
  plan.md                  ← per-feature plan
  todo.md                  ← per-feature task list
```

## 5. Code Style

Chart renderer interface (new module):

```python
def render_chart(spec: dict, output_path: Path) -> Path:
    """Render an Economist-style chart from a Stage 3 chart spec.

    Spec shape (existing, unchanged):
        {"title": str, "subtitle": str,
         "data": [{"metric": str, "value": float, "unit": str, "color": str}],
         "source": str}

    Returns the written path on success. Raises ChartRenderError on
    malformed spec or matplotlib failure.
    """
```

Prompt synthesis returns a single multi-line string in this format:

```
[Editorial illustration in The Economist's style — bold, high-contrast, no text]

Subject: <one-sentence visual metaphor>
Mood: <e.g. satirical, ominous, dispassionate>
Composition: <e.g. one figure centred, three small figures at edges>
Palette: Economist red #E3120B, deep navy, off-white, one accent
Aspect ratio: 1792x1024 (landscape hero)
Constraints: no text, no words, no captions, no logos
```

## 6. Testing Strategy

- pytest, mirrors existing `tests/test_*` layout
- New tests:
  - `tests/test_chart_renderer.py` — spec → PNG; malformed spec raises; output file exists with expected dimensions
  - `tests/test_image_prompt_synth.py` — given article + title, prompt contains required clauses (no-text constraint, aspect ratio, Economist palette)
  - `tests/test_pipeline_handshake.py` — Stage 3 writes prompt artefact and exits 10; `--resume <slug>` reads dropped image and runs Stage 4; `--no-image` strips `image:` and runs Stage 4
  - `tests/test_publication_validator_image_optional.py` — validator accepts articles without `image:`; still rejects when `image:` references a nonexistent file
  - `tests/test_defect_prevention_bug017.py` — BUG-017 rule fires only when hero + chart point to the same asset (not when paths differ by directory)
- Target ≥ 80% coverage on new modules; `src/quality/*` per-module gate (90%) unchanged
- One end-to-end smoke test gated on `RUN_E2E=1` (skipped by default; runs the full real pipeline once)

## 7. Boundaries

**Always:**
- Render the chart on every Stage 3 (no flag)
- Generate the image prompt on every Stage 3 (no flag)
- Run deterministic image gate (dims, format, size) in `--resume` before Stage 4
- Articles can ship without `image:` line (chart-only mode)

**Ask first:**
- Adding any new third-party image service (Replicate, HF, Gemini, etc.)
- Changing the editorial-illustration prompt template significantly
- Modifying the chart spec schema (it is the LLM's output contract)
- Removing the DALL-E opt-in path (`featured_image_agent.py`)

**Never:**
- Auto-call a paid image API as the default path
- Ship an article whose `image:` references a file not on disk
- Embed PII or proprietary data in the prompt artefact

## 8. Success Criteria

1. Running `python -m src.agent_sdk.pipeline "<topic>"` produces:
   - `output/charts/<slug>.png` rendered from the spec (no API call), and
   - `output/posts/<slug>.image_prompt.md` containing a complete, paste-ready prompt, and
   - `output/state/<slug>.json` recording stage-3 state, and
   - Exit code 10 and a clear "next step" message
2. Running `--resume <slug>` after dropping a PNG at `output/posts/images/<slug>.png`:
   - Deterministic gate validates dimensions (1792×1024 ±5%), format (PNG), size (>50 KB), file exists
   - On pass: Stage 4 runs, validator green, article finalised with both `image:` and chart embed
   - On reject: exit code 11 with a clear message naming the failed check
3. Running `--resume <slug> --no-image`:
   - Strips `image:` from frontmatter
   - Validator accepts (chart-only is publishable)
4. `deploy_to_blog.py` deploys without broken-image regressions in either mode
5. Test suite ≥ 2150 passing; new modules ≥ 80% covered

## 9. Locked Decisions

| Open Q | Decision |
|---|---|
| Multimodal validation in pipeline? | No. Pipeline runs deterministic checks only (dims/format/size/exists). Visual-quality grade is human-orchestrated (operator reads the file via Read tool when in the loop). |
| Handoff message verbosity? | Verbose. Full prompt embedded inline + exact drop-path + next command, so the human can copy-paste without context-switching back to chat. |
| Resume timeout? | None. `--resume <slug>` is open-ended. State lives on disk; multiple pipelines can coexist identified by slug. |

## 10. Notes

- DALL-E auto path (`featured_image_agent.py`) stays in the repo as an opt-in for any user with `OPENAI_API_KEY`. Out of scope for this spec to remove it; in scope to NOT call it by default.
- Slug derivation reuses whatever `deploy_to_blog.py` uses today (`article_path.stem`); to be verified in Task 3.2.
- `logs/spike/pipeline_*` files become telemetry-only — the canonical artefacts live under `output/`.
