#!/usr/bin/env python3
"""
Skills Gap Analyzer - Agent Performance as Team Skills Indicator

Maps agent defect patterns to human role skill levels (Junior/Mid/Senior)
for data-driven hiring and training recommendations.

Usage:
    python3 scripts/skills_gap_analyzer.py --report
    python3 scripts/skills_gap_analyzer.py --format markdown > team_skills.md
    python3 scripts/skills_gap_analyzer.py --role writer_agent
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class SkillsGapAnalyzer:
    """Analyze agent performance to identify team skills gaps"""

    # Agent → Human Role mapping
    ROLE_MAPPING = {
        "writer_agent": "Content Writer",
        "research_agent": "Research Analyst",
        "editor_agent": "Senior Editor",
        "graphics_agent": "Data Visualization Designer",
        "governance_tracker": "QA Lead",
        "featured_image_agent": "Visual Designer",
        "quality_enforcer": "DevOps Engineer",
    }

    # Velocity impact constants
    # 1 bug fix ≈ 0.5 story points based on average team velocity (10 pts/sprint, ~20 tasks)
    STORY_POINTS_PER_FIX_DAY: float = 0.5
    # Industry average for medium-severity bugs; used when no historical TTR data exists
    DEFAULT_BUG_RESOLUTION_DAYS: float = 2.0
    # 2-week sprints with capacity for ~4 bugs before quality work crowds out features
    MAX_BUGS_PER_SPRINT: float = 4.0
    # Minimum bug sample required for statistically reliable correlation patterns
    MIN_BUGS_FOR_STATISTICAL_CONFIDENCE: int = 20

    # Velocity risk thresholds (days of lost sprint capacity)
    # 10 days ≈ one full sprint lost; 5 days ≈ half sprint; 2 days ≈ quarter sprint
    VELOCITY_RISK_CRITICAL: float = 10.0
    VELOCITY_RISK_HIGH: float = 5.0
    VELOCITY_RISK_MEDIUM: float = 2.0

    # Quality grade thresholds (skill score 0-100)
    # Aligned with standard performance-review benchmarks used in engineering orgs
    GRADE_A_THRESHOLD: float = 85.0  # High performer: strong signal, few defects
    GRADE_B_THRESHOLD: float = 70.0  # Above average: occasional gaps
    GRADE_C_THRESHOLD: float = 55.0  # Average: notable gaps needing attention
    GRADE_D_THRESHOLD: float = 40.0  # Below average: systematic issues

    # Correlation strength thresholds (skill gap % = 100 - skill_score)
    # A gap ≥50 % means the agent is performing at half capacity → strong defect correlation
    STRONG_CORRELATION_GAP: float = 50.0
    # A gap ≥25 % represents a material skills deficit → moderate correlation
    MODERATE_CORRELATION_GAP: float = 25.0

    # Skills rubric: Role → {skill: {junior: X, mid: Y, senior: Z}}
    SKILLS_RUBRIC = {
        "Content Writer": {
            "requirements_adherence": {
                "junior": 50,  # % compliance with requirements
                "mid": 75,
                "senior": 95,
                "weight": 0.4,  # Importance weight
            },
            "cms_knowledge": {
                "junior": 40,  # % correct usage (Jekyll, frontmatter, etc)
                "mid": 70,
                "senior": 95,
                "weight": 0.3,
            },
            "style_compliance": {
                "junior": 60,  # % adherence to Economist style
                "mid": 85,
                "senior": 98,
                "weight": 0.3,
            },
        },
        "Research Analyst": {
            "source_verification": {
                "junior": 60,  # % of claims verified with sources
                "mid": 80,
                "senior": 95,
                "weight": 0.5,
            },
            "data_accuracy": {
                "junior": 70,  # % of data points accurate
                "mid": 85,
                "senior": 98,
                "weight": 0.3,
            },
            "citation_quality": {
                "junior": 50,  # % proper citation format
                "mid": 75,
                "senior": 95,
                "weight": 0.2,
            },
        },
        "Senior Editor": {
            "quality_gate_enforcement": {
                "junior": 70,  # % of issues caught
                "mid": 85,
                "senior": 95,
                "weight": 0.4,
            },
            "style_review": {
                "junior": 60,  # % style violations caught
                "mid": 80,
                "senior": 95,
                "weight": 0.3,
            },
            "structural_review": {
                "junior": 65,  # % structural issues caught
                "mid": 80,
                "senior": 95,
                "weight": 0.3,
            },
        },
        "Data Visualization Designer": {
            "visual_accuracy": {
                "junior": 70,  # % charts without zone violations
                "mid": 85,
                "senior": 98,
                "weight": 0.4,
            },
            "design_compliance": {
                "junior": 65,  # % adherence to style guide
                "mid": 80,
                "senior": 95,
                "weight": 0.3,
            },
            "technical_execution": {
                "junior": 70,  # % correct implementation
                "mid": 85,
                "senior": 95,
                "weight": 0.3,
            },
        },
    }

    def __init__(self, tracker_file: str = "skills/defect_tracker.json"):
        """Initialize analyzer with defect tracker data"""
        self.tracker_file = Path(tracker_file)
        self.tracker_data = self._load_tracker()
        self.bugs = self.tracker_data.get("bugs", [])

    def _load_tracker(self) -> dict[str, Any]:
        """Load defect tracker JSON"""
        if not self.tracker_file.exists():
            raise FileNotFoundError(f"Defect tracker not found: {self.tracker_file}")

        with open(self.tracker_file) as f:
            return json.load(f)

    def analyze_agent_performance(self, agent_name: str) -> dict[str, Any]:
        """
        Analyze performance for a specific agent

        Returns:
            {
                'role': 'Content Writer',
                'bugs_count': 3,
                'critical_bugs': 1,
                'skill_scores': {'requirements_adherence': 45, ...},
                'overall_score': 42,
                'skill_level': 'junior',
                'top_gap': 'requirements_adherence',
                'recommendation': 'Prompt engineering + Training'
            }
        """
        # Get bugs for this agent
        agent_bugs = [
            b
            for b in self.bugs
            if b.get("responsible_agent") == agent_name
            or b.get("component") == agent_name
        ]

        if not agent_bugs:
            return {
                "role": self.ROLE_MAPPING.get(agent_name, agent_name),
                "bugs_count": 0,
                "critical_bugs": 0,
                "skill_scores": {},
                "overall_score": 100,
                "skill_level": "senior",
                "top_gap": "None",
                "recommendation": "Maintain current level",
            }

        role = self.ROLE_MAPPING.get(agent_name, agent_name)
        rubric = self.SKILLS_RUBRIC.get(role, {})

        # Count critical bugs
        critical_bugs = sum(1 for b in agent_bugs if b.get("severity") == "critical")

        # Calculate skill scores based on bug patterns
        skill_scores = self._calculate_skill_scores(agent_name, agent_bugs, rubric)

        # Calculate overall score (weighted average)
        if skill_scores and rubric:
            overall_score = sum(
                score * rubric[skill]["weight"]
                for skill, score in skill_scores.items()
                if skill in rubric
            )
        else:
            # Default scoring: penalize by bug count
            base_score = 100
            penalty = len(agent_bugs) * 15  # 15 points per bug
            critical_penalty = critical_bugs * 20  # Additional 20 for critical
            overall_score = max(0, base_score - penalty - critical_penalty)

        # Determine skill level
        skill_level = self._determine_skill_level(overall_score)

        # Identify top gap
        top_gap = self._identify_top_gap(skill_scores) if skill_scores else "None"

        # Generate recommendation
        recommendation = self._generate_recommendation(
            agent_name, skill_level, len(agent_bugs), critical_bugs
        )

        return {
            "role": role,
            "bugs_count": len(agent_bugs),
            "critical_bugs": critical_bugs,
            "skill_scores": skill_scores,
            "overall_score": round(overall_score, 1),
            "skill_level": skill_level,
            "top_gap": top_gap,
            "recommendation": recommendation,
        }

    def _calculate_skill_scores(
        self, agent_name: str, bugs: list[dict], rubric: dict
    ) -> dict[str, float]:
        """Calculate individual skill scores based on bug patterns"""
        if not rubric:
            return {}

        skill_scores = {}

        for skill_name, _skill_def in rubric.items():
            # Start at senior level (100)
            score = 100.0

            # Penalize based on relevant bugs
            for bug in bugs:
                penalty = self._calculate_skill_penalty(bug, skill_name, agent_name)
                score -= penalty

            # Ensure score stays in valid range
            skill_scores[skill_name] = max(0, min(100, score))

        return skill_scores

    def _calculate_skill_penalty(
        self, bug: dict, skill_name: str, agent_name: str
    ) -> float:
        """Calculate penalty for a specific skill based on bug characteristics"""
        base_penalty = 10.0

        # Severity multiplier
        severity_multipliers = {
            "critical": 2.0,
            "high": 1.5,
            "medium": 1.0,
            "low": 0.5,
        }
        severity = bug.get("severity", "medium")
        multiplier = severity_multipliers.get(severity, 1.0)

        # Skill-specific penalties based on root cause
        root_cause = bug.get("root_cause", "")

        if skill_name == "requirements_adherence":
            if root_cause in ["requirements_gap", "prompt_engineering"]:
                return base_penalty * multiplier * 1.5
            if "embed" in bug.get("description", "").lower():
                return base_penalty * multiplier

        elif skill_name == "cms_knowledge":
            if "jekyll" in bug.get("component", "").lower():
                return base_penalty * multiplier * 2.0
            if "frontmatter" in bug.get("description", "").lower():
                return base_penalty * multiplier * 1.5

        elif skill_name == "style_compliance":
            if root_cause == "prompt_engineering":
                return base_penalty * multiplier * 1.3

        elif skill_name == "source_verification":
            if "verification" in bug.get("description", "").lower():
                return base_penalty * multiplier * 2.0

        elif skill_name == "quality_gate_enforcement":
            if root_cause == "validation_gap":
                return base_penalty * multiplier * 1.5

        elif skill_name == "visual_accuracy":
            if "zone" in bug.get("description", "").lower():
                return base_penalty * multiplier * 2.0

        # Default penalty if bug impacts this agent
        return base_penalty * multiplier * 0.5

    def _determine_skill_level(self, overall_score: float) -> str:
        """Determine skill level based on overall score"""
        if overall_score >= 85:
            return "senior"
        elif overall_score >= 65:
            return "mid"
        else:
            return "junior"

    def _identify_top_gap(self, skill_scores: dict[str, float]) -> str:
        """Identify the skill with the lowest score"""
        if not skill_scores:
            return "None"
        return min(skill_scores.items(), key=lambda x: x[1])[0]

    def _generate_recommendation(
        self, agent_name: str, skill_level: str, bug_count: int, critical_bugs: int
    ) -> str:
        """Generate actionable recommendation based on analysis"""
        if skill_level == "senior" and bug_count == 0:
            return "Maintain current level"

        if critical_bugs > 0:
            urgency = "🔴 URGENT: "
        elif bug_count >= 3:
            urgency = "🟡 CONSIDER: "
        else:
            urgency = ""

        # Recommendations based on skill level and agent type
        if skill_level == "junior":
            if agent_name == "writer_agent":  # noqa: SIM116
                return f"{urgency}Prompt engineering + CMS training"
            elif agent_name == "research_agent":
                return f"{urgency}Source verification workshop"
            elif agent_name == "editor_agent":
                return f"{urgency}Quality gate training"
            elif agent_name == "graphics_agent":
                return f"{urgency}Visual design training"
            else:
                return f"{urgency}Skill development required"

        elif skill_level == "mid":
            return f"Prompt refinement + {bug_count} bug patterns to address"

        return "Minor improvements needed"

    def generate_team_assessment(self) -> dict[str, Any]:
        """
        Generate complete team skills assessment

        Returns:
            {
                'by_role': {agent: analysis, ...},
                'hiring_recommendations': [...],
                'training_priorities': [...],
                'summary': {...}
            }
        """
        # Analyze all agents with bugs
        agents = set()
        for bug in self.bugs:
            if bug.get("responsible_agent"):
                agents.add(bug.get("responsible_agent"))
            elif bug.get("component"):
                # Map component to agent if possible
                component = bug.get("component")
                if component in self.ROLE_MAPPING or component in [
                    "writer_agent",
                    "research_agent",
                    "editor_agent",
                    "graphics_agent",
                ]:
                    agents.add(component)

        by_role = {}
        for agent in sorted(agents):
            by_role[agent] = self.analyze_agent_performance(agent)

        # Generate hiring recommendations
        hiring_recs = self._generate_hiring_recommendations(by_role)

        # Generate training priorities
        training_priorities = self._generate_training_priorities(by_role)

        # Summary statistics
        summary = {
            "total_agents_analyzed": len(by_role),
            "total_bugs": len(self.bugs),
            "critical_bugs": sum(
                1 for b in self.bugs if b.get("severity") == "critical"
            ),
            "avg_skill_level": self._calculate_avg_skill_level(by_role),
            "roles_needing_attention": sum(
                1 for a in by_role.values() if a["skill_level"] == "junior"
            ),
        }

        # Velocity/quality correlation (Critical Question #5)
        velocity_impact = self.calculate_velocity_impact()
        quality_correlation = self.correlate_skills_with_quality()

        return {
            "by_role": by_role,
            "hiring_recommendations": hiring_recs,
            "training_priorities": training_priorities,
            "velocity_impact": velocity_impact,
            "quality_correlation": quality_correlation,
            "summary": summary,
            "generated_at": datetime.now().isoformat(),
        }

    def _generate_hiring_recommendations(
        self, by_role: dict[str, dict]
    ) -> list[dict[str, Any]]:
        """Generate hiring recommendations based on skills analysis"""
        recommendations = []

        for _agent, analysis in by_role.items():
            if analysis["skill_level"] == "junior" and analysis["critical_bugs"] > 0:
                recommendations.append(
                    {
                        "priority": "URGENT",
                        "role": analysis["role"],
                        "reason": f"{analysis['critical_bugs']} critical bugs, {analysis['bugs_count']} total",
                        "current_level": "junior",
                        "target_level": "mid-senior",
                    }
                )
            elif (
                analysis["skill_level"] == "junior" or analysis["skill_level"] == "mid"
            ) and analysis["bugs_count"] >= 3:
                recommendations.append(
                    {
                        "priority": "CONSIDER",
                        "role": analysis["role"],
                        "reason": f"{analysis['bugs_count']} bugs, score {analysis['overall_score']}/100",
                        "current_level": analysis["skill_level"],
                        "target_level": "senior",
                    }
                )

        return sorted(recommendations, key=lambda x: x["priority"])

    def _generate_training_priorities(
        self, by_role: dict[str, dict]
    ) -> list[dict[str, Any]]:
        """Generate training priorities ranked by impact"""
        priorities = []

        for agent, analysis in by_role.items():
            if analysis["top_gap"] != "None" and analysis["bugs_count"] > 0:
                impact_score = analysis["bugs_count"] * (
                    2 if analysis["critical_bugs"] > 0 else 1
                )

                priorities.append(
                    {
                        "role": analysis["role"],
                        "skill_gap": analysis["top_gap"],
                        "current_score": analysis["skill_scores"].get(
                            analysis["top_gap"], 0
                        ),
                        "target_score": 85,  # Mid-senior level
                        "impact_score": impact_score,
                        "training_type": self._suggest_training_type(
                            agent, analysis["top_gap"]
                        ),
                    }
                )

        return sorted(priorities, key=lambda x: x["impact_score"], reverse=True)

    def _suggest_training_type(self, agent: str, skill_gap: str) -> str:
        """Suggest specific training type for skill gap"""
        training_map = {
            "requirements_adherence": "Requirements Analysis Workshop",
            "cms_knowledge": "Jekyll/CMS Deep Dive",
            "style_compliance": "Economist Style Guide Training",
            "source_verification": "Source Verification Best Practices",
            "quality_gate_enforcement": "Quality Gate Implementation",
            "visual_accuracy": "Visual Design Standards Workshop",
        }
        return training_map.get(skill_gap, "General Skills Development")

    def _calculate_avg_skill_level(self, by_role: dict[str, dict]) -> str:
        """Calculate average skill level across all roles"""
        if not by_role:
            return "N/A"

        scores = [a["overall_score"] for a in by_role.values()]
        avg_score = sum(scores) / len(scores)

        return self._determine_skill_level(avg_score)

    def calculate_velocity_impact(self) -> dict[str, Any]:
        """
        Calculate how skills gaps impact team velocity.

        Uses bug resolution time and severity as proxies for lost sprint capacity.
        Higher skill gaps → more bugs → more rework → lower effective velocity.

        Returns:
            {
                'by_role': {
                    agent: {
                        'role': str,
                        'velocity_loss_days': float,
                        'rework_cost_points': float,
                        'open_bugs': int,
                        'avg_resolution_days': float,
                        'velocity_risk': str  # 'low', 'medium', 'high', 'critical'
                    }
                },
                'total_velocity_loss_days': float,
                'total_rework_cost_points': float,
                'highest_impact_role': str,
            }
        """
        severity_weights = {"critical": 3.0, "high": 2.0, "medium": 1.0, "low": 0.5}

        agents: set[str] = set()
        for bug in self.bugs:
            agent = bug.get("responsible_agent") or bug.get("component")
            if agent and agent in self.ROLE_MAPPING:
                agents.add(agent)

        by_role: dict[str, Any] = {}
        for agent in sorted(agents):
            agent_bugs = [
                b
                for b in self.bugs
                if b.get("responsible_agent") == agent or b.get("component") == agent
            ]

            open_bugs = [b for b in agent_bugs if b.get("status") == "open"]
            fixed_bugs = [
                b for b in agent_bugs if b.get("time_to_resolve_days") is not None
            ]

            # Average resolution time from historical fixed bugs
            avg_resolution = (
                sum(b["time_to_resolve_days"] for b in fixed_bugs) / len(fixed_bugs)
                if fixed_bugs
                else self.DEFAULT_BUG_RESOLUTION_DAYS
            )

            # Velocity loss = sum of (severity_weight * estimated_fix_days) for open bugs
            velocity_loss = sum(
                severity_weights.get(b.get("severity", "medium"), 1.0) * avg_resolution
                for b in open_bugs
            )

            # Rework cost in story points
            rework_points = round(velocity_loss * self.STORY_POINTS_PER_FIX_DAY, 1)

            # Velocity risk level
            if velocity_loss >= self.VELOCITY_RISK_CRITICAL:
                risk = "critical"
            elif velocity_loss >= self.VELOCITY_RISK_HIGH:
                risk = "high"
            elif velocity_loss >= self.VELOCITY_RISK_MEDIUM:
                risk = "medium"
            else:
                risk = "low"

            by_role[agent] = {
                "role": self.ROLE_MAPPING[agent],
                "velocity_loss_days": round(velocity_loss, 1),
                "rework_cost_points": rework_points,
                "open_bugs": len(open_bugs),
                "avg_resolution_days": round(avg_resolution, 1),
                "velocity_risk": risk,
            }

        total_velocity_loss = sum(r["velocity_loss_days"] for r in by_role.values())
        total_rework_points = sum(r["rework_cost_points"] for r in by_role.values())
        highest_impact = (
            max(by_role.items(), key=lambda x: x[1]["velocity_loss_days"])[1]["role"]
            if by_role
            else "N/A"
        )

        return {
            "by_role": by_role,
            "total_velocity_loss_days": round(total_velocity_loss, 1),
            "total_rework_cost_points": round(total_rework_points, 1),
            "highest_impact_role": highest_impact,
        }

    def correlate_skills_with_quality(self) -> dict[str, Any]:
        """
        Correlate skill gap scores with quality output metrics.

        Answers: "How do skills gaps correlate with team velocity/quality?"

        Returns:
            {
                'correlations': [
                    {
                        'agent': str,
                        'role': str,
                        'skill_score': float,       # 0-100
                        'defect_rate': float,        # bugs per sprint (estimated)
                        'fix_rate': float,           # % bugs fixed
                        'quality_grade': str,        # A/B/C/D/F
                        'correlation_label': str     # 'strong', 'moderate', 'weak'
                    }
                ],
                'insight': str,   # human-readable summary
                'data_quality': str,  # 'sufficient' | 'limited' (< 20 bugs)
            }
        """
        agents: set[str] = set()
        for bug in self.bugs:
            agent = bug.get("responsible_agent") or bug.get("component")
            if agent and agent in self.ROLE_MAPPING:
                agents.add(agent)

        correlations = []
        for agent in sorted(agents):
            agent_bugs = [
                b
                for b in self.bugs
                if b.get("responsible_agent") == agent or b.get("component") == agent
            ]

            if not agent_bugs:
                continue

            # Get skill score
            analysis = self.analyze_agent_performance(agent)
            skill_score = analysis["overall_score"]

            # Quality metrics
            total = len(agent_bugs)
            fixed = sum(1 for b in agent_bugs if b.get("status") == "fixed")
            fix_rate = round(fixed / total * 100, 1) if total else 0.0

            # Defect rate: bugs per sprint normalised to MAX_BUGS_PER_SPRINT capacity
            defect_rate = round(total / self.MAX_BUGS_PER_SPRINT, 2)

            # Quality grade: based on skill score (standard engineering performance benchmarks)
            if skill_score >= self.GRADE_A_THRESHOLD:
                grade = "A"
            elif skill_score >= self.GRADE_B_THRESHOLD:
                grade = "B"
            elif skill_score >= self.GRADE_C_THRESHOLD:
                grade = "C"
            elif skill_score >= self.GRADE_D_THRESHOLD:
                grade = "D"
            else:
                grade = "F"

            # Correlation strength: inverse relationship between skill gap and defect rate
            gap = 100 - skill_score
            if gap >= self.STRONG_CORRELATION_GAP:
                label = "strong"  # large gap → many defects
            elif gap >= self.MODERATE_CORRELATION_GAP:
                label = "moderate"
            else:
                label = "weak"  # small gap → few defects

            correlations.append(
                {
                    "agent": agent,
                    "role": self.ROLE_MAPPING[agent],
                    "skill_score": skill_score,
                    "defect_rate": defect_rate,
                    "fix_rate": fix_rate,
                    "quality_grade": grade,
                    "correlation_label": label,
                }
            )

        # Sort by skill_score ascending (worst first)
        correlations.sort(key=lambda x: x["skill_score"])

        # Generate insight summary
        data_quality = (
            "sufficient"
            if len(self.bugs) >= self.MIN_BUGS_FOR_STATISTICAL_CONFIDENCE
            else "limited"
        )
        if correlations:
            worst = correlations[0]
            insight = (
                f"{worst['role']} shows the strongest skills-quality correlation "
                f"(skill score {worst['skill_score']}/100, defect rate "
                f"{worst['defect_rate']:.1f}x per sprint). "
                f"{'Sufficient' if data_quality == 'sufficient' else 'Limited'} "
                f"data ({len(self.bugs)} bugs) for pattern analysis."
            )
        else:
            insight = "No agent-attributed bugs found. Assign 'responsible_agent' to defects for analysis."

        return {
            "correlations": correlations,
            "insight": insight,
            "data_quality": data_quality,
        }

    def format_team_assessment_table(
        self, assessment: dict[str, Any], format: str = "markdown"
    ) -> str:
        """Format team assessment as table for executive reporting"""
        if format == "markdown":
            return self._format_markdown_table(assessment)
        elif format == "text":
            return self._format_text_table(assessment)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_markdown_table(self, assessment: dict[str, Any]) -> str:
        """Format as markdown table"""
        lines = ["# 👥 Team Skills Assessment\n"]

        # Summary
        summary = assessment["summary"]
        lines.append("## Executive Summary\n")
        lines.append(f"- **Total Agents Analyzed**: {summary['total_agents_analyzed']}")
        lines.append(
            f"- **Total Bugs**: {summary['total_bugs']} ({summary['critical_bugs']} critical)"
        )
        lines.append(f"- **Average Skill Level**: {summary['avg_skill_level'].title()}")
        lines.append(
            f"- **Roles Needing Attention**: {summary['roles_needing_attention']}\n"
        )

        # By Role Performance table
        lines.append("## By Role Performance\n")
        lines.append("| Role | Skill Level | Score | Bugs | Top Gap | Recommendation |")
        lines.append("|------|------------|-------|------|---------|----------------|")

        by_role = assessment["by_role"]
        for agent in sorted(by_role.keys()):
            analysis = by_role[agent]
            level_display = (
                f"{analysis['skill_level'].title()} ({analysis['overall_score']}/100)"
            )
            bugs_display = (
                f"{analysis['bugs_count']} ({analysis['critical_bugs']} critical)"
            )
            top_gap = analysis["top_gap"].replace("_", " ").title()

            lines.append(
                f"| {analysis['role']} | {level_display} | "
                f"{analysis['overall_score']}/100 | {bugs_display} | "
                f"{top_gap} | {analysis['recommendation']} |"
            )

        # Hiring Recommendations
        lines.append("\n## Hiring Recommendations\n")
        hiring_recs = assessment["hiring_recommendations"]
        if hiring_recs:
            for rec in hiring_recs:
                icon = "🔴" if rec["priority"] == "URGENT" else "🟡"
                lines.append(
                    f"{icon} **{rec['priority']}**: {rec['role']} "
                    f"(current: {rec['current_level']}, target: {rec['target_level']}) - {rec['reason']}"
                )
        else:
            lines.append("✅ No urgent hiring needs identified")

        # Training Priorities
        lines.append("\n## Training Priorities\n")
        training = assessment["training_priorities"]
        if training:
            for i, priority in enumerate(training, 1):
                skill_gap = priority["skill_gap"].replace("_", " ").title()
                lines.append(
                    f"{i}. **{priority['role']}** - {skill_gap} "
                    f"(current: {priority['current_score']:.0f}/100, target: {priority['target_score']}/100)"
                )
                lines.append(f"   - Training: {priority['training_type']}")
                lines.append(f"   - Impact Score: {priority['impact_score']}\n")
        else:
            lines.append("✅ No critical training gaps identified")

        # Velocity Impact (Critical Question #5)
        velocity = assessment.get("velocity_impact", {})
        if velocity:
            lines.append("\n## Velocity Impact\n")
            lines.append(
                f"- **Total Estimated Velocity Loss**: {velocity['total_velocity_loss_days']} days"
            )
            lines.append(
                f"- **Total Rework Cost**: {velocity['total_rework_cost_points']} story points"
            )
            lines.append(
                f"- **Highest Impact Role**: {velocity['highest_impact_role']}\n"
            )
            vel_by_role = velocity.get("by_role", {})
            if vel_by_role:
                lines.append(
                    "| Role | Risk | Open Bugs | Velocity Loss (days) | Rework (pts) |"
                )
                lines.append(
                    "|------|------|-----------|---------------------|--------------|"
                )
                risk_icons = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢",
                }
                for agent in sorted(vel_by_role.keys()):
                    row = vel_by_role[agent]
                    icon = risk_icons.get(row["velocity_risk"], "")
                    lines.append(
                        f"| {row['role']} | {icon} {row['velocity_risk'].title()} | "
                        f"{row['open_bugs']} | {row['velocity_loss_days']} | "
                        f"{row['rework_cost_points']} |"
                    )

        # Quality Correlation (Critical Question #5)
        quality_corr = assessment.get("quality_correlation", {})
        if quality_corr:
            lines.append("\n## Skills-Quality Correlation\n")
            lines.append(f"*{quality_corr.get('insight', '')}*\n")
            data_quality = quality_corr.get("data_quality", "limited")
            lines.append(
                f"**Data Quality**: {data_quality.title()} "
                f"({'≥20' if data_quality == 'sufficient' else '<20'} bugs)\n"
            )
            corrs = quality_corr.get("correlations", [])
            if corrs:
                lines.append(
                    "| Role | Skill Score | Quality Grade | Defect Rate | Fix Rate | Correlation |"
                )
                lines.append(
                    "|------|------------|--------------|-------------|----------|-------------|"
                )
                for c in corrs:
                    lines.append(
                        f"| {c['role']} | {c['skill_score']}/100 | {c['quality_grade']} | "
                        f"{c['defect_rate']:.2f}x/sprint | {c['fix_rate']}% | "
                        f"{c['correlation_label'].title()} |"
                    )

        # Timestamp
        lines.append(f"\n---\n*Generated: {assessment['generated_at']}*")

        return "\n".join(lines)

    def _format_text_table(self, assessment: dict[str, Any]) -> str:
        """Format as plain text table"""
        lines = ["=" * 80]
        lines.append("TEAM SKILLS ASSESSMENT")
        lines.append("=" * 80)

        summary = assessment["summary"]
        lines.append(f"\nTotal Agents: {summary['total_agents_analyzed']}")
        lines.append(
            f"Total Bugs: {summary['total_bugs']} ({summary['critical_bugs']} critical)"
        )
        lines.append(f"Average Skill Level: {summary['avg_skill_level'].upper()}")
        lines.append(f"Roles Needing Attention: {summary['roles_needing_attention']}")

        lines.append("\n" + "-" * 80)
        lines.append("BY ROLE PERFORMANCE")
        lines.append("-" * 80)

        by_role = assessment["by_role"]
        for agent in sorted(by_role.keys()):
            analysis = by_role[agent]
            lines.append(f"\n{analysis['role'].upper()}")
            lines.append(
                f"  Skill Level: {analysis['skill_level'].upper()} ({analysis['overall_score']}/100)"
            )
            lines.append(
                f"  Bugs: {analysis['bugs_count']} total, {analysis['critical_bugs']} critical"
            )
            lines.append(f"  Top Gap: {analysis['top_gap'].replace('_', ' ').title()}")
            lines.append(f"  Recommendation: {analysis['recommendation']}")

        lines.append("\n" + "-" * 80)
        lines.append("HIRING RECOMMENDATIONS")
        lines.append("-" * 80)

        hiring_recs = assessment["hiring_recommendations"]
        if hiring_recs:
            for rec in hiring_recs:
                lines.append(f"\n[{rec['priority']}] {rec['role']}")
                lines.append(
                    f"  Current: {rec['current_level']}, Target: {rec['target_level']}"
                )
                lines.append(f"  Reason: {rec['reason']}")
        else:
            lines.append("\nNo urgent hiring needs identified")

        lines.append("\n" + "-" * 80)
        lines.append("TRAINING PRIORITIES")
        lines.append("-" * 80)

        training = assessment["training_priorities"]
        if training:
            for i, priority in enumerate(training, 1):
                lines.append(
                    f"\n{i}. {priority['role']} - {priority['skill_gap'].replace('_', ' ').title()}"
                )
                lines.append(
                    f"   Score: {priority['current_score']:.0f}/100 → {priority['target_score']}/100"
                )
                lines.append(f"   Training: {priority['training_type']}")
                lines.append(f"   Impact: {priority['impact_score']}")
        else:
            lines.append("\nNo critical training gaps identified")

        # Velocity Impact (Critical Question #5)
        velocity = assessment.get("velocity_impact", {})
        if velocity:
            lines.append("\n" + "-" * 80)
            lines.append("VELOCITY IMPACT")
            lines.append("-" * 80)
            lines.append(
                f"\nTotal Velocity Loss: {velocity['total_velocity_loss_days']} days"
            )
            lines.append(
                f"Total Rework Cost: {velocity['total_rework_cost_points']} story points"
            )
            lines.append(f"Highest Impact Role: {velocity['highest_impact_role']}")
            for agent in sorted(velocity.get("by_role", {}).keys()):
                row = velocity["by_role"][agent]
                lines.append(f"\n  {row['role'].upper()}")
                lines.append(f"    Risk: {row['velocity_risk'].upper()}")
                lines.append(f"    Open Bugs: {row['open_bugs']}")
                lines.append(f"    Velocity Loss: {row['velocity_loss_days']} days")
                lines.append(f"    Rework Cost: {row['rework_cost_points']} points")

        # Quality Correlation (Critical Question #5)
        quality_corr = assessment.get("quality_correlation", {})
        if quality_corr:
            lines.append("\n" + "-" * 80)
            lines.append("SKILLS-QUALITY CORRELATION")
            lines.append("-" * 80)
            lines.append(f"\nInsight: {quality_corr.get('insight', '')}")
            lines.append(
                f"Data Quality: {quality_corr.get('data_quality', 'limited').upper()}"
            )
            for c in quality_corr.get("correlations", []):
                lines.append(f"\n  {c['role'].upper()}")
                lines.append(
                    f"    Skill Score: {c['skill_score']}/100  Grade: {c['quality_grade']}"
                )
                lines.append(
                    f"    Defect Rate: {c['defect_rate']:.2f}x/sprint  Fix Rate: {c['fix_rate']}%"
                )
                lines.append(f"    Correlation: {c['correlation_label'].upper()}")

        lines.append("\n" + "=" * 80)
        lines.append(f"Generated: {assessment['generated_at']}")
        lines.append("=" * 80)

        return "\n".join(lines)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Analyze agent performance as team skills gaps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate full report
  python3 scripts/skills_gap_analyzer.py --report

  # Export as markdown
  python3 scripts/skills_gap_analyzer.py --format markdown > team_skills.md

  # Analyze specific role
  python3 scripts/skills_gap_analyzer.py --role writer_agent

  # Export as JSON
  python3 scripts/skills_gap_analyzer.py --json > assessment.json
        """,
    )
    parser.add_argument(
        "--tracker",
        default="skills/defect_tracker.json",
        help="Path to defect tracker JSON file",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate full team assessment report",
    )
    parser.add_argument(
        "--role",
        help="Analyze specific agent role (e.g., writer_agent)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "text"],
        default="markdown",
        help="Output format for report",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON data",
    )

    args = parser.parse_args()

    analyzer = SkillsGapAnalyzer(args.tracker)

    if args.role:
        # Analyze specific role
        analysis = analyzer.analyze_agent_performance(args.role)
        print(json.dumps(analysis, indent=2))

    elif args.json:
        # Output raw JSON
        assessment = analyzer.generate_team_assessment()
        print(json.dumps(assessment, indent=2))

    elif args.report:
        # Generate formatted report
        assessment = analyzer.generate_team_assessment()
        report = analyzer.format_team_assessment_table(assessment, format=args.format)
        print(report)

    else:
        # Default: Show help
        parser.print_help()


if __name__ == "__main__":
    main()
