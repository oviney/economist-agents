#!/usr/bin/env python3
"""
Skills Manager for Blog QA Agent
Implements Claude-style learning and skill improvement
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class SkillsManager:
    """Manages learned validation patterns and continuous improvement"""
    
    def __init__(self, skills_file: str = None):
        if skills_file is None:
            # Default to skills directory relative to this script
            script_dir = Path(__file__).parent.parent
            skills_file = script_dir / "skills" / "blog_qa_skills.json"
        
        self.skills_file = Path(skills_file)
        self.skills = self._load_skills()
    
    def _load_skills(self) -> Dict[str, Any]:
        """Load existing skills or create new skill set"""
        if self.skills_file.exists():
            with open(self.skills_file, 'r') as f:
                return json.load(f)
        else:
            return self._create_default_skills()
    
    def _create_default_skills(self) -> Dict[str, Any]:
        """Create initial skill set"""
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "skills": {},
            "validation_stats": {
                "total_runs": 0,
                "issues_found": 0,
                "issues_fixed": 0,
                "last_run": None
            }
        }
    
    def get_patterns(self, category: str = None) -> List[Dict[str, Any]]:
        """Get validation patterns, optionally filtered by category"""
        if category and category in self.skills.get("skills", {}):
            return self.skills["skills"][category].get("patterns", [])
        
        # Return all patterns across all categories
        all_patterns = []
        for cat_data in self.skills.get("skills", {}).values():
            all_patterns.extend(cat_data.get("patterns", []))
        return all_patterns
    
    def learn_pattern(self, category: str, pattern_id: str, pattern_data: Dict[str, Any]):
        """Add a new learned pattern"""
        if "skills" not in self.skills:
            self.skills["skills"] = {}
        
        if category not in self.skills["skills"]:
            self.skills["skills"][category] = {
                "description": pattern_data.get("description", ""),
                "patterns": []
            }
        
        # Check if pattern already exists
        existing = next(
            (p for p in self.skills["skills"][category]["patterns"] 
             if p["id"] == pattern_id), 
            None
        )
        
        if existing:
            # Update existing pattern
            existing.update(pattern_data)
            existing["last_seen"] = datetime.now().isoformat()
        else:
            # Add new pattern
            pattern_data["id"] = pattern_id
            pattern_data["learned_on"] = datetime.now().isoformat()
            self.skills["skills"][category]["patterns"].append(pattern_data)
        
        self.skills["last_updated"] = datetime.now().isoformat()
    
    def record_run(self, issues_found: int, issues_fixed: int = 0):
        """Record validation run statistics"""
        stats = self.skills.get("validation_stats", {})
        stats["total_runs"] = stats.get("total_runs", 0) + 1
        stats["issues_found"] = stats.get("issues_found", 0) + issues_found
        stats["issues_fixed"] = stats.get("issues_fixed", 0) + issues_fixed
        stats["last_run"] = datetime.now().isoformat()
        self.skills["validation_stats"] = stats
    
    def save(self):
        """Persist skills to disk"""
        self.skills_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.skills_file, 'w') as f:
            json.dump(self.skills, f, indent=2)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return self.skills.get("validation_stats", {})
    
    def suggest_improvements(self, validation_results: Dict[str, Any]) -> List[str]:
        """Analyze results and suggest new patterns to learn"""
        suggestions = []
        
        # Check for recurring issues
        if validation_results.get("yaml_issues"):
            suggestions.append(
                "Consider adding pattern for: recurring YAML validation failures"
            )
        
        if validation_results.get("style_issues"):
            suggestions.append(
                "Consider adding pattern for: common style violations"
            )
        
        if validation_results.get("link_issues"):
            suggestions.append(
                "Consider adding pattern for: broken link patterns"
            )
        
        return suggestions
    
    def export_report(self) -> str:
        """Generate human-readable skills report"""
        report_lines = [
            "=== Blog QA Skills Report ===",
            f"Last Updated: {self.skills.get('last_updated', 'Unknown')}",
            "",
            "Validation Statistics:",
        ]
        
        stats = self.get_stats()
        report_lines.append(f"  Total Runs: {stats.get('total_runs', 0)}")
        report_lines.append(f"  Issues Found: {stats.get('issues_found', 0)}")
        report_lines.append(f"  Issues Fixed: {stats.get('issues_fixed', 0)}")
        report_lines.append(f"  Last Run: {stats.get('last_run', 'Never')}")
        report_lines.append("")
        
        report_lines.append("Learned Skills:")
        for category, cat_data in self.skills.get("skills", {}).items():
            report_lines.append(f"\n  {category.replace('_', ' ').title()}:")
            report_lines.append(f"    {cat_data.get('description', '')}")
            for pattern in cat_data.get("patterns", []):
                report_lines.append(f"    - {pattern['id']}: {pattern.get('pattern', '')}")
                report_lines.append(f"      Severity: {pattern.get('severity', 'unknown')}")
        
        return "\n".join(report_lines)


if __name__ == "__main__":
    # Test the skills manager
    manager = SkillsManager()
    print(manager.export_report())
