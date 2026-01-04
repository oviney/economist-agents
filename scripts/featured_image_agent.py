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
VISUAL STYLE: Editorial illustration for The Economist magazine

REQUIREMENTS:
- Minimalist and conceptual (symbolic, not literal)
- Limited color palette:
  - Navy blue (#17648d) for primary subjects
  - Burgundy red (#843844) for accents or contrast
  - Warm beige (#f1f0e9) for backgrounds
  - Use negative space effectively
- Professional, businesslike tone
- No text, labels, or words in the image
- Avoid technology clichés:
  - NO lightbulbs (for ideas)
  - NO upward arrows (for growth)
  - NO gears or cogs (for systems)
  - NO puzzle pieces (for integration)
  - NO handshakes (for partnership)

COMPOSITION:
- Simple, clear focal point
- Abstract or metaphorical representation
- European editorial illustration aesthetic
- Flat design or subtle gradients only
- High contrast between elements
- Generous margins and breathing room

SUBJECTS TO FAVOR:
- Human figures in simplified, stylized form
- Architectural elements (buildings, bridges, structures)
- Geometric shapes with symbolic meaning
- Objects in unexpected contexts or scales
- Subtle visual puns or clever juxtapositions

TONE:
- Intelligent and thought-provoking
- Slightly wry or knowing
- Confident without being flashy
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
TASK: Create an editorial illustration that captures the essence of this article.
The image should be conceptual and metaphorical, not literal.
Think about what visual metaphor best represents the tension or paradox in the topic.

Remember:
- No text or labels
- Economist color palette only
- Avoid obvious tech clichés
- Favor clever, subtle symbolism over literal representation
"""

    return prompt


def generate_featured_image(
    topic: str,
    article_summary: str,
    output_path: str,
    contrarian_angle: str = "",
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1024x1024",
    quality: Literal["standard", "hd"] = "standard",
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
