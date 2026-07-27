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
    if primitives < _MIN_PRIMITIVES:
        raise HeroSvgError(
            f"hero SVG has only {primitives} drawing primitives; expected at least "
            f"{_MIN_PRIMITIVES} (a near-empty canvas is a failed drawing)"
        )


#: Chrome is the only rasteriser available here — there is no rsvg-convert or
#: cairosvg in this environment, and adding one would be a new dependency for a
#: capability we already have.
_CHROME_BINARIES = ("google-chrome", "chromium", "chromium-browser")
_RENDER_TIMEOUT_S = 60

#: Matches the gate's 16:9 contract and the shipped hero's intrinsic size.
_RENDER_WIDTH = 1600
_RENDER_HEIGHT = 900


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
    binary = next((b for b in _CHROME_BINARIES if shutil.which(b)), None)
    if binary is None:
        logger.warning(
            "No Chrome/Chromium binary found (%s) — skipping hero render, so the "
            "vision critique will be skipped too",
            ", ".join(_CHROME_BINARIES),
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
