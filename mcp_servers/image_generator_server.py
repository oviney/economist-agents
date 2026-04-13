#!/usr/bin/env python3
"""
Image Generator MCP Server

Exposes DALL-E 3 editorial image generation as an MCP tool so that any
agent in the pipeline can request an Economist-style illustration without
knowing the underlying OpenAI API details.

Usage (stdio transport):
    python3 mcp_servers/image_generator_server.py

Requires:
    OPENAI_API_KEY environment variable
"""

import base64
import binascii
import logging
import os
from pathlib import Path
from typing import Literal

import openai
import requests
from mcp.server.fastmcp import FastMCP

# ═══════════════════════════════════════════════════════════════════════════
# ECONOMIST EDITORIAL ILLUSTRATION STYLE
# (Sourced from skills/editorial-illustration/SKILL.md)
# ═══════════════════════════════════════════════════════════════════════════

ECONOMIST_IMAGE_STYLE = """
Create an editorial illustration in the style of The Economist magazine's
bold, graphic cover art and editorial imagery.

STYLE:
- Bold, high-contrast graphic editorial illustration
- Strong geometric compositions with confident lines and shapes
- Conceptual metaphor: human figures or symbolic objects representing ideas
- Clear dominant foreground subject against a minimal or abstract background
- NOT watercolour, NOT oil painting, NOT photorealism, NOT soft brushstrokes
- NOT pastel, NOT painterly, NOT textured canvas

CRITICAL - NO TEXT:
- ABSOLUTELY NO TEXT, WORDS, LETTERS, NUMBERS, OR SYMBOLS ANYWHERE
- No labels, captions, signs, or written content of any kind

HUMAN ELEMENT (MANDATORY):
- Always include at least one human figure or symbolic object representing a person
- Stylised but expressive — body language tells the story
- People in suits, at desks, in boardrooms, on factory floors
- Show emotion: frustration, curiosity, determination, bemusement

COLOUR PALETTE (BOLD AND LIMITED):
- Economist red: #E3120B as a primary accent
- Strong blues: #3b6d8f, #17648d, navy
- High-contrast darks: charcoal #333333, deep navy #1a1a2e
- Accents: dusty red #a34054, ochre #c4953a
- Background: clean white, off-white #f4f0e6, or flat colour blocks
- Use bold colour blocking — large areas of flat, saturated colour
- Avoid gradients, soft washes, or muted pastel tones

COMPOSITION:
- Strong geometric composition with clear visual hierarchy
- Clear dominant foreground subject
- Minimal or abstract background — NOT busy, NOT detailed environments
- Use scale exaggeration for editorial effect (tiny person, enormous machine)
- Generous negative space on one side for text overlay

AVOID:
- Technology clichés: lightbulbs, upward arrows, gears, puzzle pieces
- Generic abstract shapes that could represent anything
- Watercolour, oil painting, or any fine-art painting aesthetic
- Photorealism or stock photo aesthetics
- Soft gradients, pastel colours, or delicate brushwork
- Busy, cluttered compositions

TONE:
- Confident and authoritative
- Intelligent and thought-provoking
- Slightly satirical or wry
- Timeless, not trendy
"""


logger = logging.getLogger(__name__)

# DALL-E 3 rejects prompts longer than 4000 characters.  We cap at 3900 to
# leave a small safety margin and avoid silent generation failures.
DALLE_MAX_PROMPT_LENGTH = 3900


def _truncate_prompt(prompt: str, context: str = "DALL-E") -> str:
    """Truncate *prompt* to :data:`DALLE_MAX_PROMPT_LENGTH` if necessary.

    Args:
        prompt: The prompt string to check and possibly truncate.
        context: Label used in the warning log message.

    Returns:
        The original prompt (unchanged) when it is within the limit,
        or a truncated copy otherwise.
    """
    if len(prompt) > DALLE_MAX_PROMPT_LENGTH:
        logger.warning(
            "%s prompt length %d exceeds %d chars; truncating",
            context,
            len(prompt),
            DALLE_MAX_PROMPT_LENGTH,
        )
        return prompt[:DALLE_MAX_PROMPT_LENGTH]
    return prompt


mcp = FastMCP(
    name="image-generator",
    instructions=(
        "Generates Economist-style editorial illustrations using DALL-E 3. "
        "Requires the OPENAI_API_KEY environment variable."
    ),
)


def _build_dalle_prompt(article_title: str, article_summary: str) -> str:
    """Build the DALL-E 3 prompt from the editorial illustration template.

    Args:
        article_title: Headline or title of the article.
        article_summary: 2–3 sentence summary of the article's argument.

    Returns:
        Formatted prompt string ready for the DALL-E 3 API.
    """
    prompt = f"{ECONOMIST_IMAGE_STYLE}\n\n"
    prompt += f"ARTICLE TOPIC: {article_title}\n\n"
    prompt += f"ARTICLE SUMMARY: {article_summary}\n\n"
    prompt += (
        "TASK: Create a bold, graphic SCENE with a conceptual metaphor that captures "
        "the article's argument.\n\n"
        'Think: "What single striking image would The Economist put on its cover '
        "to represent this article's thesis?\"\n\n"
        "The viewer should understand the article's ARGUMENT from the image, "
        "not just its topic.\n\n"
        "CRITICAL: ZERO text, words, letters, numbers, or symbols in the image."
    )
    return _truncate_prompt(prompt)


@mcp.tool()
def generate_editorial_image(
    article_title: str,
    article_summary: str,
    output_path: str,
) -> dict:
    """Generate an Economist-style editorial illustration using DALL-E 3.

    Wraps the DALL-E 3 API call with The Economist's editorial illustration
    prompt template (bold graphic illustration, human figures, no text).
    The generated image is saved to *output_path* and the function returns
    metadata about the saved file.

    Args:
        article_title: Headline or title of the article.
        article_summary: 2–3 sentence summary describing the article's argument.
        output_path: Filesystem path where the PNG should be saved.
            Parent directories are created automatically.

    Returns:
        On success::

            {"path": "<output_path>", "size_bytes": <int>}

        On failure::

            {"error": "<description>", "path": None, "size_bytes": 0}

    Raises:
        Nothing — all exceptions are caught and returned as structured errors.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY is not set")
        return {
            "error": "OPENAI_API_KEY environment variable is not set",
            "path": None,
            "size_bytes": 0,
        }

    prompt = _build_dalle_prompt(article_title, article_summary)

    # Allow operators to tune the image-download timeout via the environment.
    # Fall back to 15 s if the value is missing, non-numeric, or non-positive.
    try:
        download_timeout = int(os.environ.get("IMAGE_DOWNLOAD_TIMEOUT_SECONDS", "15"))
        if download_timeout <= 0:
            raise ValueError("timeout must be greater than zero")
    except ValueError:
        logger.warning(
            "IMAGE_DOWNLOAD_TIMEOUT_SECONDS must be a positive integer; using default of 15 s"
        )
        download_timeout = 15

    try:
        client = openai.OpenAI(api_key=api_key)

        logger.info("Calling DALL-E 3 for '%s'", article_title[:60])
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",
            quality="hd",
            n=1,
        )

        if not response.data:
            return {
                "error": "DALL-E returned no image data",
                "path": None,
                "size_bytes": 0,
            }

        image_data = response.data[0]

        b64_json = getattr(image_data, "b64_json", None)
        image_url = getattr(image_data, "url", None)

        if b64_json:
            try:
                image_bytes = base64.b64decode(b64_json)
            except binascii.Error as exc:
                logger.error("Failed to decode base64 image data: %s", exc)
                return {
                    "error": f"Failed to decode base64 image data: {exc}",
                    "path": None,
                    "size_bytes": 0,
                }
        elif image_url:
            http_response = requests.get(image_url, timeout=download_timeout)
            http_response.raise_for_status()
            image_bytes = http_response.content
        else:
            return {
                "error": "No image data (neither b64_json nor url) in DALL-E response",
                "path": None,
                "size_bytes": 0,
            }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(image_bytes)

        size_bytes = len(image_bytes)
        logger.info("Image saved to %s (%d bytes)", output_path, size_bytes)

        return {"path": str(output_path), "size_bytes": size_bytes}

    except openai.AuthenticationError as exc:
        logger.error("OpenAI authentication failed: %s", exc)
        return {
            "error": f"Invalid OpenAI API key: {exc}",
            "path": None,
            "size_bytes": 0,
        }
    except (requests.RequestException, OSError) as exc:
        logger.error("I/O error during image generation: %s", exc)
        return {
            "error": f"I/O error during image generation: {exc}",
            "path": None,
            "size_bytes": 0,
        }
    except openai.OpenAIError as exc:
        logger.error("OpenAI API error: %s", exc)
        return {
            "error": f"OpenAI API error: {exc}",
            "path": None,
            "size_bytes": 0,
        }


@mcp.tool()
def generate_image(
    prompt: str,
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1792x1024",
) -> dict:
    """Generate an image using DALL-E 3 and return its URL.

    A lightweight wrapper around the DALL-E 3 API that accepts a raw prompt
    and returns the hosted image URL together with the revised prompt that
    OpenAI used.

    Args:
        prompt: Text description of the image to generate.
        size: Image dimensions — one of ``"1792x1024"`` (default, landscape),
              ``"1024x1024"`` (square), or ``"1024x1792"`` (portrait).

    Returns:
        A dictionary with keys:

        - ``url`` (str): HTTPS URL to the generated image.
        - ``revised_prompt`` (str): The prompt OpenAI actually used
          (may differ from the input if DALL-E rewrote it for safety).

    Raises:
        ValueError: If ``OPENAI_API_KEY`` is not set in the environment.
        openai.OpenAIError: If the API call fails.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is not set. "
            "Please export OPENAI_API_KEY=<your-key> before using this tool."
        )

    client = openai.OpenAI(api_key=api_key)
    prompt = _truncate_prompt(prompt, context="Raw DALL-E")
    logger.info("Calling DALL-E 3 for prompt (first 60 chars): %r", prompt[:60])

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality="hd",
        n=1,
    )

    image_data = response.data[0]
    url = image_data.url or ""
    revised_prompt = image_data.revised_prompt or prompt

    logger.info("Image generated: url=%r", url[:80] if url else "(empty)")
    return {"url": url, "revised_prompt": revised_prompt}


if __name__ == "__main__":
    mcp.run(transport="stdio")
