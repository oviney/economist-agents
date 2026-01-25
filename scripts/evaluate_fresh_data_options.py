#!/usr/bin/env python3
"""
Evaluate Fresh Data Integration Options

Uses our Research Agent to analyze and recommend the best approach
for enabling research beyond LLM training data cutoffs.

Usage:
    python scripts/evaluate_fresh_data_options.py
"""

import logging
from pathlib import Path

try:
    import orjson as json
except ImportError:
    import json

from llm_client import create_llm_client, call_llm

logger = logging.getLogger(__name__)

# Load the research brief as context
RESEARCH_BRIEF_PATH = Path(__file__).parent.parent / "docs/research/FRESH_DATA_OPTIONS_BRIEF.md"

ANALYST_PROMPT = """You are a Senior Solutions Architect evaluating technology options for an AI agent system.

Your task is to analyze the provided research brief and recommend the best approach for enabling
fresh data access (beyond LLM training cutoffs) in our CrewAI-based agentic workflow.

CURRENT SYSTEM:
- Framework: CrewAI with OpenAI GPT-4o
- Existing integrations: arXiv API (custom tool), ChromaDB RAG
- Use case: Economist-style research articles requiring cutting-edge data

EVALUATION CRITERIA (in order of importance):
1. Speed to production (we need fresh data NOW)
2. Maintenance burden (we're a small team)
3. Future-proofing (industry standards matter)
4. Risk (we can't break production)

OUTPUT FORMAT (JSON):
{
  "recommended_option": "Option X: [Name]",
  "confidence": "high|medium|low",
  "rationale": "2-3 sentence summary of why",
  "implementation_steps": [
    {"step": 1, "action": "...", "effort": "X story points"},
    {"step": 2, "action": "...", "effort": "X story points"}
  ],
  "quick_win": "Single action we can do TODAY to get fresh web data",
  "risks": ["Risk 1", "Risk 2"],
  "alternatives_considered": [
    {"option": "Option Y", "why_not": "Reason"}
  ]
}

Be decisive. We need actionable guidance, not analysis paralysis."""


def load_research_brief() -> str:
    """Load the research brief document."""
    if not RESEARCH_BRIEF_PATH.exists():
        raise FileNotFoundError(f"Research brief not found: {RESEARCH_BRIEF_PATH}")
    return RESEARCH_BRIEF_PATH.read_text()


def evaluate_options() -> dict:
    """Run the evaluation using our LLM client."""
    print("🔍 Loading research brief...")
    research_brief = load_research_brief()

    print("🤖 Creating LLM client...")
    client = create_llm_client()

    user_prompt = f"""Analyze this research brief and provide your recommendation:

---
{research_brief}
---

Based on this analysis, what should we do? Provide your recommendation in JSON format."""

    print("📊 Evaluating options with AI analyst...")
    response = call_llm(client, ANALYST_PROMPT, user_prompt, max_tokens=2000)

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


def format_recommendation(rec: dict) -> str:
    """Format the recommendation for display."""
    output = []
    output.append("\n" + "=" * 70)
    output.append("🎯 FRESH DATA INTEGRATION RECOMMENDATION")
    output.append("=" * 70)

    if "recommended_option" in rec:
        output.append(f"\n✅ RECOMMENDATION: {rec['recommended_option']}")
        output.append(f"   Confidence: {rec.get('confidence', 'N/A').upper()}")
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
    logging.basicConfig(level=logging.INFO)

    print("\n🚀 Fresh Data Options Evaluator")
    print("   Using AI to analyze best approach for real-time research\n")

    recommendation = evaluate_options()
    print(format_recommendation(recommendation))

    # Save recommendation
    output_path = Path(__file__).parent.parent / "docs/research/RECOMMENDATION.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(json.dumps(recommendation, option=json.OPT_INDENT_2))

    print(f"\n💾 Full recommendation saved to: {output_path}")


if __name__ == "__main__":
    main()
