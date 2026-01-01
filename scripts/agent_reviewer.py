#!/usr/bin/env python3
"""
Automated Agent Reviewer

Implements automated quality review for agent outputs based on 
AGENT_QUALITY_STANDARDS.md. This reviewer runs after each agent 
completes to validate output before it proceeds to the next stage.

Inspired by: Nick Tune's automated code review approach
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any
import yaml


class AgentReviewer:
    """Automated reviewer that validates agent outputs against quality standards"""
    
    def __init__(self, standards_file: str = None):
        if standards_file is None:
            script_dir = Path(__file__).parent.parent
            standards_file = script_dir / "docs" / "conventions" / "AGENT_QUALITY_STANDARDS.md"
        
        self.standards_file = Path(standards_file)
        self.load_standards()
    
    def load_standards(self):
        """Load quality standards from documentation"""
        # For now, hardcode standards. Future: parse from markdown
        
        self.banned_openings = [
            r"in today's (fast-paced )?world",
            r"it'?s no secret that",
            r"when it comes to",
            r"in recent years",
            r"amidst the .+ surrounding",
            r"as .+ continues to evolve",
        ]
        
        self.banned_phrases = [
            r"game-changer",
            r"paradigm shift",
            r"revolutionary",
            r"leverage\s+\w+",  # leverage as verb
            r"it could be argued that",
            r"some might say",
            r"at the end of the day",
        ]
        
        self.banned_closings = [
            r"in conclusion",
            r"to conclude",
            r"in summary",
            r"only time will tell",
            r"remains to be seen",
            r"will depend largely on",
            r"whether .+ becomes",
        ]
    
    def review_research_output(self, research_data: Dict) -> Tuple[bool, List[str]]:
        """Review Research Agent output"""
        issues = []
        
        # Check 1: Required fields present
        required_fields = ['headline_stat', 'data_points']
        for field in required_fields:
            if field not in research_data:
                issues.append(f"CRITICAL: Missing required field '{field}'")
        
        # Check 2: Headline stat structure
        if 'headline_stat' in research_data:
            hs = research_data['headline_stat']
            if not isinstance(hs, dict):
                issues.append("CRITICAL: headline_stat must be an object")
            else:
                if 'source' not in hs or not hs['source']:
                    issues.append("CRITICAL: headline_stat missing named source")
                if 'verified' not in hs:
                    issues.append("CRITICAL: headline_stat missing verification flag")
        
        # Check 3: Data points verification rate
        if 'data_points' in research_data:
            data_points = research_data['data_points']
            if isinstance(data_points, list) and len(data_points) > 0:
                verified_count = sum(1 for dp in data_points if dp.get('verified', False))
                verification_rate = verified_count / len(data_points)
                
                if verification_rate < 0.90:
                    issues.append(
                        f"WARNING: Verification rate {verification_rate:.0%} "
                        f"below 90% threshold"
                    )
                
                # Check for unnamed sources
                for i, dp in enumerate(data_points):
                    if 'source' not in dp or not dp['source']:
                        issues.append(f"CRITICAL: Data point {i+1} missing named source")
                    elif dp['source'].lower() in ['studies show', 'research indicates', 'experts say']:
                        issues.append(f"BANNED: Data point {i+1} uses generic source '{dp['source']}'")
        
        # Check 4: Chart data completeness (if present)
        if 'chart_data' in research_data and research_data['chart_data']:
            chart = research_data['chart_data']
            required_chart_fields = ['title', 'data']
            for field in required_chart_fields:
                if field not in chart:
                    issues.append(f"CRITICAL: Chart missing required field '{field}'")
        
        return len(issues) == 0, issues
    
    def review_writer_output(self, article_content: str, chart_filename: str = None) -> Tuple[bool, List[str]]:
        """Review Writer Agent output"""
        issues = []
        
        # Extract front matter
        fm_match = re.match(r'^---\n(.*?)\n---', article_content, re.DOTALL)
        if not fm_match:
            issues.append("CRITICAL: No YAML front matter found")
            return False, issues
        
        # Parse front matter
        try:
            front_matter = yaml.safe_load(fm_match.group(1))
        except yaml.YAMLError as e:
            issues.append(f"CRITICAL: Invalid YAML front matter: {e}")
            return False, issues
        
        # Check 1: Required front matter fields
        required_fields = ['layout', 'title', 'date', 'categories']
        for field in required_fields:
            if field not in front_matter:
                issues.append(f"CRITICAL: Missing required front matter field '{field}'")
        
        # Check 2: Title specificity (must be substantial)
        if 'title' in front_matter:
            title = front_matter['title']
            if len(title.split()) < 4:
                issues.append(f"WARNING: Title too short (≥4 words expected): '{title}'")
            
            # Check for generic titles
            generic_patterns = ['myth vs reality', 'ultimate guide', 'everything you need']
            title_lower = title.lower()
            for pattern in generic_patterns:
                if pattern in title_lower:
                    issues.append(f"WARNING: Generic title pattern detected: '{pattern}'")
        
        # Check 3: Categories field (must be array with ≥1 item)
        if 'categories' in front_matter:
            categories = front_matter['categories']
            if not isinstance(categories, list):
                issues.append("CRITICAL: categories must be an array")
            elif len(categories) == 0:
                issues.append("CRITICAL: categories array is empty (need ≥1)")
        
        # Extract body content
        body = article_content.split('---', 2)[2].strip() if article_content.count('---') >= 2 else ""
        
        # Check 4: Banned opening patterns
        first_para = body.split('\n\n')[0] if body else ""
        for pattern in self.banned_openings:
            if re.search(pattern, first_para, re.IGNORECASE):
                issues.append(f"BANNED: Opening contains forbidden pattern: '{pattern}'")
        
        # Check 5: Banned phrases in body
        for pattern in self.banned_phrases:
            matches = re.findall(pattern, body, re.IGNORECASE)
            if matches:
                issues.append(f"BANNED: Body contains forbidden phrase: '{matches[0]}'")
        
        # Check 6: Banned closing patterns
        last_paras = '\n\n'.join(body.split('\n\n')[-3:]) if body else ""
        for pattern in self.banned_closings:
            if re.search(pattern, last_paras, re.IGNORECASE):
                issues.append(f"BANNED: Ending contains forbidden pattern: '{pattern}'")
        
        # Check 7: Verification flags (must be removed)
        if '[NEEDS SOURCE]' in body or '[UNVERIFIED]' in body:
            issues.append("CRITICAL: Verification flags still present in body")
        
        # Check 8: Chart embedding (if chart provided)
        if chart_filename:
            if f'![' not in body or chart_filename not in body:
                issues.append(f"CRITICAL: Chart not embedded (expected '{chart_filename}')")
            
            # Check for chart reference in text
            chart_refs = ['as the chart shows', 'the chart illustrates', 'shown in the chart']
            has_ref = any(ref in body.lower() for ref in chart_refs)
            if not has_ref:
                issues.append("WARNING: Chart embedded but not referenced in text")
        
        # Check 9: Readability (word count)
        word_count = len(body.split())
        if word_count < 800:
            issues.append(f"WARNING: Article too short ({word_count} words, ≥800 expected)")
        elif word_count > 1500:
            issues.append(f"WARNING: Article too long ({word_count} words, ≤1500 expected)")
        
        return len(issues) == 0, issues
    
    def review_editor_output(self, edited_article: str) -> Tuple[bool, List[str]]:
        """Review Editor Agent output"""
        issues = []
        
        # Extract body
        body = edited_article.split('---', 2)[2].strip() if edited_article.count('---') >= 2 else ""
        
        # Check 1: Verification flags MUST be gone
        if '[NEEDS SOURCE]' in body or '[UNVERIFIED]' in body:
            issues.append("CRITICAL: Editor failed to remove verification flags")
        
        # Check 2: Banned patterns still present?
        for pattern in self.banned_openings + self.banned_phrases + self.banned_closings:
            if re.search(pattern, body, re.IGNORECASE):
                issues.append(f"CRITICAL: Editor failed to remove banned pattern: '{pattern}'")
        
        return len(issues) == 0, issues
    
    def review_graphics_output(self, chart_spec: Dict) -> Tuple[bool, List[str]]:
        """Review Graphics Agent output (chart spec before generation)"""
        issues = []
        
        # Check 1: Required fields
        required_fields = ['title', 'data']
        for field in required_fields:
            if field not in chart_spec:
                issues.append(f"CRITICAL: Chart spec missing '{field}'")
        
        # Check 2: Title length
        if 'title' in chart_spec:
            title = chart_spec['title']
            if len(title) > 50:
                issues.append(f"WARNING: Chart title too long ({len(title)} chars, ≤50 expected)")
        
        # Check 3: Data points
        if 'data' in chart_spec:
            data = chart_spec['data']
            if isinstance(data, list):
                if len(data) < 3:
                    issues.append("WARNING: Chart has <3 data points (may not be useful)")
        
        # Check 4: Source line present
        if 'source_line' not in chart_spec:
            issues.append("WARNING: Chart missing source attribution line")
        
        return len(issues) == 0, issues
    
    def generate_review_report(self, agent_name: str, is_valid: bool, issues: List[str]) -> str:
        """Generate formatted review report"""
        status = "✅ PASSED" if is_valid else "❌ FAILED"
        
        report = [
            f"\n{'='*60}",
            f"AUTOMATED REVIEW: {agent_name}",
            f"{'='*60}",
            f"Status: {status}",
            f"Issues Found: {len(issues)}",
        ]
        
        if issues:
            report.append("\nISSUES:")
            for i, issue in enumerate(issues, 1):
                severity = "CRITICAL" if "CRITICAL" in issue else \
                          "BANNED" if "BANNED" in issue else "WARNING"
                report.append(f"  [{severity}] {issue}")
        else:
            report.append("\n  No issues detected - output meets quality standards")
        
        report.append(f"{'='*60}\n")
        
        return "\n".join(report)


def review_agent_output(agent_name: str, output: Any, context: Dict = None) -> Tuple[bool, List[str]]:
    """
    Main entry point for automated agent review.
    
    Args:
        agent_name: Name of agent that produced output (research_agent, writer_agent, etc)
        output: The agent's output (dict for research, string for writer, etc)
        context: Additional context (e.g., chart_filename for writer)
    
    Returns:
        (is_valid, issues_list)
    """
    reviewer = AgentReviewer()
    context = context or {}
    
    if agent_name == "research_agent":
        is_valid, issues = reviewer.review_research_output(output)
    elif agent_name == "writer_agent":
        chart_filename = context.get('chart_filename')
        is_valid, issues = reviewer.review_writer_output(output, chart_filename)
    elif agent_name == "editor_agent":
        is_valid, issues = reviewer.review_editor_output(output)
    elif agent_name == "graphics_agent":
        is_valid, issues = reviewer.review_graphics_output(output)
    else:
        return False, [f"Unknown agent type: {agent_name}"]
    
    # Print report
    report = reviewer.generate_review_report(agent_name, is_valid, issues)
    print(report)
    
    return is_valid, issues


if __name__ == "__main__":
    # Test the reviewer with sample outputs
    
    # Test 1: Research Agent output
    print("Testing Research Agent Review:")
    research_output = {
        "headline_stat": {
            "value": "80%",
            "source": "Tricentis Research",
            "year": "2024",
            "verified": True
        },
        "data_points": [
            {"stat": "50%", "source": "Gartner", "year": "2024", "verified": True},
            {"stat": "30%", "source": "Unknown", "year": "2024", "verified": False}
        ]
    }
    review_agent_output("research_agent", research_output)
    
    # Test 2: Writer Agent output (with issues)
    print("\nTesting Writer Agent Review (with issues):")
    writer_output_bad = """---
layout: post
title: "Testing"
date: 2026-01-01
---

In today's fast-paced world of software testing, we see many challenges.

This is a game-changer for the industry. [NEEDS SOURCE]

In conclusion, testing is important.
"""
    review_agent_output("writer_agent", writer_output_bad)
    
    # Test 3: Writer Agent output (good)
    print("\nTesting Writer Agent Review (good):")
    writer_output_good = """---
layout: post
title: "Self-Healing Tests: The 80% Maintenance Gap"
date: 2026-01-01
categories: [quality-engineering, test-automation]
---

Self-healing tests promise an 80% cut in maintenance costs. According to 
Tricentis Research, only 10% of companies achieve it.

The gap reveals a fundamental misunderstanding of what "self-healing" means. 
Teams expect magic; vendors deliver incremental improvements.

Companies that invest in robust test infrastructure will outpace competitors. 
Those that chase AI magic bullets will bleed talent and ship slower.
"""
    review_agent_output("writer_agent", writer_output_good)
