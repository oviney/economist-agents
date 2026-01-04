#!/usr/bin/env python3
"""
Test Stage 4 Crew - Review and Final Editorial Polish

Stage 4 represents the final review and editorial refinement stage.
It ingests YAML/JSON output from Stage 3 and applies additional quality checks.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crews.stage4_crew import Stage4Crew


def test_stage4_crew_initialization():
    """Test Stage4Crew can be instantiated"""
    crew = Stage4Crew()
    assert crew is not None
    assert hasattr(crew, "kickoff")


def test_stage4_ingests_stage3_output():
    """
    CRITICAL: Stage 4 must successfully consume YAML/JSON output from Stage 3

    Stage 3 outputs:
    {
        "article": "---\ntitle: ...\ndate: ...\n---\n\nArticle content...",
        "chart_data": {...}
    }
    """
    # Simulate Stage 3 output
    stage3_output = {
        "article": """---
title: "Test Article"
date: 2026-01-04
category: quality-engineering
---

This is a test article with proper Economist style.
The data shows clear trends.""",
        "chart_data": {
            "title": "Test Chart",
            "data": [{"year": 2023, "value": 10}, {"year": 2024, "value": 20}],
        },
    }

    crew = Stage4Crew()
    result = crew.kickoff(stage3_input=stage3_output)

    # Verify structure
    assert isinstance(result, dict)
    assert "article" in result
    assert "editorial_score" in result
    assert "gates_passed" in result


def test_stage4_editorial_quality_gates():
    """Test Stage 4 applies >95% gate pass rate requirement"""
    stage3_output = {
        "article": """---
title: "Quality Engineering Evolution"
date: 2026-01-04
category: quality-engineering
---

The landscape is shifting. Test automation now accounts for 60% of QE budgets, according to Gartner's 2024 report.

Chart data reveals the gap.""",
        "chart_data": {"title": "Budget Trends", "data": []},
    }

    crew = Stage4Crew()
    result = crew.kickoff(stage3_input=stage3_output)

    # Editorial quality gates (5 gates total)
    assert result["gates_passed"] >= 5 * 0.95  # >95% pass rate
    assert result["editorial_score"] >= 95


def test_stage4_output_structure():
    """Test Stage 4 output matches expected format"""
    stage3_output = {
        "article": """---
title: "Test"
date: 2026-01-04
---

Content here.""",
        "chart_data": {},
    }

    crew = Stage4Crew()
    result = crew.kickoff(stage3_input=stage3_output)

    # Required output fields
    assert "article" in result
    assert "editorial_score" in result
    assert "gates_passed" in result
    assert "reviewer_feedback" in result
    assert "publication_ready" in result

    # Article should still be valid YAML frontmatter
    assert result["article"].startswith("---\n")
    assert "title:" in result["article"]


def test_stage4_economist_style_enforcement():
    """Test Stage 4 enforces Economist editorial standards"""
    # Article with style violations
    stage3_output = {
        "article": """---
title: "Test Article"
date: 2026-01-04
---

In today's fast-paced world, testing is a game-changer!

In conclusion, we should leverage these insights.""",
        "chart_data": {},
    }

    crew = Stage4Crew()
    result = crew.kickoff(stage3_input=stage3_output)

    # Should detect style violations
    cleaned_article = result["article"]
    assert "In today's" not in cleaned_article  # Banned opening
    assert "game-changer" not in cleaned_article  # Banned phrase
    assert "In conclusion" not in cleaned_article  # Banned closing
    assert "!" not in cleaned_article  # No exclamation points


if __name__ == "__main__":
    print("Running Stage 4 Crew Tests...")
    print("=" * 70)

    try:
        test_stage4_crew_initialization()
        print("✓ Test 1: Stage4Crew initialization")
    except Exception as e:
        print(f"✗ Test 1 FAILED: {e}")

    try:
        test_stage4_ingests_stage3_output()
        print("✓ Test 2: Stage 3 output ingestion")
    except Exception as e:
        print(f"✗ Test 2 FAILED: {e}")

    try:
        test_stage4_editorial_quality_gates()
        print("✓ Test 3: Editorial quality gates (>95%)")
    except Exception as e:
        print(f"✗ Test 3 FAILED: {e}")

    try:
        test_stage4_output_structure()
        print("✓ Test 4: Output structure validation")
    except Exception as e:
        print(f"✗ Test 4 FAILED: {e}")

    try:
        test_stage4_economist_style_enforcement()
        print("✓ Test 5: Economist style enforcement")
    except Exception as e:
        print(f"✗ Test 5 FAILED: {e}")

    print("=" * 70)
