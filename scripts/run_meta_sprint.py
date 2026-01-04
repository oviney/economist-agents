#!/usr/bin/env python3
"""
Meta-Sprint Runner for Self-Documentation

Orchestrates the meta-blog article generation where the economist-agents
system writes about itself. Uses ContextManager to inject repository
documentation as research data, bypassing external topic scouting.

Architecture:
    1. Initialize ContextManager with STORY_META_BLOG.md
    2. Read README.md and QUALITY_DASHBOARD.md as research sources
    3. Inject content into context (research_data, topic_status)
    4. Execute blog generation pipeline with pre-loaded context

Usage:
    ./run.sh scripts/run_meta_sprint.py [--output-dir OUTPUT_DIR]

Sprint 10 Context:
- Story: Meta-Blog About Economist-Agents Architecture
- Research Source: Repository self-documentation
- Goal: Demonstrate multi-agent capabilities via self-analysis
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from context_manager import ContextManager
from economist_agent import generate_economist_post


def start_sprint(output_dir: str = "output") -> dict:
    """
    Execute meta-sprint for self-documentation blog article.

    Strategy:
    1. Initialize ContextManager with story context
    2. Read repository documentation files
    3. Inject as research_data to bypass Topic Scout
    4. Mark topic as approved to skip external search
    5. Run blog generation with injected context

    Args:
        output_dir: Directory for article output (default: "output")

    Returns:
        dict: Blog generation results with article_path, metrics

    Raises:
        FileNotFoundError: If required context or research files missing
        ValueError: If context initialization fails
    """
    print("\n" + "=" * 70)
    print("🚀 META-SPRINT: Economist-Agents Self-Documentation")
    print("=" * 70 + "\n")

    # Step 1: Initialize ContextManager with story context
    story_path = "docs/STORY_META_BLOG.md"
    print(f"📋 Loading story context: {story_path}")

    if not Path(story_path).exists():
        raise FileNotFoundError(
            f"Story context not found: {story_path}\n"
            f"Please ensure STORY_META_BLOG.md exists in docs/ directory"
        )

    ctx = ContextManager(story_path)
    print(f"   ✓ Story loaded: {ctx.get('title', 'Unknown')}")
    print(f"   ✓ Story points: {ctx.get('story_points', 'Unknown')}")
    print(f"   ✓ Priority: {ctx.get('priority', 'Unknown')}")

    # Step 2: Automated Research - Read repository documentation
    print("\n📚 Automated Research: Reading repository documentation...")

    research_files = {
        "README.md": "Project overview, architecture, metrics",
        "docs/QUALITY_DASHBOARD.md": "Quality metrics, agent performance",
    }

    research_data = {}
    for file_path, description in research_files.items():
        full_path = Path(file_path)
        if not full_path.exists():
            print(f"   ⚠️  Warning: {file_path} not found - skipping")
            continue

        print(f"   Reading: {file_path} ({description})")
        with open(full_path, encoding="utf-8") as f:
            content = f.read()
            research_data[file_path] = {
                "content": content,
                "description": description,
                "size_bytes": len(content.encode("utf-8")),
                "lines": content.count("\n") + 1,
            }
        print(
            f"      ✓ Loaded {research_data[file_path]['lines']} lines, "
            f"{research_data[file_path]['size_bytes']:,} bytes"
        )

    if not research_data:
        raise FileNotFoundError(
            "No research files found. Ensure README.md and "
            "docs/QUALITY_DASHBOARD.md exist."
        )

    print(f"\n   ✓ Total research sources: {len(research_data)}")
    total_bytes = sum(d["size_bytes"] for d in research_data.values())
    print(f"   ✓ Total research data: {total_bytes:,} bytes")

    # Step 3: Context Injection - Store research data in context
    print("\n💉 Context Injection: Loading research into shared context...")

    ctx.set("research_data", research_data)
    ctx.set("research_files", list(research_data.keys()))
    ctx.set(
        "research_summary",
        {
            "total_files": len(research_data),
            "total_bytes": total_bytes,
            "files": {
                path: {"lines": data["lines"], "description": data["description"]}
                for path, data in research_data.items()
            },
        },
    )

    print(f"   ✓ Research data injected: {len(research_data)} files")

    # Step 4: Override - Mark topic as approved (bypass Topic Scout)
    print("\n⏭️  Override: Bypassing Topic Scout (topic pre-approved)...")

    ctx.set("topic_status", "approved")
    ctx.set("topic_source", "meta-sprint")
    ctx.set(
        "topic_reason",
        "Self-documentation meta-story - research source is repository itself",
    )

    print("   ✓ Topic status: approved")
    print("   ✓ Topic Scout: bypassed")

    # Step 5: Execute - Run blog generation with injected context
    print("\n🎬 Execute: Starting blog generation pipeline...\n")

    # Extract topic and category from context
    topic = ctx.get(
        "title",
        "How Six AI Personas Vote on Your Content: Inside the Economist-Agents Architecture",
    )
    category = ctx.get("category", "software-engineering")

    # Build talking points from story context
    talking_points_list = []
    if ctx.get("key_innovation"):
        talking_points_list.append(ctx.get("key_innovation"))
    if ctx.get("metrics_to_highlight"):
        metrics = ctx.get("metrics_to_highlight", [])
        if isinstance(metrics, list):
            talking_points_list.extend(metrics[:3])  # Top 3 metrics

    talking_points = ", ".join(talking_points_list) if talking_points_list else ""

    # Format research data for talking points
    if research_data:
        talking_points += (
            f"\n\nResearch Source: Repository self-documentation "
            f"({len(research_data)} files: {', '.join(research_data.keys())})"
        )

    # Run the blog generation
    try:
        result = generate_economist_post(
            topic=topic,
            category=category,
            talking_points=talking_points,
            output_dir=output_dir,
            interactive=False,  # Automated execution for meta-sprint
            governance=None,
        )

        print("\n" + "=" * 70)
        print("✅ META-SPRINT COMPLETE")
        print("=" * 70)
        print(f"\n   Article: {result.get('article_path', 'N/A')}")
        print(f"   Word count: {result.get('word_count', 0)}")
        print(f"   Gates passed: {result.get('gates_passed', 0)}/5")

        if result.get("chart_path"):
            print(f"   Chart: {result.get('chart_path')}")

        # Append context summary to result
        result["context_manager"] = {
            "story_id": ctx.story_id,
            "research_files": len(research_data),
            "research_bytes": total_bytes,
            "topic_status": ctx.get("topic_status"),
        }

        return result

    except Exception as e:
        print(f"\n❌ Meta-sprint execution failed: {e}")
        raise


def main():
    """CLI entry point for meta-sprint execution."""
    parser = argparse.ArgumentParser(
        description="Run meta-sprint for economist-agents self-documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default output to output/ directory
  ./run.sh scripts/run_meta_sprint.py

  # Custom output directory
  ./run.sh scripts/run_meta_sprint.py --output-dir articles/

  # With blog directory
  ./run.sh scripts/run_meta_sprint.py --output-dir /path/to/blog/_posts

Sprint 10 Context:
  Story: STORY_META_BLOG.md (3 story points)
  Research: Repository self-documentation
  Goal: Demonstrate multi-agent capabilities
        """,
    )

    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory for generated article (default: output/)",
    )

    args = parser.parse_args()

    try:
        result = start_sprint(output_dir=args.output_dir)
        sys.exit(0 if result.get("gates_passed", 0) >= 4 else 1)

    except FileNotFoundError as e:
        print(f"\n❌ Missing required file: {e}")
        sys.exit(2)

    except Exception as e:
        print(f"\n❌ Meta-sprint failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
