#!/usr/bin/env python3
"""
Featured Image Generation Agent for Economist-Style Articles

Generates DALL-E 3 editorial illustrations that match The Economist's visual style:
- Minimalist, conceptual, symbolic
- Limited color palette (navy #17648d, burgundy #843844, beige #f1f0e9)
- Professional, businesslike tone
- No text or labels
- Avoids clichés (lightbulbs, arrows, gears)

Usage:
    from featured_image_agent import generate_featured_image

    image_path = generate_featured_image(
        topic="The Economics of Flaky Tests",
        article_summary="QA teams spend 30% of time debugging unreliable tests...",
        output_path="assets/images/flaky-tests.png"
    )
"""

import base64
import os
from pathlib import Path
from typing import Literal

# ═══════════════════════════════════════════════════════════════════════════
# ECONOMIST VISUAL STYLE SPECIFICATION
# ═══════════════════════════════════════════════════════════════════════════

ECONOMIST_IMAGE_STYLE = """
Create an editorial illustration in the style of The Economist magazine's
commissioned artwork — the kind by David Parkins or Kevin "KAL" Kallaugher.

STYLE:
- Painterly, textured illustration with visible brushstrokes
- Think oil painting meets political cartoon
- Rich, layered composition with depth and dimension
- NOT flat vector art, NOT minimalist icons, NOT stock photography
- Cross-hatching, colour washes, and artistic texture throughout

CRITICAL - NO TEXT:
- ABSOLUTELY NO TEXT, WORDS, LETTERS, NUMBERS, OR SYMBOLS ANYWHERE
- No labels, captions, signs, or written content of any kind

HUMAN ELEMENT (MANDATORY):
- Always include at least one human figure
- Stylised but expressive — body language tells the story
- People in suits, at desks, in boardrooms, on factory floors
- Show emotion: frustration, curiosity, determination, bemusement

COLOUR PALETTE (RICH AND MUTED):
- Blues: #3b6d8f, #17648d, steel blue
- Warm greys: #8a8a8a, charcoal shadows
- Accents: dusty red #a34054, ochre #c4953a, sage green #7a9a6f
- Natural skin tones, varied
- Background: cream #f4f0e6, warm grey #d9d3c7, parchment
- Avoid pure black, neon, or oversaturated colours

COMPOSITION:
- Asymmetric, with a clear focal point
- Use scale exaggeration for editorial effect (tiny person, enormous machine)
- Overlapping elements create depth and dimension
- Environmental context — place subjects in real settings (offices, cities)
- Generous negative space on one side for text overlay

AVOID:
- Technology clichés: lightbulbs, upward arrows, gears, puzzle pieces
- Generic abstract shapes that could represent anything
- Flat design or icon-like simplicity
- Photorealism or stock photo aesthetics

TONE:
- Intelligent and thought-provoking
- Slightly satirical or wry
- Confident editorial voice
- Timeless, not trendy
"""


def create_image_prompt(
    topic: str, article_summary: str, contrarian_angle: str = ""
) -> str:
    """
    Generate DALL-E 3 prompt for Economist-style featured image.

    Args:
        topic: Article headline/title
        article_summary: 2-3 sentence summary of article
        contrarian_angle: The counterintuitive take (if available)

    Returns:
        Formatted prompt for DALL-E 3
    """

    # Build the prompt
    prompt = f"{ECONOMIST_IMAGE_STYLE}\n\n"
    prompt += f"ARTICLE TOPIC: {topic}\n\n"
    prompt += f"ARTICLE SUMMARY: {article_summary}\n\n"

    if contrarian_angle:
        prompt += f"CONTRARIAN ANGLE: {contrarian_angle}\n\n"

    prompt += """
TASK: Create a SCENE, not a symbol. Show a specific moment that captures
the article's argument.

Think: "What would a photograph of this article's thesis look like, if
drawn by a political cartoonist with a paintbrush?"

Examples of good scenes:
- Article about AI failure → A person in a suit staring at a massive
  computer screen showing gibberish, painted in frustrated oil strokes
- Article about testing costs → An engineer buried under a towering pile
  of paper test reports, rendered in watercolour with dusty red accents
- Article about security → A figure holding a cracked umbrella while
  digital rain pours through, in textured blue-grey tones

The viewer should understand the article's ARGUMENT from the image,
not just its topic.

CRITICAL: ZERO text, words, letters, numbers, or symbols in the image.
"""

    return prompt


def generate_featured_image(
    topic: str,
    article_summary: str,
    output_path: str,
    contrarian_angle: str = "",
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1792x1024",
    quality: Literal["standard", "hd"] = "hd",
) -> str | None:
    """
    Generate a featured image using DALL-E 3.

    Args:
        topic: Article headline
        article_summary: Brief summary of article content
        output_path: Where to save the generated image
        contrarian_angle: The article's counterintuitive take (optional)
        size: Image size (1024x1024, 1792x1024, or 1024x1792)
        quality: Image quality (standard or hd)

    Returns:
        Path to saved image, or None if generation failed

    Raises:
        ValueError: If output_path is invalid
        RuntimeError: If image generation fails
    """

    print(f"🎨 Featured Image Agent: Generating illustration for '{topic[:50]}...'")

    # Check if OpenAI API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        print("   ⚠️  OPENAI_API_KEY not set. Skipping image generation.")
        return None

    # Create the image prompt
    prompt = create_image_prompt(topic, article_summary, contrarian_angle)

    try:
        # Import OpenAI (only if API key is set)
        # Note: DALL-E uses specialized image generation endpoint, not standard chat
        # completion, so we maintain direct client instantiation here per ADR-002 exception
        import openai

        # Create OpenAI client for DALL-E image generation
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # Generate image with DALL-E 3
        print("   Calling DALL-E 3...")
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )

        # Get the image URL or b64_json
        # Type narrowing: response.data is list[Image] | None
        if not response.data:
            raise RuntimeError("DALL-E returned no image data")

        image_data = response.data[0]

        if hasattr(image_data, "b64_json") and image_data.b64_json:
            # Image returned as base64
            image_bytes = base64.b64decode(image_data.b64_json)
        elif hasattr(image_data, "url") and image_data.url:
            # Image returned as URL, need to download
            import requests

            image_response = requests.get(image_data.url, timeout=30)
            image_response.raise_for_status()
            image_bytes = image_response.content
        else:
            print("   ⚠️  No image data in response")
            return None

        # Save to output path
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "wb") as f:
            f.write(image_bytes)

        print(f"   ✓ Image saved to {output_path}")

        # Log the revised prompt (DALL-E 3 may revise prompts)
        if hasattr(image_data, "revised_prompt") and image_data.revised_prompt:
            print(f"   ℹ DALL-E revised prompt: {image_data.revised_prompt[:100]}...")

        return str(output_path)

    except Exception as e:
        print(f"   ⚠️  Image generation failed: {str(e)}")
        return None


def test_generate_sample_images():
    """Test function to generate sample images"""

    test_topics = [
        {
            "topic": "The Economics of Flaky Tests",
            "summary": "QA teams spend 30% of time debugging unreliable tests. The cost: $50k per engineer annually. Yet investment in test stability remains low.",
            "contrarian": "Flaky tests are a symptom of poor engineering culture, not a technical problem.",
        },
        {
            "topic": "Self-Healing Tests: Myth vs Reality",
            "summary": "AI promises 80% reduction in test maintenance. Industry data shows actual gains closer to 15%. Vendors oversell, teams under-deliver.",
            "contrarian": "Self-healing tests solve the wrong problem—they mask code quality issues.",
        },
        {
            "topic": "The Death of the QA Department",
            "summary": "Traditional QA roles shrinking while embedded quality engineers grow 40% annually. The shift reflects DevOps maturity.",
            "contrarian": "QA isn't dying—it's evolving into a more strategic, influential function.",
        },
    ]

    output_dir = Path("output/test-images")
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, test in enumerate(test_topics, 1):
        print(f"\n=== Test {i}/3 ===")
        output_path = str(output_dir / f"test-image-{i}.png")

        result = generate_featured_image(
            topic=test["topic"],
            article_summary=test["summary"],
            contrarian_angle=test["contrarian"],
            output_path=output_path,
        )

        if result:
            print(f"✅ Generated: {result}")
        else:
            print("❌ Generation failed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Economist-style featured images"
    )
    parser.add_argument("--test", action="store_true", help="Generate test images")
    parser.add_argument("--topic", help="Article topic/headline")
    parser.add_argument("--summary", help="Article summary")
    parser.add_argument("--contrarian", help="Contrarian angle (optional)")
    parser.add_argument("--output", help="Output image path")

    args = parser.parse_args()

    if args.test:
        test_generate_sample_images()
    elif args.topic and args.summary and args.output:
        generate_featured_image(
            topic=args.topic,
            article_summary=args.summary,
            contrarian_angle=args.contrarian or "",
            output_path=args.output,
        )
    else:
        parser.print_help()
