#!/usr/bin/env python3
"""
Generate Sample Metrics Data

Creates realistic historical metrics for demonstration.
Simulates 5 runs with varying quality scores and agent performance.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


def generate_sample_data():
    """Generate sample historical data"""

    skills_dir = Path(__file__).parent.parent / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Generate quality history
    quality_history = {
        "version": "1.0",
        "created": (datetime.now() - timedelta(days=30)).isoformat(),
        "runs": [],
    }

    base_score = 92
    for i in range(6):
        date = datetime.now() - timedelta(days=30 - i * 5)
        # Gradually improving scores
        score = base_score + i * 1.5 + random.uniform(-1, 1)

        quality_history["runs"].append(
            {
                "timestamp": date.isoformat(),
                "quality_score": round(score),
                "grade": "A+" if score >= 95 else "A",
                "color": "brightgreen" if score >= 95 else "green",
                "components": {
                    "test_coverage": round(90 + i * 0.8 + random.uniform(-1, 1), 1),
                    "test_pass_rate": 100.0,
                    "documentation": 100.0,
                    "code_style": round(96 + i * 0.4 + random.uniform(-1, 1), 1),
                },
            }
        )

    # Calculate trend
    scores = [r["quality_score"] for r in quality_history["runs"]]
    recent = sum(scores[-3:]) / 3
    older = sum(scores[:-3]) / len(scores[:-3])
    diff = recent - older
    quality_history["trend"] = f"improving ⬆️ (+{diff:.1f} points)"

    # Save quality history
    with open(skills_dir / "quality_history.json", "w") as f:
        json.dump(quality_history, f, indent=2)

    print(f"✅ Generated quality_history.json with {len(quality_history['runs'])} runs")
    print(f"   Trend: {quality_history['trend']}")

    # Generate agent metrics
    agent_metrics = {
        "version": "1.0",
        "created": (datetime.now() - timedelta(days=30)).isoformat(),
        "runs": [],
        "summary": {
            "total_runs": 0,
            "agents": {
                "research_agent": {},
                "writer_agent": {},
                "editor_agent": {},
                "graphics_agent": {},
            },
        },
    }

    for i in range(6):
        date = datetime.now() - timedelta(days=30 - i * 5)

        # Research agent - improving verification rate
        verification_rate = 75 + i * 4 + random.uniform(-2, 2)

        # Writer agent - occasional banned phrase initially
        banned_phrases = 1 if i < 2 else 0

        # Editor agent - improving gate pass rate
        gates_passed = 3 + i if i < 5 else 5
        gates_failed = 5 - gates_passed

        # Graphics agent - occasional violations
        zone_violations = 1 if i < 3 and random.random() < 0.3 else 0

        agent_metrics["runs"].append(
            {
                "timestamp": date.isoformat(),
                "agents": {
                    "research_agent": {
                        "data_points": 10,
                        "verified": round(10 * verification_rate / 100),
                        "unverified": round(10 * (100 - verification_rate) / 100),
                        "verification_rate": round(verification_rate, 1),
                        "sources": ["Gartner 2024", "TestGuild Survey"],
                        "prediction": "High verification rate (>80%)",
                        "actual": "Pass"
                        if verification_rate >= 80
                        else "Needs improvement",
                    },
                    "writer_agent": {
                        "word_count": 1100 + random.randint(-100, 200),
                        "banned_phrases": banned_phrases,
                        "validation_passed": banned_phrases == 0,
                        "regenerations": 1 if banned_phrases > 0 else 0,
                        "chart_embedded": True,
                        "prediction": "Clean draft (0 banned phrases, chart embedded)",
                        "actual": "Pass"
                        if banned_phrases == 0
                        else "Needs improvement",
                    },
                    "editor_agent": {
                        "gates_passed": gates_passed,
                        "gates_failed": gates_failed,
                        "gate_pass_rate": round(gates_passed / 5 * 100, 1),
                        "edits_made": 10 + random.randint(-5, 5),
                        "quality_issues": []
                        if gates_failed == 0
                        else ["Style", "Structure"],
                        "prediction": "All gates pass (5/5)",
                        "actual": "Pass"
                        if gates_failed == 0
                        else f"Failed {gates_failed} gates",
                    },
                    "graphics_agent": {
                        "charts_generated": 1,
                        "visual_qa_passed": 1 if zone_violations == 0 else 0,
                        "visual_qa_pass_rate": 100.0 if zone_violations == 0 else 0.0,
                        "zone_violations": zone_violations,
                        "regenerations": 1 if zone_violations > 0 else 0,
                        "prediction": "Pass Visual QA (100%)",
                        "actual": "Pass"
                        if zone_violations == 0
                        else f"{zone_violations} violations",
                    },
                },
                "summary": {
                    "agents_tracked": 4,
                    "agents_successful": sum(
                        [
                            1 if verification_rate >= 80 else 0,
                            1 if banned_phrases == 0 else 0,
                            1 if gates_failed == 0 else 0,
                            1 if zone_violations == 0 else 0,
                        ]
                    ),
                    "success_rate": 0,  # Will be calculated
                },
            }
        )

        agent_metrics["runs"][-1]["summary"]["success_rate"] = round(
            agent_metrics["runs"][-1]["summary"]["agents_successful"] / 4 * 100, 1
        )

    agent_metrics["summary"]["total_runs"] = len(agent_metrics["runs"])

    # Calculate per-agent summaries
    agent_metrics["summary"]["agents"]["research_agent"] = {
        "total_runs": 6,
        "avg_verification_rate": round(
            sum(
                r["agents"]["research_agent"]["verification_rate"]
                for r in agent_metrics["runs"]
            )
            / 6,
            1,
        ),
        "trend": "improving ⬆️",
    }

    agent_metrics["summary"]["agents"]["writer_agent"] = {
        "total_runs": 6,
        "clean_draft_rate": round(
            sum(
                1
                for r in agent_metrics["runs"]
                if r["agents"]["writer_agent"]["banned_phrases"] == 0
            )
            / 6
            * 100,
            1,
        ),
        "avg_regenerations": round(
            sum(
                r["agents"]["writer_agent"]["regenerations"]
                for r in agent_metrics["runs"]
            )
            / 6,
            1,
        ),
    }

    agent_metrics["summary"]["agents"]["editor_agent"] = {
        "total_runs": 6,
        "avg_gate_pass_rate": round(
            sum(
                r["agents"]["editor_agent"]["gate_pass_rate"]
                for r in agent_metrics["runs"]
            )
            / 6,
            1,
        ),
        "trend": "improving ⬆️",
    }

    agent_metrics["summary"]["agents"]["graphics_agent"] = {
        "total_runs": 6,
        "avg_qa_pass_rate": round(
            sum(
                r["agents"]["graphics_agent"]["visual_qa_pass_rate"]
                for r in agent_metrics["runs"]
            )
            / 6,
            1,
        ),
        "avg_violations": round(
            sum(
                r["agents"]["graphics_agent"]["zone_violations"]
                for r in agent_metrics["runs"]
            )
            / 6,
            1,
        ),
    }

    # Save agent metrics
    with open(skills_dir / "agent_metrics.json", "w") as f:
        json.dump(agent_metrics, f, indent=2)

    print(f"✅ Generated agent_metrics.json with {len(agent_metrics['runs'])} runs")
    print("\nAgent Performance Summary:")
    print(
        f"  Research Agent: {agent_metrics['summary']['agents']['research_agent']['avg_verification_rate']}% verification"
    )
    print(
        f"  Writer Agent: {agent_metrics['summary']['agents']['writer_agent']['clean_draft_rate']}% clean drafts"
    )
    print(
        f"  Editor Agent: {agent_metrics['summary']['agents']['editor_agent']['avg_gate_pass_rate']}% gate pass rate"
    )
    print(
        f"  Graphics Agent: {agent_metrics['summary']['agents']['graphics_agent']['avg_qa_pass_rate']}% QA pass rate"
    )


if __name__ == "__main__":
    generate_sample_data()
    print("\n🎉 Sample data generated! Run metrics_dashboard.py to visualize.")
