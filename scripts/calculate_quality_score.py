#!/usr/bin/env python3
"""
Quality Score Calculator

Calculates project quality score based on:
- Test Coverage (40%)
- Test Pass Rate (30%)
- Documentation (20%)
- Code Style (10%)

Formula: (Coverage×0.4 + Pass Rate×0.3 + Docs×0.2 + Style×0.1) × 100

Target: 90%+ quality score

Historical Tracking:
- Appends each run to skills/quality_history.json
- Tracks trend over time (improving/stable/declining)
- Enables quality dashboard visualization
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path


def get_test_coverage():
    """Calculate test coverage percentage"""
    # For now, estimate based on test count vs. code files
    # In future, integrate pytest-cov

    test_dir = Path(__file__).parent.parent / "tests"
    scripts_dir = Path(__file__).parent

    test_files = list(test_dir.glob("*.py"))
    script_files = list(scripts_dir.glob("*.py"))

    # Count test assertions as proxy for coverage
    test_count = 0
    for test_file in test_files:
        with open(test_file) as f:
            test_count += f.read().count("assert ")

    # Rough estimate: 10 assertions per 100 lines = good coverage
    # Current: 11 tests with ~50 assertions
    coverage_estimate = min(95, (test_count / 50) * 100)  # Cap at 95%

    return coverage_estimate


def get_test_pass_rate():
    """Calculate test pass rate percentage"""
    try:
        # Run pytest and capture results
        result = subprocess.run(
            ["python3", "tests/test_quality_system.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        output = result.stdout + result.stderr

        # Parse test results
        if "11/11 tests passed" in output or "Total: 11/11" in output:
            return 100.0
        elif "tests passed" in output:
            # Extract pass rate from output
            import re

            match = re.search(r"(\d+)/(\d+) tests passed", output)
            if match:
                passed, total = int(match.group(1)), int(match.group(2))
                return (passed / total) * 100

        return 0.0
    except Exception as e:
        print(f"   ⚠️  Could not run tests: {e}")
        return 0.0


def get_documentation_score():
    """Calculate documentation completeness percentage"""
    docs_dir = Path(__file__).parent.parent / "docs"

    # Required documentation files
    required_docs = [
        "CHANGELOG.md",
        "CHART_DESIGN_SPEC.md",
        "JEKYLL_EXPERTISE.md",
        "SKILLS_LEARNING.md",
    ]

    # Check existence and completeness
    score = 0
    for doc in required_docs:
        doc_path = docs_dir / doc
        if doc_path.exists():
            # Check if substantial (>1KB)
            size = doc_path.stat().st_size
            if size > 1000:
                score += 25  # Each doc worth 25%
            else:
                score += 10  # Minimal doc worth 10%

    # Check README exists and is substantial
    readme_path = Path(__file__).parent.parent / "README.md"
    if readme_path.exists() and readme_path.stat().st_size > 2000:
        score = min(100, score + 10)  # Bonus for good README

    return min(100, score)


def get_code_style_score():
    """Calculate code style compliance percentage"""
    # Check for common style issues

    scripts_dir = Path(__file__).parent
    python_files = list(scripts_dir.glob("*.py"))

    total_checks = 0
    passed_checks = 0

    for py_file in python_files:
        with open(py_file) as f:
            content = f.read()
            lines = content.split("\n")

            total_checks += 1
            # Check: Has docstring
            if '"""' in content[:500] or "'''" in content[:500]:
                passed_checks += 1

            total_checks += 1
            # Check: Not too many long lines (>120 chars)
            long_lines = sum(1 for line in lines if len(line) > 120)
            if long_lines < len(lines) * 0.1:  # Less than 10% long lines
                passed_checks += 1

            total_checks += 1
            # Check: Has proper imports organization
            if "import " in content[:1000]:
                passed_checks += 1

    return (passed_checks / total_checks * 100) if total_checks > 0 else 100


def calculate_quality_score():
    """Calculate overall quality score"""

    print("\n" + "=" * 70)
    print("QUALITY SCORE CALCULATION")
    print("=" * 70)

    # Gather metrics
    print("\n📊 Gathering metrics...\n")

    coverage = get_test_coverage()
    print(f"   Test Coverage:     {coverage:.1f}%")

    pass_rate = get_test_pass_rate()
    print(f"   Test Pass Rate:    {pass_rate:.1f}%")

    docs = get_documentation_score()
    print(f"   Documentation:     {docs:.1f}%")

    style = get_code_style_score()
    print(f"   Code Style:        {style:.1f}%")

    # Calculate weighted score
    quality_score = coverage * 0.4 + pass_rate * 0.3 + docs * 0.2 + style * 0.1

    print("\n" + "-" * 70)
    print(f"\n🏆 QUALITY SCORE: {quality_score:.0f}/100")
    print("\n   Formula: (Coverage×0.4 + Pass Rate×0.3 + Docs×0.2 + Style×0.1) × 100")
    print("\n   Target: 90%+")

    # Grade
    if quality_score >= 95:
        grade = "A+"
        color = "brightgreen"
    elif quality_score >= 90:
        grade = "A"
        color = "green"
    elif quality_score >= 85:
        grade = "B+"
        color = "yellowgreen"
    elif quality_score >= 80:
        grade = "B"
        color = "yellow"
    else:
        grade = "C"
        color = "orange"

    print(f"   Grade: {grade}")
    print("\n" + "=" * 70 + "\n")

    score_data = {
        "quality_score": round(quality_score),
        "grade": grade,
        "color": color,
        "components": {
            "test_coverage": round(coverage, 1),
            "test_pass_rate": round(pass_rate, 1),
            "documentation": round(docs, 1),
            "code_style": round(style, 1),
        },
    }

    # Save to history
    save_to_history(score_data)

    return score_data


def save_to_history(score_data):
    """Save quality score to historical log"""
    history_file = Path(__file__).parent.parent / "skills" / "quality_history.json"

    # Load existing history
    if history_file.exists():
        with open(history_file) as f:
            history = json.load(f)
    else:
        history = {"version": "1.0", "created": datetime.now().isoformat(), "runs": []}

    # Add current run
    run_data = {"timestamp": datetime.now().isoformat(), **score_data}
    history["runs"].append(run_data)

    # Calculate trend
    if len(history["runs"]) >= 2:
        scores = [r["quality_score"] for r in history["runs"]]
        trend = calculate_trend(scores)
        history["trend"] = trend
        print(f"\n📈 Quality Trend: {trend}")

    # Save history
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)

    print(f"   Saved to {history_file.name} (Run #{len(history['runs'])})")


def calculate_trend(scores):
    """Calculate trend from score history"""
    if len(scores) < 3:
        return "stable ➡️ (need more runs)"

    # Compare recent scores to older scores
    recent = sum(scores[-3:]) / 3
    older = sum(scores[:-3]) / len(scores[:-3]) if len(scores) > 3 else scores[0]

    diff = recent - older
    if diff > 2:
        return f"improving ⬆️ (+{diff:.1f} points)"
    elif diff < -2:
        return f"declining ⬇️ ({diff:.1f} points)"
    else:
        return "stable ➡️"


def export_badge_json(score_data):
    """Export badge data for shields.io"""
    badge_file = Path(__file__).parent.parent / "quality_score.json"

    with open(badge_file, "w") as f:
        json.dump(
            {
                "schemaVersion": 1,
                "label": "quality",
                "message": f"{score_data['quality_score']}/100",
                "color": score_data["color"],
            },
            f,
            indent=2,
        )

    print(f"✅ Badge data exported to {badge_file.name}")
    print("   Use: https://img.shields.io/endpoint?url=...")


if __name__ == "__main__":
    score_data = calculate_quality_score()
    export_badge_json(score_data)
