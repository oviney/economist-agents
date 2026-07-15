"""Keyless editorial hero image (B-007).

Renders a professional, on-brand "cover" hero for an article with no API key —
a typographic composition in the Economist palette: a red signature tab, a bold
serif headline, a thin rule, an editorial kicker, and a deterministic geometric
motif derived from the title. This is the hero path (see CLAUDE.md Operating
Constraints: no image-generation API is permitted), so a themed hero image is
always present in a generated post.

Deterministic: the motif is seeded from a hash of the title, so the same article
always yields the same hero (reproducible), while different articles differ.
"""

from __future__ import annotations

import hashlib
import logging
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ── Palette (Economist-adjacent) ─────────────────────────────────────────
_BG = (245, 244, 239)  # warm off-white
_INK = (20, 22, 28)  # near-black for the headline
_RED = (227, 18, 11)  # Economist red — the signature tab
_NAVY = (12, 35, 64)
_BURGUNDY = (123, 45, 58)
_MUTED = (110, 112, 118)  # kicker / caption grey

# 1792×1024 — the standard landscape hero size the downstream layout and
# aspect-ratio gates already expect.
_W, _H = 1792, 1024

_SERIF_BOLD_CANDIDATES = (
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
)
_SERIF_CANDIDATES = (
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
)
_SANS_CANDIDATES = (
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def _load_font(candidates: tuple[str, ...], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    logger.warning("No preferred font found; using PIL default")
    return ImageFont.load_default()


def _seed(title: str) -> int:
    return int(hashlib.sha256(title.encode("utf-8")).hexdigest(), 16)


def _draw_motif(draw: ImageDraw.ImageDraw, seed: int) -> None:
    """A restrained geometric motif on the right third — concentric arcs and a
    couple of discs in the palette, arranged deterministically from ``seed``.
    Kept quiet (thin strokes, generous space) so it reads as editorial, not busy.
    """
    cx = int(_W * 0.76)
    cy = int(_H * 0.52)
    palette = [_NAVY, _BURGUNDY, _RED]

    # Concentric arcs — count/sweep vary with the seed.
    n_arcs = 3 + (seed % 3)
    for i in range(n_arcs):
        r = 120 + i * 66
        start = (seed >> (i + 1)) % 360
        extent = 150 + ((seed >> (i + 2)) % 140)
        colour = palette[i % len(palette)]
        draw.arc(
            [cx - r, cy - r, cx + r, cy + r],
            start=start,
            end=start + extent,
            fill=colour,
            width=6,
        )

    # A solid disc + a ring, positioned by the seed, for a focal accent.
    disc_r = 46 + (seed % 30)
    angle = (seed % 360) * math.pi / 180
    dx = int(cx + math.cos(angle) * 150)
    dy = int(cy + math.sin(angle) * 150)
    draw.ellipse(
        [dx - disc_r, dy - disc_r, dx + disc_r, dy + disc_r], fill=_BURGUNDY
    )
    ring_r = 34 + ((seed >> 5) % 26)
    rx = int(cx - math.cos(angle) * 190)
    ry = int(cy - math.sin(angle) * 120)
    draw.ellipse(
        [rx - ring_r, ry - ring_r, rx + ring_r, ry + ring_r],
        outline=_NAVY,
        width=8,
    )


def _wrap_to_width(
    text: str, font: ImageFont.FreeTypeFont, max_width: int
) -> list[str]:
    """Greedy word-wrap so each line fits ``max_width`` pixels."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if font.getlength(trial) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_editorial_hero(
    title: str,
    kicker: str,
    output_path: str | Path,
) -> Path:
    """Render a keyless editorial hero PNG and return its path.

    Args:
        title: Article headline (drawn large, serif, wrapped).
        kicker: A short editorial line (the image caption / dek), drawn small.
        output_path: Destination PNG path (parent dirs created).

    Returns:
        The resolved output path.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (_W, _H), _BG)
    draw = ImageDraw.Draw(img)

    seed = _seed(title)
    _draw_motif(draw, seed)

    margin = 96
    # Red signature tab.
    draw.rectangle([margin, 96, margin + 132, 96 + 26], fill=_RED)

    # Headline — shrink to fit at most 4 lines within the left ~58% of the width.
    text_max_w = int(_W * 0.58) - margin
    for size in (128, 116, 104, 92, 80, 70):
        title_font = _load_font(_SERIF_BOLD_CANDIDATES, size)
        lines = _wrap_to_width(title.strip(), title_font, text_max_w)
        if len(lines) <= 4:
            break
    line_h = int(size * 1.06)
    y = 168
    for line in lines:
        draw.text((margin, y), line, font=title_font, fill=_INK)
        y += line_h

    # Thin rule under the headline.
    y += 24
    draw.line([margin, y, margin + text_max_w, y], fill=_INK, width=3)

    # Kicker / editorial dek beneath the rule.
    y += 28
    kicker_font = _load_font(_SERIF_CANDIDATES, 40)
    for line in _wrap_to_width(kicker.strip(), kicker_font, text_max_w)[:3]:
        draw.text((margin, y), line, font=kicker_font, fill=_MUTED)
        y += 52

    # Small standing-line bottom-left, like a section label.
    label_font = _load_font(_SANS_CANDIDATES, 26)
    draw.text(
        (margin, _H - 80),
        "ECONOMIST-STYLE ILLUSTRATION",
        font=label_font,
        fill=_MUTED,
    )

    img.save(out, "PNG")
    logger.info("Rendered keyless editorial hero: %s", out)
    return out


def generate_hero(
    title: str,
    image_alt: str,
    image_caption: str,
    output_path: str | Path,
) -> Path:
    """Produce a themed hero image for an article — keyless.

    Draws a deterministic editorial cover in Python (no image model, no API key;
    see CLAUDE.md Operating Constraints). Claude cannot generate raster images
    and no image-generation API is permitted, so this is the hero path.

    Args:
        title: Article headline.
        image_alt: The writer's illustration brief (unused for drawing, kept for
            signature stability with the caller).
        image_caption: The editorial dek/caption drawn under the headline.
        output_path: Destination PNG path.

    Returns:
        The path to the rendered hero (always exists on return).
    """
    return render_editorial_hero(title, image_caption or image_alt, output_path)
