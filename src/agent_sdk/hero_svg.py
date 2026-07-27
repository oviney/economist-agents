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

import re
from xml.etree import ElementTree

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
