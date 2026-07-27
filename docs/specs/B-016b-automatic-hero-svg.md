# Spec: B-016b — Stage 3 draws the hero SVG automatically

**Status:** Draft — failure policy decided 2026-07-27; awaiting owner LGTM to build
**Backlog:** B-016b (blocker)
**Depends on:** B-016a (mechanism), B-019 (`_link_hero_asset`, front-matter contract)
**Blocks:** every future article

## Objective

Stage 3 must produce `output/posts/images/<slug>-hero.svg` so that every generated
article has a **resolvable `image:`**. This is not a polish item: B-019 measured the
blog's gate and both validators require `image:` to be set and to resolve
(`validate-post-quality.sh` check 1 errors with `hero image not set`). Today the
hero is hand-authored by Claude in-session, so **the pipeline cannot produce a
publishable article without a human illustrator in the loop.**

Success is one sentence: `python -m src.agent_sdk.pipeline "<topic>"` yields an
article that `scripts/acceptance_blog_frontmatter.sh` passes with **0 errors**,
with no hand-drawn asset and no manual front-matter editing.

Out of scope: **multiple figures per post.** The owner's original B-016 ask
included "any charts or images the post requires", and today the pipeline draws
exactly one chart plus (after this) one hero. Multi-figure needs its own spec —
it changes the article's body structure, not just its assets.

## Assumptions (correct these before I build)

1. **SVG, hand-authored geometry, no raster model.** Constraint #4. Claude writes
   the SVG source; nothing rasterises art.
2. **One hero per article, landscape, no words in the image.** Matching the
   flaky-tests hero that shipped.
3. **A regenerated hero replaces the previous attempt** rather than versioning.
   The article is unpublished at this point; keeping rejected drafts adds clutter.
4. **Vision self-critique is worth ~2–3 extra subscription calls per article.**
   Cheap relative to Stage 3's writer, and the alternative is a human step.

## What already exists (do not rebuild)

| Piece | Where | State |
|---|---|---|
| The brief Claude draws from | `image_prompt_synth.compose_prompt` | Ships; **constraints are stale — see below** |
| Hero path convention | `output/posts/images/<slug>-hero.svg` | Ships (B-016a) |
| Front-matter linking | `pipeline._link_hero_asset` | Ships (B-019), prefers `.svg` |
| Deploy copy + `.webp` sibling | `deploy_to_blog._copy_hero_asset` | Ships (B-016a) |
| **Keyless Claude vision on an image** | `_shared.refine_image_metadata` | Ships — `query()` + `Read` tool, graceful fallback. **This is the precedent for the critique loop** |
| SVG → PNG render | `/usr/bin/google-chrome --headless --screenshot` | Available; no rsvg-convert/cairosvg in this env |
| Deterministic asset gate precedent | `chart_renderer.ChartRenderError` | Ships — fail loud with one actionable message |

### Two stale things this spec must fix

- **`_HARD_CONSTRAINTS` is DALL-E-era.** It says `Aspect ratio: 1792x1024` and is
  written for a raster prompt. The hero that actually shipped is **1600×900 SVG**.
  The brief must describe an SVG drawing task.
- **`image_gate.py` is PNG-only** — PNG magic bytes, 1792×1024 ±5%, ≥50 KB. None
  of those apply to an SVG hero. It is dead code on the keyless path; this spec
  adds an SVG gate rather than contorting the PNG one.

### The quality bar, measured

The hand-authored flaky-tests hero: **5.7 KB**, 66 primitives (20 `rect`,
16 `polygon`, 13 `ellipse`, 7 `g`, 7 `circle`, 2 `path`), exactly one `<title>` and
one `<desc>`, **zero `<text>`**, no external `href`. That composition is the target,
and those numbers are checkable.

## The central decision: visual QA with no human in the loop

Every defect in the flaky-tests hero — the enlarged drain painting over the coin
pile, the floor overlapping the drain, dead space, a valve that read as crosshairs
— was **invisible in the SVG source and obvious in a screenshot**. It took five
iterations. An automated hero inherits that failure mode.

### Rejected: (A) structural gate only

Well-formed XML, `viewBox`, `<title>`/`<desc>`, no `<text>`, no external `href`,
size ceiling — then ship. Fully hands-off.

**Why not:** a structural gate cannot see composition. Every one of the five
real defects passes it. The output is a permanent, public, outward-facing image;
"occasionally ugly" is a bad trade for zero iterations of effort. This risk is
measured, not hypothetical.

### Rejected: (B) mandatory render-and-look pause

Pipeline renders the SVG, stops, operator views it, approves or regenerates.

**Why not:** it is the safest option and I would accept it if asked, but it adds a
**second** human gate for a purpose the **first** one already serves. `make publish`
is already owner-invoked and the review-draft flow already exists (B-013). Adding a
mid-pipeline pause means the operator looks at the hero twice and the pipeline stops
being runnable unattended.

### Recommended: (C) structural gate + render + Claude-vision self-critique

1. Claude authors the SVG from the (fixed) brief.
2. **Structural gate** — deterministic, fails loud like `ChartRenderError`.
3. **Render** to PNG via headless Chrome.
4. **Claude looks at its own render** through the existing `refine_image_metadata`
   pattern, and answers a *specific* checklist rather than "is this good": is any
   subject occluded by a later-painted shape; is there a large empty region; do any
   two subjects overlap ambiguously; is the focal subject off-canvas or clipped.
5. On a reported defect, regenerate with the critique appended — **max 2 retries**.
6. If the critique is still unresolved after retries, **write and link the hero,
   then exit non-zero with the critique printed** (see Failure policy below).
7. The **existing** publish approval stays the human backstop.

**Why this one:** constraint #4 already says *"Always look at the rendered result
before shipping."* That is a standing rule, so the question is only *who looks*.
Option C automates the looking Claude can reliably do (gross composition errors)
and leaves the human looking it already does at publish. It needs no new
mechanism — `refine_image_metadata` proves the keyless vision path works and how
to degrade gracefully.

**Honest limits, stated rather than buried:**
- Claude critiquing its own output is weaker than a fresh reviewer. It will catch
  z-order and dead space; it will not reliably catch *taste*.
- A vision **malfunction** must never block the pipeline; a vision **verdict**
  may. These are different things and an earlier draft of this spec conflated
  them — see Failure policy.

## Failure policy

Three distinct outcomes, deliberately not collapsed into one rule:

| Outcome | Behaviour | Exit |
|---|---|---|
| **Structural gate fails** | Hero not written. Log the specific rule. `image:` stays absent | non-zero |
| **Vision malfunctions** — SDK raises, no text, non-JSON, Chrome missing, image >4 MB | **Degrade**: keep the structurally-valid hero, link it, log a warning. Follow `refine_image_metadata`'s precedent exactly | **zero** |
| **Vision reports an unresolved defect** after 2 retries | **Write and link the hero**, print the critique to stderr | non-zero |

The third row is the resolved open question, and it is deliberately the same
shape as the convention already in `pipeline._run_end_to_end`:

```python
if result.publication_validator_passed:
    sys.exit(0)
print("❌ Publication validator found issues:", file=sys.stderr)
for issue in result.publication_validator_issues:
    print(f"  [{issue['severity']}] {issue['check']}: {issue['message']}", ...)
sys.exit(1)
```

Artifacts on disk, issues enumerated, non-zero exit, operator decides. An
unresolved hero critique is the same class of problem, so it gets the same
treatment rather than a new one.

Why not the two alternatives considered:

- **Ship with a loud warning.** A warning is only as good as its reader. It
  scrolls past in pipeline output, and what it guards is a permanent public
  image. "Loud" is not a mechanism.
- **Leave `image:` absent so the blog gate stops it.** The operator would then
  see the blog report **"hero image not set"** — a *false* diagnosis. The hero
  exists; Claude thinks it looks wrong. That message sends you to the wrong
  place. Diagnostics must name the real fault.

Non-zero on a cosmetic issue blocks the *unattended* path, which is the right
default for something permanent, public, and unredirectable. The operator can
always look and publish anyway — the hero and article are both on disk.

## Design

### New module: `src/agent_sdk/hero_svg.py`

Mirrors `chart_renderer.py`'s shape — one gate, one error type, one entry point.

```python
class HeroSvgError(ValueError):
    """Hero SVG failed the deterministic structural gate."""


def check_hero_svg(source: str) -> None:
    """Raise HeroSvgError with one actionable message, or return None."""


def render_to_png(svg_path: Path, png_path: Path) -> Path:
    """Rasterise via headless Chrome so Claude (and the operator) can look."""
```

Structural gate, every rule checkable and derived from the measured bar:

| Rule | Threshold | Why |
|---|---|---|
| Parses as XML | `ElementTree` | A truncated SVG renders blank |
| Root is `<svg>` with `viewBox` | present | Without it the image does not scale |
| Aspect ratio | 16:9 ±2% | Matches the shipped hero and the blog's hero slot |
| `<title>` and `<desc>` | exactly one each | Accessibility; the shipped hero has both |
| No `<text>`/`<tspan>` | zero | Constraint: no words in the image |
| No external reference | no `href`/`xlink:href`, no `<image>` | Must be self-contained; an external fetch is also a privacy leak |
| No script/event handlers | no `<script>`, no `on*` attributes | It is markup the blog serves to readers |
| Primitive count | ≥ 12 | Guards the blank/near-empty output; the shipped hero has 66 |
| File size | ≤ 100 KB | Guards a pathological path-data dump |

### Stage 3 integration

One new step in `stage3_runner`, beside the chart render and the prompt sidecar,
so all three assets derive from the **same canonical slug** (B-008):

```
chart → render_chart(...)          # exists
brief → compose_prompt(...)        # exists, constraints fixed
hero  → author SVG → check_hero_svg → render_to_png → critique loop
```

Stage 3 itself never raises for a hero problem — it returns the hero path (or
none) plus any unresolved critique, and the **CLI** decides the exit code, exactly
as it already does for publication-validator issues. That keeps `run_pipeline`
usable as a library and the exit-code policy in one place. Full behaviour in
Failure policy above.

## Testing strategy

`pytest`, mocking the SDK (CLAUDE.md: "Mock APIs in tests"). No test may make a
network call or invoke Chrome — BUG-058 is the cautionary case.

| Level | What |
|---|---|
| Unit | `check_hero_svg` — one test per gate rule, both directions. Fixtures are literal SVG strings, including a real reduction of the shipped hero as the known-good case |
| Unit | `render_to_png` — Chrome invocation is mocked; assert argv shape and that a missing binary degrades rather than raises |
| Unit | Critique loop — mocked SDK returns "defect found" then "clean"; assert it retries once, caps at 2, and returns the best attempt on persistent failure |
| Unit | Vision **malfunction** degrades — SDK raises / returns non-JSON / Chrome missing → hero kept and linked, warning logged, no exception escapes, exit code unaffected |
| Unit | Vision **verdict** fails the run — unresolved critique after 2 retries → hero still written and linked, critique on stderr, CLI exits non-zero |
| Integration | Stage 3 with a stubbed author step yields a hero at the canonical slug path, and `_link_hero_asset` picks it up |
| Acceptance | `scripts/acceptance_blog_frontmatter.sh` — **0 errors** on a pipeline-generated article with no hand-drawn asset |
| Manual, required once | Generate a real hero and **look at the PNG** before declaring done (constraint #4) |

## Commands

```bash
make ci-local                                    # the merge gate (~9.5 min)
.venv/bin/python -m pytest tests/test_hero_svg.py -q
scripts/acceptance_blog_frontmatter.sh <blog-clone>
google-chrome --headless --screenshot=out.png --window-size=1600,900 file://<svg>
```

## Boundaries

- **Always:** derive the hero path from `canonical_slug`; look at the render before
  shipping; degrade gracefully on vision failure.
- **Ask first:** raising the retry cap above 2; making a vision *malfunction*
  affect the exit code (it must not — only a verdict may); touching
  `image_gate.py` (it is on the resume/handshake path).
- **Never:** a raster image model, a new API key, or a paid service (constraints
  #1–#3); `<text>` in the hero; an external `href` in shipped markup; a test that
  reaches the network or spawns Chrome.

## Success criteria

1. A generated article passes `acceptance_blog_frontmatter.sh` with **0 errors**,
   no hand-drawn asset, no manual editing.
2. `check_hero_svg` rejects each of the nine rule violations with a message naming
   the specific failure.
3. The critique loop provably retries on a reported defect and caps at 2.
4. The three failure outcomes are distinguishable and tested: a vision
   **malfunction** never raises and never changes the exit code; a vision
   **verdict** of unresolved-defect writes and links the hero *and* exits
   non-zero with the critique on stderr; a structural failure writes no hero.
5. `make ci-local` green; coverage does not drop.
6. I have looked at a real generated hero PNG and reported what I saw.

## Open questions

**None.** The failure-policy question is resolved above (2026-07-27, owner
decision): write and link the hero, exit non-zero with the critique, matching the
existing publication-validator convention.
