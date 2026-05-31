"""Compose the ChatGPT-handoff prompt for the featured image (#403 slice 3).

The writer LLM already emits a strong ``image_alt`` line in the article
frontmatter — a one-sentence visual concept (e.g. "An Economist-style
editorial illustration of a lone product manager directing a swarm of
robotic agents..."). This module wraps that concept in the hard
constraints the image tool needs (aspect ratio, no-text, palette) and
returns a paste-ready string for the human to drop into chat.openai.com
or any other web-based image tool.

This is deliberately a pure-Python template — no LLM call, no API key,
no cost. The whole point of the handshake spec is to keep the image
step zero-spend and human-paced.

Signature change vs the plan
----------------------------
The plan listed ``compose_prompt(title, summary, themes)``. Switched to
``compose_prompt(title, image_alt, image_caption)`` after looking at the
writer's actual output: image_alt is already a fully-formed visual
concept the LLM generated; image_caption is the editorial frame. That
is strictly better than asking the writer for a summary + themes and
then synthesising a visual concept from those (we'd be redoing work
the writer already did).
"""

from __future__ import annotations

# Hard constraints that every prompt must end with. Kept as a module
# constant so tests can assert their presence and so the operator can
# eyeball them when reviewing the artefact.
_HARD_CONSTRAINTS: tuple[str, ...] = (
    "Palette: Economist red #E3120B, deep navy, off-white, one accent",
    "Aspect ratio: 1792x1024 (landscape hero)",
    "Constraints: no text, no words, no captions, no logos in the image itself",
    "Style: bold, high-contrast graphic editorial illustration "
    "(not painterly, not photorealistic)",
)

# Cap on inputs we drop into the prompt. Generous enough to keep the
# writer's full image_alt but short enough that a typo or stray HTML
# from a copy-paste can't bloat the output into something unwieldy.
_MAX_FIELD_LEN = 600


class PromptSynthError(ValueError):
    """Raised when required inputs are missing or empty."""


def _clean(s: str) -> str:
    """Trim, collapse internal whitespace, cap length."""
    cleaned = " ".join(s.split())
    return cleaned[:_MAX_FIELD_LEN]


def compose_prompt(
    title: str,
    image_alt: str,
    image_caption: str = "",
) -> str:
    """Return the ChatGPT-handoff prompt string for ``title``.

    Args:
        title: Article title (used for human-orientation only — the image
            tool does not see it as a directive).
        image_alt: The visual concept the writer LLM emitted in the
            frontmatter ``image_alt`` field. This is the actual instruction
            to the image tool.
        image_caption: Optional editorial caption from the frontmatter.
            When provided, surfaces as ``Editorial framing:`` so the
            image tool understands the tone the article sets.

    Returns:
        A plain-text prompt ready to paste verbatim into the ChatGPT
        web UI. No markdown, no code fences — image tools generally
        ignore those anyway and they make the artefact harder to read.

    Raises:
        PromptSynthError: ``title`` or ``image_alt`` is empty/whitespace.
    """
    if not title or not title.strip():
        raise PromptSynthError("title is required")
    if not image_alt or not image_alt.strip():
        raise PromptSynthError("image_alt is required")

    title_c = _clean(title)
    alt_c = _clean(image_alt)
    caption_c = _clean(image_caption)

    lines: list[str] = [
        f'Generate an editorial illustration for the article "{title_c}".',
        "",
        f"Subject: {alt_c}",
    ]
    if caption_c:
        lines.append(f"Editorial framing: {caption_c}")
    lines.append("")
    lines.extend(_HARD_CONSTRAINTS)

    return "\n".join(lines)
