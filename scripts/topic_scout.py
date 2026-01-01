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

import os
import json
from datetime import datetime

# Import unified LLM client
from llm_client import create_llm_client, call_llm

SCOUT_AGENT_PROMPT = """You are a Topic Scout for a quality engineering blog targeting senior engineers and engineering leaders.

YOUR MISSION:
Identify 5 high-value article topics that would resonate with this audience RIGHT NOW.

EVALUATION CRITERIA (score each 1-5):

1. TIMELINESS (Is this relevant now?)
   - Recent tool releases, acquisitions, or announcements
   - Emerging practices gaining traction
   - Industry shifts or controversies
   - Upcoming conference themes

2. DATA AVAILABILITY (Can we make charts?)
   - Are there surveys, reports, or studies with numbers?
   - Benchmark data available?
   - Trend data over time?
   - Comparison data across companies/tools?

3. CONTRARIAN POTENTIAL (Can we say something different?)
   - Is conventional wisdom wrong or incomplete?
   - Underreported angles?
   - Unpopular but defensible positions?

4. AUDIENCE FIT (Will senior QE leaders care?)
   - Strategic implications for QE functions
   - Budget/headcount decisions
   - Career-relevant for QE leaders
   - Actionable for practitioners

5. ECONOMIST STYLE FIT (Can we make this sharp and witty?)
   - Clear thesis possible
   - Inherent tension or paradox
   - Good title potential (puns, wordplay)

TOPIC CATEGORIES TO MONITOR:
- Test automation economics (ROI, maintenance costs, build times)
- AI/ML in testing (copilots, test generation, visual testing)
- Platform engineering & developer experience
- Shift-left/shift-right movements
- Quality metrics and observability
- Tool ecosystem changes (Playwright, Cypress, k6, etc.)
- Organizational models (embedded QE, SRE, platform teams)
- Performance and reliability engineering
- Security testing integration
- Mobile and cross-platform testing

OUTPUT FORMAT:
Return a JSON array of exactly 5 topics:
[
  {
    "topic": "Clear, specific article title",
    "hook": "The attention-grabbing angle or stat (1 sentence)",
    "thesis": "The main argument we'd make (1 sentence)",
    "data_sources": ["Where we'd get numbers for charts"],
    "timeliness_trigger": "Why now? What happened recently?",
    "contrarian_angle": "How we'd challenge conventional wisdom",
    "title_ideas": ["Economist-style title option 1", "Option 2"],
    "scores": {
      "timeliness": 4,
      "data_availability": 5,
      "contrarian_potential": 3,
      "audience_fit": 5,
      "economist_fit": 4
    },
    "total_score": 21,
    "talking_points": "key point 1, key point 2, key point 3"
  }
]

Sort by total_score descending. Be specific—not "AI in Testing" but "Why AI Test Generation Tools Are Overpromising on Maintenance Reduction".
"""

TREND_RESEARCH_PROMPT = """You are researching current trends in software quality engineering.

Search for and analyze:
1. Recent announcements from major testing tool vendors (last 30 days)
2. Hot discussions in QE communities
3. New research reports or surveys on testing practices
4. Conference talk submissions/trends (if visible)
5. Job posting trends for QE roles
6. Venture capital activity in testing/quality space

For each finding, note:
- What happened
- When (be specific)
- Why it matters to QE leaders
- Data/numbers if available

Focus on developments that would interest a senior QE leader making strategic decisions."""


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
    
    # First, gather current trends
    trend_prompt = TREND_RESEARCH_PROMPT
    if focus_area:
        trend_prompt += f"\n\nFocus especially on: {focus_area}"
    
    print("   Researching current trends...")
    trends = call_llm(
        client,
        "",  # No system prompt for this call
        trend_prompt,
        max_tokens=2000
    )
    
    # Then, identify topics based on trends
    print("   Identifying high-value topics...")
    scout_prompt = f"""Based on these current trends in quality engineering:

{trends}

{SCOUT_AGENT_PROMPT}"""
    
    response_text = call_llm(
        client,
        "",  # System prompt embedded in scout_prompt
        scout_prompt,
        max_tokens=3000
    )
    
    # Parse JSON from response
    try:
        start = response_text.find('[')
        end = response_text.rfind(']') + 1
        if start != -1 and end > start:
            topics = json.loads(response_text[start:end])
        else:
            print("   ⚠ Could not parse topic list")
            return []
    except json.JSONDecodeError as e:
        print(f"   ⚠ JSON parse error: {e}")
        return []
    
    # Sort by score
    topics.sort(key=lambda x: x.get('total_score', 0), reverse=True)
    
    print(f"\n✅ Found {len(topics)} high-value topics:\n")
    for i, t in enumerate(topics, 1):
        score = t.get('total_score', 0)
        print(f"   {i}. [{score}/25] {t['topic']}")
        print(f"      └─ {t.get('hook', 'No hook')[:80]}...")
    
    return topics


def update_content_queue(topics: list, queue_file: str = "content_queue.json"):
    """Save scouted topics to a queue file."""
    queue_data = {
        "updated": datetime.now().isoformat(),
        "topics": topics
    }
    with open(queue_file, 'w') as f:
        json.dump(queue_data, f, indent=2)
    print(f"\n📝 Saved {len(topics)} topics to {queue_file}")


def format_for_workflow(topics: list) -> str:
    """Format topics for GitHub Actions workflow dispatch."""
    output = []
    for t in topics:
        output.append({
            "topic": t["topic"],
            "category": "quality-engineering",
            "talking_points": t.get("talking_points", ""),
            "score": t.get("total_score", 0)
        })
    return json.dumps(output, indent=2)


def main():
    client = create_client()
    
    # Optional focus area from environment
    focus = os.environ.get('FOCUS_AREA', '').strip()
    
    topics = scout_topics(client, focus if focus else None)
    
    if topics:
        # Save to queue
        update_content_queue(topics)
        
        # Also output for GitHub Actions
        print("\n" + "="*60)
        print("WORKFLOW-READY FORMAT:")
        print("="*60)
        print(format_for_workflow(topics))
        
        # Set output for GitHub Actions
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                # Escape for GitHub Actions
                topics_json = json.dumps(topics).replace('%', '%25').replace('\n', '%0A').replace('\r', '%0D')
                f.write(f"topics={topics_json}\n")
                f.write(f"top_topic={topics[0]['topic']}\n")


if __name__ == "__main__":
    main()
