#!/usr/bin/env python3
"""
Evaluate Architecture Options

Generic script to evaluate research briefs using AI analysis.
Supports multiple topics: fresh-data, infrastructure, or any custom brief.

Usage:
    python scripts/evaluate_architecture_options.py --topic fresh-data
    python scripts/evaluate_architecture_options.py --topic infrastructure
    python scripts/evaluate_architecture_options.py --brief path/to/brief.md
"""

import argparse
import logging
from pathlib import Path
from typing import Any

try:
    import orjson as json
except ImportError:
    import json

from llm_client import create_llm_client, call_llm

logger = logging.getLogger(__name__)

DOCS_DIR = Path(__file__).parent.parent / "docs/research"

BRIEFS = {
    "fresh-data": {
        "path": DOCS_DIR / "FRESH_DATA_OPTIONS_BRIEF.md",
        "title": "Fresh Data Integration",
        "context": "enabling research beyond LLM training data cutoffs",
    },
    "infrastructure": {
        "path": DOCS_DIR / "INFRASTRUCTURE_OPTIONS_BRIEF.md",
        "title": "Infrastructure & Deployment",
        "context": "choosing between GitHub Actions, VPS, or cloud platforms",
    },
}

ANALYST_PROMPT = """You are a Senior Solutions Architect evaluating technology options for an AI agent system.

Your task is to analyze the provided research brief and recommend the best approach.

CURRENT SYSTEM:
- Framework: CrewAI with OpenAI GPT-4o
- Existing integrations: arXiv API (custom tool), ChromaDB RAG
- Use case: Economist-style research articles (on-demand generation)
- Team size: Small (minimize operational burden)

EVALUATION CRITERIA (in order of importance):
1. Speed to production (we need results quickly)
2. Maintenance burden (we're a small team)
3. Cost efficiency (budget-conscious)
4. Future-proofing (industry standards, scalability)
5. Risk (we can't break production)

OUTPUT FORMAT (JSON):
{
  "recommended_option": "Option X: [Name]",
  "confidence": "high|medium|low",
  "rationale": "2-3 sentence summary of why this is the best choice",
  "implementation_steps": [
    {"step": 1, "action": "Specific action", "effort": "X story points"},
    {"step": 2, "action": "Specific action", "effort": "X story points"}
  ],
  "quick_win": "Single action we can do TODAY",
  "estimated_cost": "Monthly cost estimate",
  "risks": ["Risk 1", "Risk 2"],
  "alternatives_considered": [
    {"option": "Option Y", "why_not": "Specific reason"}
  ],
  "decision_reversibility": "easy|moderate|difficult"
}

Be decisive and practical. We need actionable guidance, not analysis paralysis.
Prefer options that can be implemented incrementally."""


def load_research_brief(brief_path: Path) -> str:
    """Load a research brief document."""
    if not brief_path.exists():
        raise FileNotFoundError(f"Research brief not found: {brief_path}")
    return brief_path.read_text()


def evaluate_options(brief_path: Path, title: str) -> dict[str, Any]:
    """Run the evaluation using our LLM client."""
    print(f"🔍 Loading research brief: {title}...")
    research_brief = load_research_brief(brief_path)

    print("🤖 Creating LLM client...")
    client = create_llm_client()

    user_prompt = f"""Analyze this research brief about {title} and provide your recommendation:

---
{research_brief}
---

Based on this analysis, what should we do? Provide your recommendation in JSON format."""

    print("📊 Evaluating options with AI analyst...")
    response = call_llm(client, ANALYST_PROMPT, user_prompt, max_tokens=2500)

    # Parse JSON from response
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            recommendation = json.loads(response[start:end])
        else:
            recommendation = {"raw_response": response}
    except json.JSONDecodeError:
        recommendation = {"raw_response": response}

    return recommendation


def format_recommendation(rec: dict[str, Any], title: str) -> str:
    """Format the recommendation for display."""
    output = []
    output.append("\n" + "=" * 70)
    output.append(f"🎯 {title.upper()} RECOMMENDATION")
    output.append("=" * 70)

    if "recommended_option" in rec:
        output.append(f"\n✅ RECOMMENDATION: {rec['recommended_option']}")
        output.append(f"   Confidence: {rec.get('confidence', 'N/A').upper()}")

        if "estimated_cost" in rec:
            output.append(f"   Est. Cost: {rec['estimated_cost']}")

        if "decision_reversibility" in rec:
            output.append(f"   Reversibility: {rec['decision_reversibility']}")

        output.append(f"\n📝 RATIONALE:\n   {rec.get('rationale', 'N/A')}")

        if "quick_win" in rec:
            output.append(f"\n⚡ QUICK WIN (do today):\n   {rec['quick_win']}")

        if "implementation_steps" in rec:
            output.append("\n📋 IMPLEMENTATION STEPS:")
            for step in rec["implementation_steps"]:
                effort = step.get("effort", "TBD")
                output.append(f"   {step['step']}. {step['action']} [{effort}]")

        if "risks" in rec:
            output.append("\n⚠️  RISKS:")
            for risk in rec["risks"]:
                output.append(f"   • {risk}")

        if "alternatives_considered" in rec:
            output.append("\n🔄 ALTERNATIVES CONSIDERED:")
            for alt in rec["alternatives_considered"]:
                output.append(f"   • {alt['option']}: {alt['why_not']}")
    else:
        output.append("\n📝 RAW RESPONSE:")
        output.append(rec.get("raw_response", str(rec)))

    output.append("\n" + "=" * 70)
    return "\n".join(output)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate architecture options using AI analysis"
    )
    parser.add_argument(
        "--topic",
        choices=list(BRIEFS.keys()),
        help="Predefined topic to evaluate",
    )
    parser.add_argument(
        "--brief",
        type=Path,
        help="Path to custom research brief markdown file",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Evaluate all predefined topics",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.all:
        topics_to_evaluate = list(BRIEFS.keys())
    elif args.brief:
        topics_to_evaluate = [("custom", args.brief)]
    elif args.topic:
        topics_to_evaluate = [args.topic]
    else:
        parser.print_help()
        print("\n📋 Available topics:")
        for topic, info in BRIEFS.items():
            print(f"   --topic {topic}: {info['title']}")
        return

    all_recommendations = {}

    for topic in topics_to_evaluate:
        if isinstance(topic, tuple):
            # Custom brief
            topic_name, brief_path = topic
            title = brief_path.stem.replace("_", " ").title()
        else:
            # Predefined topic
            topic_name = topic
            brief_info = BRIEFS[topic]
            brief_path = brief_info["path"]
            title = brief_info["title"]

        print(f"\n🚀 Architecture Options Evaluator: {title}")
        print(f"   Analyzing: {brief_info.get('context', 'options')}\n")

        recommendation = evaluate_options(brief_path, title)
        all_recommendations[topic_name] = recommendation

        print(format_recommendation(recommendation, title))

        # Save individual recommendation
        output_path = DOCS_DIR / f"RECOMMENDATION_{topic_name.upper()}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(json.dumps(recommendation, option=json.OPT_INDENT_2))

        print(f"💾 Recommendation saved to: {output_path}")

    if len(all_recommendations) > 1:
        # Save combined recommendations
        combined_path = DOCS_DIR / "RECOMMENDATIONS_ALL.json"
        with open(combined_path, "wb") as f:
            f.write(json.dumps(all_recommendations, option=json.OPT_INDENT_2))
        print(f"\n📦 All recommendations saved to: {combined_path}")


if __name__ == "__main__":
    main()
