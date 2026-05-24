"""Deterministic image-quality gate for the --resume handshake (#403 slice 4).

The visual-quality grade (mood matches the article, no awkward composition,
etc.) is *not* attempted here — that is human-orchestrated, done by the
operator reading the file via the Read tool before deploy. This module
only enforces the things a computer can check reliably and quickly:

- The file exists.
- It is a real PNG (magic bytes match).
- It is at least ``MIN_BYTES`` (50 KB) — guards against accidental
  saves of empty/cropped/placeholder files.
- It is approximately the expected aspect ratio (1792×1024 ±5% per
  dimension) — matches the prompt's hard constraint.

When any check fails, ``check_hero_image`` raises ``ImageGateError`` with
a single human-readable message naming the specific failure. Callers
(pipeline.py --resume) translate to exit code 11.
"""

from __future__ import annotations

import struct
from pathlib import Path

EXPECTED_WIDTH = 1792
EXPECTED_HEIGHT = 1024
DIM_TOLERANCE_PCT = 5
MIN_BYTES = 50 * 1024  # 50 KB
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class ImageGateError(ValueError):
    """Hero image failed one of the deterministic gate checks."""


def _read_png_dimensions(path: Path) -> tuple[int, int]:
    """Return (width, height) from a PNG IHDR chunk.

    PNG byte layout (per RFC 2083):
      bytes 0-7   = signature
      bytes 8-15  = IHDR chunk length + type
      bytes 16-23 = width (big-endian uint32), height (big-endian uint32)

    Raises ImageGateError if the file is too short to contain the IHDR
    or the magic bytes don't match.
    """
    try:
        with path.open("rb") as f:
            header = f.read(24)
    except OSError as exc:
        raise ImageGateError(f"could not open {path}: {exc}") from exc
    if len(header) < 24 or header[:8] != PNG_MAGIC:
        raise ImageGateError(f"{path} is not a valid PNG (magic bytes mismatch)")
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def _within_tolerance(actual: int, expected: int, pct: int) -> bool:
    """True when ``actual`` is within ``pct%`` of ``expected``."""
    if expected == 0:
        return actual == 0
    diff = abs(actual - expected)
    return (diff * 100) <= (expected * pct)


def check_hero_image(path: Path) -> None:
    """Run all deterministic checks on the hero PNG at ``path``.

    Raises:
        ImageGateError: with a single human-readable message naming
        the first failing check. (We stop at the first failure rather
        than aggregating because each check is a prerequisite for the
        next — there's no point measuring dimensions of a non-PNG.)
    """
    if not path.exists():
        raise ImageGateError(
            f"hero image not found at {path}. "
            "Drop the PNG generated from the image prompt and re-run "
            "`--resume`, or re-run with `--no-image` to ship chart-only."
        )

    size = path.stat().st_size
    if size < MIN_BYTES:
        raise ImageGateError(
            f"hero image at {path} is {size} bytes (<{MIN_BYTES} byte "
            "minimum). Looks like a placeholder or truncated download — "
            "re-export from the image tool."
        )

    width, height = _read_png_dimensions(path)
    width_ok = _within_tolerance(width, EXPECTED_WIDTH, DIM_TOLERANCE_PCT)
    height_ok = _within_tolerance(height, EXPECTED_HEIGHT, DIM_TOLERANCE_PCT)
    if not (width_ok and height_ok):
        raise ImageGateError(
            f"hero image dimensions {width}x{height} not within "
            f"{DIM_TOLERANCE_PCT}% of expected "
            f"{EXPECTED_WIDTH}x{EXPECTED_HEIGHT}. Re-generate at the "
            "correct aspect ratio (1792x1024 landscape hero) or resize."
        )
