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

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# ═══════════════════════════════════════════════════════════════════════════
# BOARD MEMBER PERSONAS
# ═══════════════════════════════════════════════════════════════════════════
from agent_loader import load_board_members as _load_board_members

# Import unified LLM client
from llm_client import call_llm, create_llm_client

BOARD_MEMBERS = _load_board_members()


# ═══════════════════════════════════════════════════════════════════════════
# VOTING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


def get_board_vote(client, member_id: str, member_info: dict, topics: list) -> dict:
    """Get a single board member's votes on all topics."""

    # Input validation
    if not topics or not isinstance(topics, list):
        raise ValueError(
            f"[EDITORIAL_BOARD:{member_id}] Invalid topics. Expected non-empty list, "
            f"got: {type(topics).__name__}"
        )

    if len(topics) == 0:
        raise ValueError(f"[EDITORIAL_BOARD:{member_id}] No topics to evaluate")

    topics_text = "\n\n".join(
        [
            f"TOPIC {i + 1}: {t['topic']}\n"
            f"Hook: {t.get('hook', 'N/A')}\n"
            f"Thesis: {t.get('thesis', 'N/A')}\n"
            f"Title ideas: {', '.join(t.get('title_ideas', ['N/A']))}\n"
            f"Data sources: {', '.join(t.get('data_sources', ['Unknown']))}\n"
            f"Contrarian angle: {t.get('contrarian_angle', 'N/A')}"
            for i, t in enumerate(topics)
        ]
    )

    prompt = f"""{member_info["prompt"]}

Here are the topics to evaluate:

{topics_text}

SCORING GUIDANCE - apply these two quality checks when scoring each topic:

1. THESIS QUALITY: Does the topic have a contrarian thesis - a specific, debatable argument - or is it merely a topic description?
   - Penalise topics whose "Thesis" is vague, descriptive, or not a position someone could disagree with.
   - A good thesis: "AI test generators are making maintenance costs worse, not better" (debatable claim).
   - A bad thesis: "AI is changing how teams write tests" (just a topic).

2. TITLE PROVOCATIVENESS: Are the title ideas compelling and free of weak patterns?
   - Penalise titles that start with "Why" or "How" - these telegraph the conclusion and kill curiosity.
   - Penalise titles starting with "The Impact of" or "The Role of" - generic and forgettable.
   - Reward titles with a colon twist that make the reader curious without revealing the answer.

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

    response_text = call_llm(
        client,
        "",  # System prompt embedded in member prompt
        prompt,
        max_tokens=1500,
    )

    # Parse JSON
    try:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        votes = json.loads(response_text[start:end])
        votes["member_id"] = member_id
        votes["member_name"] = member_info["name"]
        votes["weight"] = member_info["weight"]
        return votes
    except (json.JSONDecodeError, ValueError):
        return {
            "member_id": member_id,
            "member_name": member_info["name"],
            "weight": member_info["weight"],
            "votes": [],
            "error": "Failed to parse votes",
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
    print("\n" + "=" * 70)
    print("📋 EDITORIAL BOARD CONVENING")
    print("=" * 70)
    print(
        f"\n   Evaluating {len(topics)} topics with {len(BOARD_MEMBERS)} board members...\n"
    )

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
    topic_scores = {
        i: {"weighted_sum": 0, "total_weight": 0, "votes": []}
        for i in range(len(topics))
    }

    for vote_set in all_votes:
        if "error" in vote_set:
            continue
        weight = vote_set["weight"]
        for vote in vote_set.get("votes", []):
            idx = vote["topic_index"] - 1  # Convert to 0-indexed
            if 0 <= idx < len(topics):
                topic_scores[idx]["weighted_sum"] += vote["score"] * weight
                topic_scores[idx]["total_weight"] += weight
                topic_scores[idx]["votes"].append(
                    {
                        "member": vote_set["member_name"],
                        "score": vote["score"],
                        "rationale": vote["rationale"],
                    }
                )

    # Calculate final scores
    rankings = []
    for idx, scores in topic_scores.items():
        if scores["total_weight"] > 0:
            final_score = scores["weighted_sum"] / scores["total_weight"]
        else:
            final_score = 0

        rankings.append(
            {
                "rank": 0,  # Will be set after sorting
                "topic": topics[idx]["topic"],
                "weighted_score": round(final_score, 2),
                "vote_count": len(scores["votes"]),
                "votes": scores["votes"],
                "original_topic": topics[idx],
            }
        )

    # Sort by weighted score
    rankings.sort(key=lambda x: x["weighted_score"], reverse=True)
    for i, r in enumerate(rankings):
        r["rank"] = i + 1

    # Identify consensus and dissent
    top_pick = rankings[0] if rankings else None

    # Check for unanimous top pick
    top_pick_votes = [v for v in all_votes if v.get("top_pick") == 1]
    consensus = len(top_pick_votes) == len(all_votes)

    # Find any strong dissent (score < 5 from any member)
    dissenting_views = []
    if top_pick:
        for vote in top_pick["votes"]:
            if vote["score"] < 5:
                dissenting_views.append(vote)

    result = {
        "rankings": rankings,
        "top_pick": top_pick,
        "consensus": consensus,
        "dissenting_views": dissenting_views,
        "all_votes": all_votes,
        "board_size": len(BOARD_MEMBERS),
    }

    # Print summary
    print("\n" + "-" * 70)
    print("📊 VOTING RESULTS")
    print("-" * 70)
    for r in rankings:
        print(f"\n   #{r['rank']} [{r['weighted_score']}/10] {r['topic']}")
        # Show vote breakdown
        vote_summary = ", ".join(
            [f"{v['member'].split()[-1]}:{v['score']}" for v in r["votes"][:3]]
        )
        print(f"      Votes: {vote_summary}...")

    if consensus:
        print(f"\n   ✅ UNANIMOUS: All board members agree on #{rankings[0]['rank']}")
    elif dissenting_views:
        print(
            f"\n   ⚠️  DISSENT: {len(dissenting_views)} member(s) scored top pick below 5"
        )

    return result


def format_board_report(result: dict) -> str:
    """Format the board's decision as a readable report."""

    report = []
    report.append("# Editorial Board Decision\n")
    report.append(f"**Board Size:** {result['board_size']} members\n")
    report.append(
        f"**Consensus:** {'Yes ✅' if result['consensus'] else 'No (split vote)'}\n"
    )

    report.append("\n## Final Rankings\n")
    for r in result["rankings"]:
        report.append(f"### #{r['rank']}: {r['topic']}")
        report.append(f"**Weighted Score:** {r['weighted_score']}/10\n")
        report.append("**Board Feedback:**\n")
        for vote in r["votes"]:
            report.append(
                f"- **{vote['member']}** ({vote['score']}/10): {vote['rationale']}\n"
            )
        report.append("\n")

    if result["dissenting_views"]:
        report.append("## Dissenting Views on Top Pick\n")
        for dv in result["dissenting_views"]:
            report.append(f"- **{dv['member']}**: {dv['rationale']}\n")

    return "\n".join(report)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════


def main():
    """Run editorial board on topics from content_queue.json or environment."""

    client = create_llm_client()

    # Load topics
    topics_json = os.environ.get("TOPICS", "")
    if topics_json:
        topics = json.loads(topics_json)
    elif os.path.exists("content_queue.json"):
        with open("content_queue.json") as f:
            queue = json.load(f)
            topics = queue.get("topics", [])
    else:
        print("No topics found. Run topic_scout.py first.")
        return

    if not topics:
        print("No topics to evaluate.")
        return

    # Run the board
    result = run_editorial_board(client, topics, parallel=True)

    # Save results
    with open("board_decision.json", "w") as f:
        json.dump(result, f, indent=2, default=str)

    # Save readable report
    report = format_board_report(result)
    with open("board_report.md", "w") as f:
        f.write(report)

    print("\n📝 Saved decision to board_decision.json")
    print("📝 Saved report to board_report.md")

    # Set outputs for GitHub Actions
    if os.environ.get("GITHUB_OUTPUT") and result["top_pick"]:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"winner={result['top_pick']['topic']}\n")
            f.write(f"score={result['top_pick']['weighted_score']}\n")
            f.write(f"consensus={str(result['consensus']).lower()}\n")


if __name__ == "__main__":
    main()
