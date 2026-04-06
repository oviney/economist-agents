#!/usr/bin/env python3
"""
Topic Scout Agent

Monitors the quality engineering landscape to identify high-value article topics.
Runs weekly (or on-demand) to populate the content queue with timely, relevant topics.

Sources analyzed:
- Industry news and announcements
- Conference talk trends
- Tool/framework releases
- Research papers and reports
- Community discussions (Reddit, HN, dev.to)
- Competitor content gaps

Output: Ranked list of topics with data availability scores
"""

import json
import os
from datetime import datetime

from agent_loader import load_scout_prompts as _load_scout_prompts

# Content Intelligence: real blog performance data from GA4 ETL (ADR-0007)
from content_intelligence import get_performance_context

# Import unified LLM client
from llm_client import call_llm, create_llm_client

_scout_prompts = _load_scout_prompts()
SCOUT_AGENT_PROMPT = _scout_prompts["scout"]
TREND_RESEARCH_PROMPT = _scout_prompts["trend"]


def create_client():
    """Create unified LLM client (supports Anthropic Claude and OpenAI)"""
    return create_llm_client()


def scout_topics(client, focus_area: str = None) -> list:
    """
    Scout for high-value topics.

    Args:
        focus_area: Optional filter (e.g., "test automation", "AI", "performance")

    Returns:
        List of scored topic recommendations
    """
    print("🔭 Topic Scout Agent: Scanning the landscape...\n")

    # Load real blog performance data (ADR-0007 feedback loop).
    # Gracefully degrades if data/performance.db is missing.
    print("   Loading performance context from GA4 data...")
    performance_context = get_performance_context(top_limit=5, bottom_limit=5)

    # First, gather current trends
    trend_prompt = TREND_RESEARCH_PROMPT
    if focus_area:
        trend_prompt += f"\n\nFocus especially on: {focus_area}"

    print("   Researching current trends...")
    trends = call_llm(
        client,
        "",  # No system prompt for this call
        trend_prompt,
        max_tokens=2000,
    )

    # Then, identify topics based on trends AND real blog performance
    print("   Identifying high-value topics (informed by real audience data)...")
    scout_prompt = f"""{performance_context}

---

## Current Trends in Quality Engineering

{trends}

---

{SCOUT_AGENT_PROMPT}"""

    response_text = call_llm(
        client,
        "",  # System prompt embedded in scout_prompt
        scout_prompt,
        max_tokens=3000,
    )

    # Parse JSON from response
    try:
        start = response_text.find("[")
        end = response_text.rfind("]") + 1
        if start != -1 and end > start:
            topics = json.loads(response_text[start:end])
        else:
            print("   ⚠ Could not parse topic list")
            return []
    except json.JSONDecodeError as e:
        print(f"   ⚠ JSON parse error: {e}")
        return []

    # Sort by score
    topics.sort(key=lambda x: x.get("total_score", 0), reverse=True)

    print(f"\n✅ Found {len(topics)} high-value topics:\n")
    for i, t in enumerate(topics, 1):
        score = t.get("total_score", 0)
        print(f"   {i}. [{score}/25] {t['topic']}")
        print(f"      └─ {t.get('hook', 'No hook')[:80]}...")

    return topics


def update_content_queue(topics: list, queue_file: str = "content_queue.json"):
    """Save scouted topics to a queue file."""
    queue_data = {"updated": datetime.now().isoformat(), "topics": topics}
    with open(queue_file, "w") as f:
        json.dump(queue_data, f, indent=2)
    print(f"\n📝 Saved {len(topics)} topics to {queue_file}")


def format_for_workflow(topics: list) -> str:
    """Format topics for GitHub Actions workflow dispatch."""
    output = []
    for t in topics:
        output.append(
            {
                "topic": t["topic"],
                "category": "quality-engineering",
                "talking_points": t.get("talking_points", ""),
                "score": t.get("total_score", 0),
            }
        )
    return json.dumps(output, indent=2)


def main():
    client = create_client()

    # Optional focus area from environment
    focus = os.environ.get("FOCUS_AREA", "").strip()

    topics = scout_topics(client, focus if focus else None)

    if topics:
        # Save to queue
        update_content_queue(topics)

        # Also output for GitHub Actions
        print("\n" + "=" * 60)
        print("WORKFLOW-READY FORMAT:")
        print("=" * 60)
        print(format_for_workflow(topics))

        # Set output for GitHub Actions
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                # Escape for GitHub Actions
                topics_json = (
                    json.dumps(topics)
                    .replace("%", "%25")
                    .replace("\n", "%0A")
                    .replace("\r", "%0D")
                )
                f.write(f"topics={topics_json}\n")
                f.write(f"top_topic={topics[0]['topic']}\n")


if __name__ == "__main__":
    main()
