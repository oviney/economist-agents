"""Deterministic structural gate for a Claude-authored hero SVG (B-016b).

Spec: ``docs/specs/B-016b-automatic-hero-svg.md``.

This module checks only what a computer can check reliably and quickly. It
deliberately does **not** judge composition — every real defect in the first
hand-authored hero (a drain painted over the coin pile, the floor overlapping the
drain, dead space, a valve that read as crosshairs) passes every rule here and was
only visible in a render. Composition is the vision critique's job.

Thresholds are measured from the hero that shipped with the first article, not
invented: 5.7 KB, 66 primitives, one ``<title>``, one ``<desc>``, zero ``<text>``,
no external reference.

Shaped after :mod:`chart_renderer` — one error type, one actionable message
naming the specific failure.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

logger = logging.getLogger(__name__)

#: Where Claude's hand-drawn heroes land (Operating Constraint #4). Defined here,
#: the lowest-level hero module, so stage3_runner and pipeline share one
#: definition without importing each other.
HERO_IMAGES_DIR = Path("output/posts/images")

#: The blog's hero slot is 16:9, and so is the shipped hero (1600x900).
_TARGET_RATIO = 16 / 9
_RATIO_TOLERANCE = 0.02

#: Guards near-blank output. The shipped hero has 66; 12 is a floor, not a target.
_MIN_PRIMITIVES = 12

#: Guards a pathological path-data dump. The shipped hero is 5.7 KB.
_MAX_BYTES = 100_000

#: Words that mean the ``<desc>`` is a drawing *brief* rather than a description
#: of what was drawn. Mirrored term-for-term from ``PROMPT_ALT_PATTERN`` in
#: ``oviney/blog``'s ``scripts/validate-post-quality.sh`` — that gate is the
#: authority, and any term it rejects must be rejected here too.
#:
#: This matters because ``pipeline._hero_description`` harvests ``<desc>`` into
#: the published ``image_alt``. A brief that survives this gate is laundered
#: through the SVG into the blog's front matter and reddens ``main`` (five
#: occurrences: oviney/blog#1289). Failing here costs one redraw; failing there
#: costs a blocked publication queue.
_PROMPT_LANGUAGE = re.compile(
    r"editorial illustration|editorial photomontage|photorealistic"
    r"|technical diagram|infographic|blueprint|cartoon|risograph|duotone"
    r"|monochrome|palette|lighting|texture|crosshatching|newspaper engraving"
    r"|block-print|rendered|style",
    re.IGNORECASE,
)

#: Elements that paint words. `title`/`desc` are accessibility metadata and are
#: never rendered, so they are required rather than banned.
_TEXT_ELEMENTS = frozenset({"text", "tspan", "textPath"})

#: Anything that draws. Counted to detect an empty canvas.
_PRIMITIVES = frozenset(
    {
        "rect",
        "circle",
        "ellipse",
        "line",
        "polyline",
        "polygon",
        "path",
        "g",
        "use",
    }
)

_EVENT_HANDLER = re.compile(r"^on[a-z]+$", re.IGNORECASE)
_EXTERNAL_REF = re.compile(r"^\s*(?:https?:)?//|^\s*(?:file|data):", re.IGNORECASE)


class HeroSvgError(ValueError):
    """Hero SVG failed the deterministic structural gate."""


def _localname(tag: str) -> str:
    """``{http://...}rect`` -> ``rect``."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _parse_viewbox(value: str) -> tuple[float, float]:
    parts = re.split(r"[\s,]+", value.strip())
    if len(parts) != 4:
        raise HeroSvgError(f"viewBox must have 4 numbers, got {value!r}")
    try:
        _, _, width, height = (float(p) for p in parts)
    except ValueError:
        raise HeroSvgError(f"viewBox must be numeric, got {value!r}") from None
    if width <= 0 or height <= 0:
        raise HeroSvgError(f"viewBox width and height must be positive, got {value!r}")
    return width, height


def check_hero_svg(source: str) -> None:
    """Validate a hero SVG, raising :class:`HeroSvgError` on the first failure.

    Args:
        source: The complete SVG document as text.

    Raises:
        HeroSvgError: With a message naming the specific rule that failed.
    """
    if len(source.encode("utf-8")) > _MAX_BYTES:
        raise HeroSvgError(
            f"hero SVG is {len(source.encode('utf-8'))} bytes; ceiling is "
            f"{_MAX_BYTES} (the shipped reference hero is ~5,700)"
        )

    try:
        root = ElementTree.fromstring(source)
    except ElementTree.ParseError as exc:
        raise HeroSvgError(f"hero SVG is not well-formed XML: {exc}") from exc

    if _localname(root.tag) != "svg":
        raise HeroSvgError(f"root element must be <svg>, got <{_localname(root.tag)}>")

    viewbox = root.get("viewBox")
    if not viewbox:
        raise HeroSvgError("hero SVG must set viewBox so it scales on the blog")
    width, height = _parse_viewbox(viewbox)

    ratio = width / height
    if abs(ratio - _TARGET_RATIO) / _TARGET_RATIO > _RATIO_TOLERANCE:
        raise HeroSvgError(
            f"hero aspect ratio is {ratio:.3f} ({viewbox}); must be 16:9 "
            f"({_TARGET_RATIO:.3f}) within {_RATIO_TOLERANCE:.0%}"
        )

    titles: list[str] = []
    descs: list[str] = []
    primitives = 0
    for element in root.iter():
        name = _localname(element.tag)

        if name == "title":
            titles.append((element.text or "").strip())
            continue
        if name == "desc":
            descs.append((element.text or "").strip())
            continue
        if name == "script":
            raise HeroSvgError("hero SVG must not contain <script>")
        if name == "image":
            # The only element that pulls in raster content. Banned outright
            # rather than URL-filtered, which would miss a relative path.
            raise HeroSvgError(
                "hero SVG must not contain <image>; the drawing must be "
                "self-contained geometry (Operating Constraint #4)"
            )
        if name in _TEXT_ELEMENTS:
            raise HeroSvgError(
                f"hero SVG must not render text (found <{name}>); words belong in "
                "the caption, not the artwork"
            )
        if name in _PRIMITIVES:
            primitives += 1

        for attr, value in element.attrib.items():
            attr_local = _localname(attr)
            if _EVENT_HANDLER.match(attr_local):
                raise HeroSvgError(
                    f"hero SVG must not contain event handlers (found {attr_local!r})"
                )
            if attr_local in ("href", "src") and _EXTERNAL_REF.match(value):
                raise HeroSvgError(
                    f"hero SVG must be self-contained; found an external "
                    f"reference {value!r}"
                )

    if len(titles) != 1 or not titles[0]:
        raise HeroSvgError(
            f"hero SVG must have exactly one non-empty <title> (found {len(titles)})"
        )
    if len(descs) != 1 or not descs[0]:
        raise HeroSvgError(
            f"hero SVG must have exactly one non-empty <desc> (found {len(descs)})"
        )

    brief = _PROMPT_LANGUAGE.search(descs[0])
    if brief:
        raise HeroSvgError(
            f"hero <desc> reads as a drawing prompt, not alt text (found "
            f"{brief.group(0)!r}); it is published verbatim as image_alt, so "
            f"describe what the drawing shows — a screen-reader user needs the "
            f"subject, not the medium or the art direction"
        )
    if primitives < _MIN_PRIMITIVES:
        raise HeroSvgError(
            f"hero SVG has only {primitives} drawing primitives; expected at least "
            f"{_MIN_PRIMITIVES} (a near-empty canvas is a failed drawing)"
        )


#: Chrome is the only rasteriser available here — there is no rsvg-convert or
#: cairosvg in this environment, and adding one would be a new dependency for a
#: capability we already have.
_CHROME_BINARIES = ("google-chrome", "chromium", "chromium-browser")

#: macOS ships Chrome as an app bundle, so it is never on ``PATH`` under any of
#: the names above and ``shutil.which()`` alone can never find it (BUG-068). The
#: failure was silent — no raster, therefore no vision critique, therefore
#: Constraint #4 unenforceable on the platform the owner runs.
_CHROME_APP_PATHS = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
)
_RENDER_TIMEOUT_S = 60

#: Matches the gate's 16:9 contract and the shipped hero's intrinsic size.
_RENDER_WIDTH = 1600
_RENDER_HEIGHT = 900


#: Below this share of an edge, a run is anti-aliasing or a deliberate accent
#: touching the frame, not a shape running out of it.
_EDGE_MIN_COVERAGE = 0.02
#: Per-channel tolerance, so anti-aliased boundaries do not read as new colours.
_EDGE_COLOUR_TOLERANCE = 16


def report_edge_contact(png_path: Path) -> list[str]:
    """Measure where rendered content meets the frame edge.

    This is a **measurement, not a verdict**, and the distinction is the whole
    point. B-027 exists because a hero was reported clipped on the strength of a
    glance at a thumbnail, and a border-pixel check proved it was not. Constraint
    #4 says look at the rendered result; this supplies numbers so that looking does
    not have to mean guessing.

    Taken on the raster, not the SVG — a true SVG bounding box needs transform
    composition and path-data parsing, which is both hard and prone to false
    failures on valid geometry.

    Full-bleed content is excluded structurally rather than by threshold: a border
    pixel counts only when the perpendicular line through it is *not* uniform. A
    band spanning the full width is deliberate, and a coverage threshold alone
    cannot recognise that, because such a band necessarily puts a partial run on
    both vertical edges.

    **Known limitation, deliberately not "fixed".** A shape that intentionally
    bleeds off one side — a desk, a wall, a table edge, all common and correct —
    is geometrically identical to a shape accidentally clipped. The shipped hero
    has exactly that: a desk rect from x=0 that stops at x=680. Telling those apart
    requires intent, which pixels do not carry. So this reports *what is true*
    (content meets this edge, by this much) and leaves the judgement to a human.
    Do not add heuristics to suppress the "false positives"; they are not false,
    they are unadjudicated.

    Returns a list of human-readable measurements, empty when nothing meets an edge
    without crossing. Never raises: this informs the reviewer and must not be the
    reason a run fails (B-016b failure policy, row 2).
    """
    try:
        from PIL import Image

        with Image.open(png_path) as handle:
            image = handle.convert("RGB")
            width, height = image.size
            pixels = image.load()
    except Exception as exc:  # noqa: BLE001 — a reporter must never break a run
        logger.debug("edge-contact check skipped for %s (%s)", png_path, exc)
        return []

    if width < 2 or height < 2:
        return []

    def _close(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
        return all(
            abs(c - d) <= _EDGE_COLOUR_TOLERANCE for c, d in zip(a, b, strict=True)
        )

    row_spans: dict[int, bool] = {}
    col_spans: dict[int, bool] = {}

    def _row_crosses(y: int) -> bool:
        """True when row ``y`` is one colour all the way across — a full-bleed band."""
        if y not in row_spans:
            first = pixels[0, y]
            row_spans[y] = all(_close(pixels[x, y], first) for x in range(width))
        return row_spans[y]

    def _col_crosses(x: int) -> bool:
        """True when column ``x`` is one colour top to bottom."""
        if x not in col_spans:
            first = pixels[x, 0]
            col_spans[x] = all(_close(pixels[x, y], first) for y in range(height))
        return col_spans[x]

    edges: dict[str, tuple[list[tuple[int, int, int]], object]] = {
        "top": ([pixels[x, 0] for x in range(width)], _col_crosses),
        "bottom": ([pixels[x, height - 1] for x in range(width)], _col_crosses),
        "left": ([pixels[0, y] for y in range(height)], _row_crosses),
        "right": ([pixels[width - 1, y] for y in range(height)], _row_crosses),
    }

    findings: list[str] = []
    for name, (line, crosses) in edges.items():
        dominant = Counter(line).most_common(1)[0][0]
        clipped = sum(
            1
            for index, colour in enumerate(line)
            if not _close(colour, dominant) and not crosses(index)  # type: ignore[operator]
        )
        coverage = clipped / len(line)
        if coverage >= _EDGE_MIN_COVERAGE:
            findings.append(
                f"Content meets the {name} edge across {coverage:.0%} of it without "
                "crossing the frame. Deliberate bleed-off and accidental clipping "
                "look identical here — look at the render before judging."
            )
    return findings


def _find_chrome() -> str | None:
    """Locate a Chrome/Chromium executable, or ``None`` if none is installed.

    ``PATH`` is searched first: a binary the operator put there is a deliberate
    choice and should outrank a system-default app bundle. Bundle paths are the
    fallback that makes macOS work at all (BUG-068).
    """
    for name in _CHROME_BINARIES:
        found = shutil.which(name)
        if found:
            return found
    return next((str(p) for p in _CHROME_APP_PATHS if p.exists()), None)


def render_to_png(svg_path: Path, png_path: Path) -> Path | None:
    """Rasterise ``svg_path`` so the composition can be *looked at*.

    The structural gate cannot see composition, and Operating Constraint #4
    requires looking at the rendered result before shipping — so something has to
    produce a raster. This is that step; the vision critique and the operator both
    read its output.

    Returns ``None`` on every failure rather than raising. Rendering exists to
    *enable* a quality check, so its absence must degrade to "no critique
    available", never to a failed article (spec failure policy, row 2: a vision
    malfunction must not affect the exit code).
    """
    binary = _find_chrome()
    if binary is None:
        logger.warning(
            "No Chrome/Chromium binary found (searched PATH for %s, and %s) — "
            "skipping hero render, so the vision critique will be skipped too and "
            "NOBODY WILL HAVE LOOKED AT THE HERO (Constraint #4)",
            ", ".join(_CHROME_BINARIES),
            ", ".join(str(p) for p in _CHROME_APP_PATHS),
        )
        return None

    png_path.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        binary,
        "--headless",
        "--disable-gpu",
        # No profile, no network, no extensions: this renders a local file and
        # must not become a browsing session.
        "--no-sandbox",
        "--hide-scrollbars",
        f"--screenshot={png_path}",
        f"--window-size={_RENDER_WIDTH},{_RENDER_HEIGHT}",
        f"file://{svg_path.resolve()}",
    ]

    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell, local file
            argv,
            capture_output=True,
            text=True,
            timeout=_RENDER_TIMEOUT_S,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("Hero render failed (%s) — skipping vision critique", exc)
        return None

    if result.returncode != 0:
        logger.warning(
            "Hero render exited %s — skipping vision critique. stderr: %s",
            result.returncode,
            (result.stderr or "").strip()[:400],
        )
        return None
    if not png_path.is_file():
        # Chrome can exit 0 having written nothing; without this the vision step
        # would be handed a path that does not exist.
        logger.warning(
            "Hero render exited 0 but wrote no file at %s — skipping vision critique",
            png_path,
        )
        return None
    return png_path
