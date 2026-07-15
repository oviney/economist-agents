"""Gemini hero image generation (B-007).

The premium hero tier: when a Google Gemini key is present
(``GEMINI_API_KEY`` or ``GOOGLE_API_KEY`` — the free AI-Studio tier is enough),
generate a real conceptual editorial illustration with Gemini's image model.
Returns ``None`` on a missing key, missing SDK, or any error, so the caller
falls back to the keyless editorial hero — a hero is never blocked on this path.

No paid key: Google AI Studio issues a free Gemini API key at
https://aistudio.google.com/apikey.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Image-capable Gemini model. Overridable so the model id can move without a
# code change (the image-gen model line evolves quickly).
_DEFAULT_IMAGE_MODEL = "gemini-2.5-flash-image"

_STYLE_SUFFIX = (
    " Bold, high-contrast graphic editorial illustration in the style of The "
    "Economist: flat vector shapes, a restrained palette of Economist red, deep "
    "navy, burgundy and off-white, one clear conceptual metaphor, generous "
    "negative space. No text, no words, no captions, no logos. Landscape."
)


def _api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def generate_gemini_hero(prompt: str, output_path: str | Path) -> Path | None:
    """Generate an editorial hero with Gemini; return its path or ``None``.

    Args:
        prompt: The editorial illustration brief (subject + framing). A house
            style suffix is appended so the result stays on-brand.
        output_path: Destination PNG path (parent dirs created on success).

    Returns:
        The saved path, or ``None`` when no key/SDK is available or generation
        fails — signalling the caller to fall back to the keyless hero.
    """
    key = _api_key()
    if not key:
        logger.info("No GEMINI_API_KEY/GOOGLE_API_KEY — skipping Gemini hero")
        return None

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.warning(
            "google-genai not installed — skipping Gemini hero "
            "(pip install google-genai)"
        )
        return None

    model = os.environ.get("GEMINI_IMAGE_MODEL", _DEFAULT_IMAGE_MODEL)
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=model,
            contents=prompt.strip() + _STYLE_SUFFIX,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
        image_bytes = _extract_image_bytes(response)
        if not image_bytes:
            logger.warning("Gemini returned no image data — falling back")
            return None
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(image_bytes)
        logger.info("Generated Gemini hero (%s): %s", model, out)
        return out
    except Exception as exc:  # noqa: BLE001 — any failure → keyless fallback
        logger.warning("Gemini hero generation failed (%s) — falling back", exc)
        return None


def _extract_image_bytes(response: object) -> bytes | None:
    """Pull the first inline image payload out of a Gemini response, tolerating
    SDK shape differences."""
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            data = getattr(inline, "data", None)
            if data:
                return data
    return None
