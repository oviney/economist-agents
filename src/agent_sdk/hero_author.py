"""Claude authors the hero SVG, then critiques its own render (B-016b).

Spec: ``docs/specs/B-016b-automatic-hero-svg.md``.

Two loops, for two different kinds of wrong:

1. **Structural** — :func:`hero_svg.check_hero_svg` is deterministic, so a
   rejection is fed straight back and redrawn. Cheap and reliable.
2. **Compositional** — the gate is blind to it. Every real defect in the first
   hand-authored hero (a drain painted over the coin pile, the floor overlapping
   the drain, dead space, a valve that read as crosshairs) passed all nine
   structural rules and was visible only in a render. So the SVG is rasterised and
   Claude is shown its own drawing against a specific checklist.

Keyless throughout: everything runs through ``claude_agent_sdk.query()`` on the
subscription (Operating Constraints #1–#3). The vision step follows
``_shared.refine_image_metadata``'s precedent — it inspects the PNG with the
``Read`` tool and degrades to "no critique" on any malfunction.

**Malfunction vs verdict.** A vision *malfunction* (no renderer, SDK raises,
non-JSON reply) must never cost us the hero and must never affect the exit code. A
vision *verdict* of "still defective" is reported to the caller, which surfaces it
and exits non-zero. Conflating those two is the mistake the spec's first draft
made.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from src.agent_sdk.hero_svg import HeroSvgError, check_hero_svg, render_to_png
from src.agent_sdk.stage3_runner import _collect_text

logger = logging.getLogger(__name__)

#: Structural rejections are deterministic and cheap to fix — but a draw is NOT
#: cheap (measured: ~454s and $0.45 each), so keep the worst case bounded.
_MAX_STRUCTURAL_ATTEMPTS = 2

#: Measured: the critique does NOT converge. Across three real attempts it found
#: genuine defects every time (dead space, clipped edges), so each redraw cost
#: ~8 minutes and bought nothing. Reduced from the spec's 2 to 1 — one correction
#: is worth trying; a second is just spend. See the spec's failure policy: the
#: critique's real value is the report, not the loop.
_MAX_CRITIQUE_RETRIES = 1

#: Wall-clock ceilings. ``_collect_text`` has no timeout of its own (BUG-059), so
#: without these a stalled SDK call blocks the pipeline forever.
#:
#: These numbers are MEASURED, not guessed. Instrumenting the message stream for
#: one hero draw: 440s of SystemMessage/ThinkingBlock traffic, then a single
#: 3,725-char TextBlock at 454s, cost $0.4534. Drawing a composed scene in SVG is
#: genuinely a large reasoning task. The first three values I picked (max_turns=1,
#: 240s, $0.40) were each independently fatal.
_DRAW_TIMEOUT_S = 600
_CRITIQUE_TIMEOUT_S = 180

#: Thinking consumes turns, so a one-turn cap fails with "Reached maximum number
#: of turns (1)" before any text arrives. Measured working value: 3.
_DRAW_MAX_TURNS = 4

#: Cost ceilings, mirroring how the writer and graphics agents are bounded. Set
#: above the measured $0.4534 with headroom rather than at it.
_DRAW_BUDGET_USD = 0.75
_CRITIQUE_BUDGET_USD = 0.15

_SVG_BLOCK = re.compile(r"<svg\b.*?</svg\s*>", re.DOTALL | re.IGNORECASE)
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

#: A worked example beats a rulebook. Measured: with rules alone the model
#: produces clipart-grade output (crude figure, dead space, clipped edges) that
#: passes every structural rule. This condensed extract of the hero that shipped
#: with the first article demonstrates the techniques that actually matter —
#: full-bleed background, a rotated group, separation strokes on overlapping
#: shapes, and silhouette figures built from few large forms.
_EXEMPLAR = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900">
  <title>A green build drains the engineering budget</title>
  <desc>An engineer presses a green tick while a severed pipeline pours coins into a drain.</desc>
  <rect width="1600" height="900" fill="#f3efe4"/>
  <g transform="rotate(13.6 800 450)">
    <rect x="-200" y="300" width="1400" height="90" fill="#17557f"/>
    <rect x="-200" y="300" width="1400" height="18" fill="#0f3a5f"/>
  </g>
  <polygon points="900,760 1500,760 1560,900 840,900" fill="#111111"/>
  <ellipse cx="1180" cy="762" rx="120" ry="26" fill="#0b2b46"/>
  <ellipse cx="1150" cy="700" rx="34" ry="14" fill="#e3120b" stroke="#f3efe4" stroke-width="3"/>
  <ellipse cx="1205" cy="672" rx="34" ry="14" fill="#c10f09" stroke="#f3efe4" stroke-width="3"/>
  <circle cx="620" cy="560" r="86" fill="#1c8f4a" stroke="#f3efe4" stroke-width="6"/>
  <path d="M580 560 l30 32 l58 -66" stroke="#f3efe4" stroke-width="16" fill="none"/>
  <path d="M300 470 q40 -110 96 -110 q56 0 60 110 z" fill="#111111"/>
  <rect x="318" y="470" width="80" height="210" rx="18" fill="#111111"/>
</svg>"""

HERO_SYSTEM_PROMPT = f"""You draw editorial hero illustrations as hand-authored SVG.

You are not describing an image for another tool to generate — you are writing the
SVG source yourself, shape by shape, in the manner of an Economist graphic.

Hard requirements (a validator rejects the file otherwise):
- One <svg> root with viewBox="0 0 1600 900". No width/height dependence.
- Exactly one <title> and one <desc>, both non-empty. These are accessibility
  metadata and are never painted.
- NO <text>, <tspan>, or <textPath>. No words, letters, numerals, or logos are
  drawn anywhere in the artwork.
- No <image>, no <script>, no on* event attributes, no external references. The
  file must be entirely self-contained geometry.
- Between 20 and 45 drawing primitives. Build the picture from a modest number
  of large, confident shapes rather than many tiny ones.
- Keep the whole file under about 6 KB. A long file is a sign of fussy detail,
  not of quality.

Craft requirements:
- Bold, high-contrast, flat graphic shapes. Not painterly, not photorealistic,
  not gradient-heavy.
- Fill the frame. Large empty regions read as an unfinished drawing.
- Mind paint order: SVG paints in document order, so anything drawn later covers
  what came before. Draw background first, foreground subjects last.
- Give overlapping subjects a thin background-coloured stroke so they read as
  separate objects rather than a merged silhouette.
- Nothing important may be clipped by the canvas edge.

Study this extract from a hero that shipped, and imitate its technique — few
large forms, a full-bleed background, silhouettes rather than cartoon faces,
separation strokes where shapes overlap, and one clear editorial idea:

{_EXEMPLAR}

Do not copy its subject. Draw the requested subject with that same economy.

Output the SVG source and nothing else. No prose, no markdown fences."""

_CRITIQUE_SYSTEM_PROMPT = """You are a ruthless art director reviewing a rendered
illustration. You are looking for concrete composition faults, not taste.

Answer ONLY with JSON: {"ok": true|false, "defects": ["...", "..."]}

Report a defect only for these, and quote what you actually see:
- A subject is hidden or clipped by a shape painted over it.
- A large region of the canvas is empty (roughly a quarter or more).
- Two subjects overlap so ambiguously that you cannot tell them apart.
- Something important is cut off by the canvas edge.
- The drawing is unreadable as the subject it claims to depict.

Do not report: colour preferences, style opinions, missing text or labels (text is
forbidden by design), or suggestions for improvement. If none of the listed faults
are present, return {"ok": true, "defects": []}."""


@dataclass(frozen=True)
class HeroResult:
    """Outcome of authoring a hero.

    Attributes:
        path: The written SVG, or ``None`` when no structurally valid hero was
            produced.
        critique: Unresolved composition defects. Empty means "nothing to report",
            which includes the case where the critique could not run at all.
        error: Why no hero exists. Empty when ``path`` is set.
        cost_usd: Total subscription cost of the attempts.
    """

    path: Path | None
    critique: str = ""
    error: str = ""
    cost_usd: float = 0.0


def _extract_svg(text: str) -> str:
    """Pull the SVG document out of a reply that may be wrapped in prose/fences."""
    match = _SVG_BLOCK.search(text or "")
    return match.group(0).strip() if match else (text or "").strip()


def _parse_verdict(text: str) -> list[str]:
    """Return reported defects. An unparseable reply means "no critique"."""
    match = _JSON_BLOCK.search(text or "")
    if not match:
        logger.warning("Hero critique reply was not JSON — treating as no critique")
        return []
    try:
        verdict = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("Hero critique JSON did not parse — treating as no critique")
        return []
    if not isinstance(verdict, dict) or verdict.get("ok") is True:
        return []
    defects = verdict.get("defects") or []
    if not isinstance(defects, list):
        return []
    return [str(d).strip() for d in defects if str(d).strip()]


async def _draw(prompt: str, model: str) -> tuple[str, float]:
    """One bounded drawing call. Raises on timeout so the caller can retry."""
    return await asyncio.wait_for(
        _collect_text(
            prompt,
            HERO_SYSTEM_PROMPT,
            model=model,
            max_turns=_DRAW_MAX_TURNS,
            max_budget_usd=_DRAW_BUDGET_USD,
        ),
        timeout=_DRAW_TIMEOUT_S,
    )


async def _author(brief: str, slug: str, images_dir: Path, model: str) -> HeroResult:
    svg_path = images_dir / f"{slug}-hero.svg"
    png_path = images_dir / f"{slug}-hero.preview.png"
    cost = 0.0
    carry_forward = ""

    for redraw in range(_MAX_CRITIQUE_RETRIES + 1):
        # ── structural loop ────────────────────────────────────────────
        svg = ""
        last_error = ""
        for attempt in range(_MAX_STRUCTURAL_ATTEMPTS):
            prompt = f"Draw the hero illustration.\n\n{brief}"
            if carry_forward:
                prompt += (
                    "\n\nA previous attempt was rejected for these composition "
                    f"faults — fix them specifically:\n{carry_forward}"
                )
            if last_error:
                prompt += (
                    f"\n\nYour previous SVG failed validation: {last_error}\n"
                    "Return corrected SVG source only."
                )
            try:
                text, call_cost = await _draw(prompt, model)
            except TimeoutError:
                # Retryable: a stalled generation is not a reason to give up, but
                # it must not hang. Shrink the ask on the way round.
                last_error = (
                    f"generation exceeded {_DRAW_TIMEOUT_S}s — return a simpler "
                    "drawing with fewer, larger shapes"
                )
                logger.warning(
                    "Hero attempt %s/%s timed out after %ss",
                    attempt + 1,
                    _MAX_STRUCTURAL_ATTEMPTS,
                    _DRAW_TIMEOUT_S,
                )
                continue
            except Exception as exc:  # noqa: BLE001 - degrade, never crash Stage 3
                logger.warning("Hero authoring call failed: %s", exc)
                return HeroResult(path=None, error=str(exc), cost_usd=cost)
            cost += call_cost

            candidate = _extract_svg(text)
            try:
                check_hero_svg(candidate)
            except HeroSvgError as exc:
                last_error = str(exc)
                logger.info(
                    "Hero attempt %s/%s rejected: %s",
                    attempt + 1,
                    _MAX_STRUCTURAL_ATTEMPTS,
                    last_error,
                )
                continue
            svg = candidate
            break

        if not svg:
            return HeroResult(path=None, error=last_error, cost_usd=cost)

        images_dir.mkdir(parents=True, exist_ok=True)
        svg_path.write_text(svg)

        # ── compositional loop ─────────────────────────────────────────
        defects = await _critique(svg_path, png_path, model)
        if not defects:
            return HeroResult(path=svg_path, cost_usd=cost)

        carry_forward = "\n".join(f"- {d}" for d in defects)
        # `redraw` is 0-based and the last pass has no redraw left, so report
        # what will actually happen rather than a bare counter ("redraw 2/1"
        # was the confusing output this replaces).
        remaining = _MAX_CRITIQUE_RETRIES - redraw
        outcome = (
            f"redrawing ({remaining} attempt(s) left)"
            if remaining > 0
            else "no redraws left — reporting"
        )
        logger.warning("Hero composition defects, %s:\n%s", outcome, carry_forward)

    # Retries exhausted. Keep the hero — it is structurally valid and on disk —
    # and hand the critique back so the CLI can exit non-zero. Shipping silently
    # would rely on a warning nobody reads; discarding it would report the wrong
    # fault ("hero image not set") for a composition problem.
    return HeroResult(path=svg_path, critique=carry_forward, cost_usd=cost)


async def _critique(svg_path: Path, png_path: Path, model: str) -> list[str]:
    """Show Claude its own render. Any malfunction means "no critique"."""
    rendered = render_to_png(svg_path, png_path)
    if rendered is None:
        return []
    try:
        text, _ = await asyncio.wait_for(
            _collect_text(
                "Use the Read tool to look at this rendered illustration and report "
                f"composition faults: {rendered}",
                _CRITIQUE_SYSTEM_PROMPT,
                model=model,
                allowed_tools=["Read"],
                max_turns=3,
                max_budget_usd=_CRITIQUE_BUDGET_USD,
            ),
            timeout=_CRITIQUE_TIMEOUT_S,
        )
    except Exception as exc:  # noqa: BLE001 - a malfunction must not cost the hero
        logger.warning("Hero critique failed (%s) — proceeding without it", exc)
        return []
    return _parse_verdict(text)


def author_hero_svg(
    *,
    brief: str,
    slug: str,
    images_dir: Path,
    model: str | None = None,
) -> HeroResult:
    """Author ``<slug>-hero.svg`` in ``images_dir`` and critique its render.

    Never raises. Stage 3 must not fail because of a hero, so every failure is
    reported in the returned :class:`HeroResult` and the CLI decides the exit code.
    """
    from src.agent_sdk.stage3_runner import DEFAULT_GRAPHICS_MODEL

    try:
        return asyncio.run(
            _author(brief, slug, images_dir, model or DEFAULT_GRAPHICS_MODEL)
        )
    except Exception as exc:  # noqa: BLE001 - last-resort guard
        logger.warning("Hero authoring aborted: %s", exc)
        return HeroResult(path=None, error=str(exc))
