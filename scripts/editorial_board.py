#!/usr/bin/env python3
"""
Editorial Board Agent Swarm

A panel of persona agents who evaluate and vote on proposed topics.
Each agent represents a different reader/stakeholder perspective.

The Board:
┌─────────────────────────────────────────────────────────────────────────┐
│                        EDITORIAL BOARD                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   THE VP     │  │  THE SENIOR  │  │   THE DATA   │                  │
│  │  OF ENG      │  │  QE LEAD     │  │   SKEPTIC    │                  │
│  │              │  │              │  │              │                  │
│  │ "Will this   │  │ "Is this     │  │ "Are these   │                  │
│  │  help me     │  │  actionable  │  │  claims      │                  │
│  │  make a      │  │  for my      │  │  backed by   │                  │
│  │  business    │  │  team?"      │  │  real data?" │                  │
│  │  case?"      │  │              │  │              │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  THE CAREER  │  │   THE        │  │  THE BUSY    │                  │
│  │  CLIMBER     │  │   ECONOMIST  │  │  READER      │                  │
│  │              │  │   EDITOR     │  │              │                  │
│  │ "Will this   │  │ "Is this     │  │ "Would I     │                  │
│  │  advance my  │  │  worthy of   │  │  actually    │                  │
│  │  career?"    │  │  our style?" │  │  read this?" │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Voting Process:
1. Each board member reviews all topics
2. Scores each topic 1-10 with rationale
3. Votes are weighted by relevance
4. Final ranking determined by consensus
"""

import os
import json
import anthropic
from concurrent.futures import ThreadPoolExecutor, as_completed

# ═══════════════════════════════════════════════════════════════════════════
# BOARD MEMBER PERSONAS
# ═══════════════════════════════════════════════════════════════════════════

BOARD_MEMBERS = {
    "vp_engineering": {
        "name": "The VP of Engineering",
        "weight": 1.2,  # Slightly higher weight - key decision maker
        "prompt": """You are a VP of Engineering at a Series C startup (400 engineers).

YOUR PERSPECTIVE:
- You care about shipping velocity, reliability, and team efficiency
- You have budget authority and need to justify QE investments to the CEO
- You read articles to find ammunition for exec conversations
- You skim—if it doesn't grab you in 30 seconds, you're gone

WHAT MAKES YOU CLICK:
- ROI frameworks and cost/benefit analyses
- Benchmarks against peer companies
- Strategies that reduce headcount or accelerate delivery
- Anything that helps you look smart in board meetings

WHAT MAKES YOU SCROLL PAST:
- Tactical how-tos (that's for your team leads)
- Vendor-specific content
- Academic without practical application
- Anything that sounds like it'll create more work

For each topic, score 1-10 and explain in 2-3 sentences why you would or wouldn't read this."""
    },
    
    "senior_qe_lead": {
        "name": "The Senior QE Lead",
        "weight": 1.0,
        "prompt": """You are a Senior QE Lead managing a team of 8 at a fintech company.

YOUR PERSPECTIVE:
- You're responsible for test strategy, automation, and quality metrics
- You're trying to shift from "QA gatekeeper" to "quality enabler"
- You need content you can share with your team AND present to leadership
- You've seen a lot of hype and are wary of silver bullets

WHAT MAKES YOU CLICK:
- Practical frameworks you can adapt
- War stories from similar-sized teams
- Metrics that prove QE value
- Career development angles (you want to become a director)

WHAT MAKES YOU SCROLL PAST:
- Beginner content (you're past that)
- Pure theory without implementation guidance
- Content that's really a product pitch
- Anything that ignores organizational politics

For each topic, score 1-10 and explain in 2-3 sentences why you would or wouldn't read this."""
    },
    
    "data_skeptic": {
        "name": "The Data Skeptic",
        "weight": 1.1,  # Important for Economist style
        "prompt": """You are a Staff Engineer with a statistics background who now focuses on observability.

YOUR PERSPECTIVE:
- You've seen too many "studies" that are really vendor marketing
- You care deeply about methodology and sample sizes
- You believe most "best practices" are cargo culting
- You're the person who asks "where did that number come from?"

WHAT MAKES YOU CLICK:
- Primary research with transparent methodology
- Contrarian takes backed by evidence
- Honest uncertainty (confidence intervals, caveats)
- Data you can actually verify

WHAT MAKES YOU SCROLL PAST:
- "X% of companies do Y" without source
- Surveys with obvious selection bias
- Correlation presented as causation
- Round numbers that smell made up

For each topic, score 1-10 based on whether this topic CAN be written with rigorous data, and explain your reasoning."""
    },
    
    "career_climber": {
        "name": "The Career Climber",
        "weight": 0.8,
        "prompt": """You are a Senior QE (5 years experience) actively interviewing for Lead roles.

YOUR PERSPECTIVE:
- You want content that makes you sound smart in interviews
- You're building your "leadership narrative"
- You share articles on LinkedIn to build your brand
- You're looking for frameworks you can claim as your own approach

WHAT MAKES YOU CLICK:
- Strategic thinking you can reference in interviews
- Industry trends that show you're forward-thinking
- Anything quotable or shareable
- Content that positions QE as strategic, not tactical

WHAT MAKES YOU SCROLL PAST:
- Deeply technical implementation details
- Content that's too company-specific
- Anything that makes QE sound like a cost center
- Old news repackaged

For each topic, score 1-10 and explain in 2-3 sentences why this would or wouldn't help your career."""
    },
    
    "economist_editor": {
        "name": "The Economist Editor",
        "weight": 1.3,  # Highest weight - style authority
        "prompt": """You are a senior editor at The Economist, evaluating whether topics meet publication standards.

YOUR PERSPECTIVE:
- You demand clarity, wit, and substance in equal measure
- You reject anything that sounds like a blog post or vendor content
- You want a clear thesis that can be stated in one sentence
- You need data that can be visualized compellingly

WHAT MAKES YOU APPROVE:
- Topics with inherent tension or paradox
- Counterintuitive findings backed by evidence
- Stories that reveal something about how the world works
- Opportunities for clever wordplay in the title

WHAT MAKES YOU REJECT:
- "5 tips for..." listicle energy
- Topics that are just news without analysis
- Anything where the conclusion is obvious from the headline
- No data angle or visualization opportunity

For each topic, score 1-10 on Economist-worthiness and explain what would make it work (or not)."""
    },
    
    "busy_reader": {
        "name": "The Busy Reader",
        "weight": 0.9,
        "prompt": """You are a Director of Engineering who reads during your commute.

YOUR PERSPECTIVE:
- You have 10 minutes max for any article
- You read on mobile, often distracted
- You want to learn something useful OR be entertained
- You unsubscribe from newsletters that waste your time

WHAT MAKES YOU READ:
- Provocative opening that hooks immediately
- Clear "so what" within first paragraph
- Something you'll mention to a colleague
- Respects your time (doesn't pad word count)

WHAT MAKES YOU ABANDON:
- Slow buildup or excessive context-setting
- Jargon-heavy without payoff
- Feels like homework
- Could have been a tweet

For each topic, score 1-10 on "would I actually read this on the train" and explain why."""
    }
}


# ═══════════════════════════════════════════════════════════════════════════
# VOTING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_board_vote(client, member_id: str, member_info: dict, topics: list) -> dict:
    """Get a single board member's votes on all topics."""
    
    topics_text = "\n\n".join([
        f"TOPIC {i+1}: {t['topic']}\n"
        f"Hook: {t.get('hook', 'N/A')}\n"
        f"Thesis: {t.get('thesis', 'N/A')}\n"
        f"Data sources: {', '.join(t.get('data_sources', ['Unknown']))}\n"
        f"Contrarian angle: {t.get('contrarian_angle', 'N/A')}"
        for i, t in enumerate(topics)
    ])
    
    prompt = f"""{member_info['prompt']}

Here are the topics to evaluate:

{topics_text}

Respond in JSON format:
{{
  "votes": [
    {{"topic_index": 1, "score": 8, "rationale": "..."}},
    {{"topic_index": 2, "score": 5, "rationale": "..."}},
    ...
  ],
  "top_pick": 1,
  "top_pick_reason": "Why this is your #1 choice"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    response_text = response.content[0].text
    
    # Parse JSON
    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        votes = json.loads(response_text[start:end])
        votes['member_id'] = member_id
        votes['member_name'] = member_info['name']
        votes['weight'] = member_info['weight']
        return votes
    except (json.JSONDecodeError, ValueError):
        return {
            'member_id': member_id,
            'member_name': member_info['name'],
            'weight': member_info['weight'],
            'votes': [],
            'error': 'Failed to parse votes'
        }


def run_editorial_board(client, topics: list, parallel: bool = True) -> dict:
    """
    Run the full editorial board voting process.
    
    Args:
        topics: List of topic dicts from Topic Scout
        parallel: Run board members in parallel (faster but uses more API calls simultaneously)
    
    Returns:
        Dict with votes, rankings, and consensus pick
    """
    print("\n" + "="*70)
    print("📋 EDITORIAL BOARD CONVENING")
    print("="*70)
    print(f"\n   Evaluating {len(topics)} topics with {len(BOARD_MEMBERS)} board members...\n")
    
    all_votes = []
    
    if parallel:
        # Run all board members in parallel
        with ThreadPoolExecutor(max_workers=len(BOARD_MEMBERS)) as executor:
            futures = {
                executor.submit(get_board_vote, client, mid, minfo, topics): mid
                for mid, minfo in BOARD_MEMBERS.items()
            }
            
            for future in as_completed(futures):
                member_id = futures[future]
                try:
                    votes = future.result()
                    all_votes.append(votes)
                    print(f"   ✓ {votes['member_name']} voted")
                except Exception as e:
                    print(f"   ✗ {member_id} failed: {e}")
    else:
        # Run sequentially
        for member_id, member_info in BOARD_MEMBERS.items():
            print(f"   Consulting {member_info['name']}...")
            votes = get_board_vote(client, member_id, member_info, topics)
            all_votes.append(votes)
            print(f"   ✓ {votes['member_name']} voted")
    
    # Calculate weighted scores
    topic_scores = {i: {'weighted_sum': 0, 'total_weight': 0, 'votes': []} 
                    for i in range(len(topics))}
    
    for vote_set in all_votes:
        if 'error' in vote_set:
            continue
        weight = vote_set['weight']
        for vote in vote_set.get('votes', []):
            idx = vote['topic_index'] - 1  # Convert to 0-indexed
            if 0 <= idx < len(topics):
                topic_scores[idx]['weighted_sum'] += vote['score'] * weight
                topic_scores[idx]['total_weight'] += weight
                topic_scores[idx]['votes'].append({
                    'member': vote_set['member_name'],
                    'score': vote['score'],
                    'rationale': vote['rationale']
                })
    
    # Calculate final scores
    rankings = []
    for idx, scores in topic_scores.items():
        if scores['total_weight'] > 0:
            final_score = scores['weighted_sum'] / scores['total_weight']
        else:
            final_score = 0
        
        rankings.append({
            'rank': 0,  # Will be set after sorting
            'topic': topics[idx]['topic'],
            'weighted_score': round(final_score, 2),
            'vote_count': len(scores['votes']),
            'votes': scores['votes'],
            'original_topic': topics[idx]
        })
    
    # Sort by weighted score
    rankings.sort(key=lambda x: x['weighted_score'], reverse=True)
    for i, r in enumerate(rankings):
        r['rank'] = i + 1
    
    # Identify consensus and dissent
    top_pick = rankings[0] if rankings else None
    
    # Check for unanimous top pick
    top_pick_votes = [v for v in all_votes if v.get('top_pick') == 1]
    consensus = len(top_pick_votes) == len(all_votes)
    
    # Find any strong dissent (score < 5 from any member)
    dissenting_views = []
    if top_pick:
        for vote in top_pick['votes']:
            if vote['score'] < 5:
                dissenting_views.append(vote)
    
    result = {
        'rankings': rankings,
        'top_pick': top_pick,
        'consensus': consensus,
        'dissenting_views': dissenting_views,
        'all_votes': all_votes,
        'board_size': len(BOARD_MEMBERS)
    }
    
    # Print summary
    print("\n" + "-"*70)
    print("📊 VOTING RESULTS")
    print("-"*70)
    for r in rankings:
        print(f"\n   #{r['rank']} [{r['weighted_score']}/10] {r['topic']}")
        # Show vote breakdown
        vote_summary = ", ".join([f"{v['member'].split()[-1]}:{v['score']}" for v in r['votes'][:3]])
        print(f"      Votes: {vote_summary}...")
    
    if consensus:
        print(f"\n   ✅ UNANIMOUS: All board members agree on #{rankings[0]['rank']}")
    elif dissenting_views:
        print(f"\n   ⚠️  DISSENT: {len(dissenting_views)} member(s) scored top pick below 5")
    
    return result


def format_board_report(result: dict) -> str:
    """Format the board's decision as a readable report."""
    
    report = []
    report.append("# Editorial Board Decision\n")
    report.append(f"**Board Size:** {result['board_size']} members\n")
    report.append(f"**Consensus:** {'Yes ✅' if result['consensus'] else 'No (split vote)'}\n")
    
    report.append("\n## Final Rankings\n")
    for r in result['rankings']:
        report.append(f"### #{r['rank']}: {r['topic']}")
        report.append(f"**Weighted Score:** {r['weighted_score']}/10\n")
        report.append("**Board Feedback:**\n")
        for vote in r['votes']:
            report.append(f"- **{vote['member']}** ({vote['score']}/10): {vote['rationale']}\n")
        report.append("\n")
    
    if result['dissenting_views']:
        report.append("## Dissenting Views on Top Pick\n")
        for dv in result['dissenting_views']:
            report.append(f"- **{dv['member']}**: {dv['rationale']}\n")
    
    return "\n".join(report)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Run editorial board on topics from content_queue.json or environment."""
    
    client = anthropic.Anthropic()
    
    # Load topics
    topics_json = os.environ.get('TOPICS', '')
    if topics_json:
        topics = json.loads(topics_json)
    elif os.path.exists('content_queue.json'):
        with open('content_queue.json') as f:
            queue = json.load(f)
            topics = queue.get('topics', [])
    else:
        print("No topics found. Run topic_scout.py first.")
        return
    
    if not topics:
        print("No topics to evaluate.")
        return
    
    # Run the board
    result = run_editorial_board(client, topics, parallel=True)
    
    # Save results
    with open('board_decision.json', 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    # Save readable report
    report = format_board_report(result)
    with open('board_report.md', 'w') as f:
        f.write(report)
    
    print(f"\n📝 Saved decision to board_decision.json")
    print(f"📝 Saved report to board_report.md")
    
    # Set outputs for GitHub Actions
    if os.environ.get('GITHUB_OUTPUT') and result['top_pick']:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"winner={result['top_pick']['topic']}\n")
            f.write(f"score={result['top_pick']['weighted_score']}\n")
            f.write(f"consensus={str(result['consensus']).lower()}\n")


if __name__ == "__main__":
    main()
