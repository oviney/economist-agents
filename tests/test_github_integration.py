#!/usr/bin/env python3
"""
GitHub Integration Test Suite

Tests all GitHub integration components:
1. Local sprint validator still works
2. Pre-work check functions
3. GitHub Actions YAML syntax
4. Issue template validation
5. Sprint sync capabilities

Usage:
    python3 tests/test_github_integration.py
"""

import json
import os
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from sprint_validator import SprintValidator


class GitHubIntegrationTests:
    """Test GitHub integration components"""

    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "tests": []}

    def test(self, name: str, func):
        """Run a test and record result"""
        print(f"\n🔍 Test: {name}")
        try:
            func()
            print("   ✅ PASS")
            self.results["passed"] += 1
            self.results["tests"].append({"name": name, "status": "PASS"})
        except AssertionError as e:
            print(f"   ❌ FAIL: {e}")
            self.results["failed"] += 1
            self.results["tests"].append(
                {"name": name, "status": "FAIL", "error": str(e)}
            )
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            self.results["failed"] += 1
            self.results["tests"].append(
                {"name": name, "status": "ERROR", "error": str(e)}
            )

    # TEST 1: Sprint Validator Still Works
    def test_sprint_validator_active_sprint(self):
        """Verify sprint validator can detect active sprint"""
        validator = SprintValidator("SPRINT.md")
        sprint = validator.get_active_sprint()

        assert sprint is not None, "No active sprint found"
        assert sprint["is_active"], "Sprint not marked as active"
        assert sprint["number"] == 2, f"Expected Sprint 2, got {sprint['number']}"
        print(f"      Active Sprint: {sprint['number']} - {sprint['name']}")

    # TEST 2: Sprint Validator Detects Stories
    def test_sprint_validator_stories(self):
        """Verify sprint validator can parse stories"""
        validator = SprintValidator("SPRINT.md")
        stories = validator.get_sprint_stories()

        assert len(stories) > 0, "No stories found"
        assert len(stories) == 4, f"Expected 4 stories, found {len(stories)}"

        # Check Story 1 structure
        story1 = stories[0]
        assert story1["number"] == 1, "Story 1 not found"
        assert (
            story1["points"] == 2
        ), f"Story 1 should be 2 points, got {story1['points']}"
        assert len(story1["tasks"]) > 0, "Story 1 has no tasks"
        print(f"      Found {len(stories)} stories with correct structure")

    # TEST 3: GitHub Actions YAML Syntax
    def test_github_actions_yaml_valid(self):
        """Verify GitHub Actions workflow files are valid YAML"""
        import yaml

        workflows = [
            ".github/workflows/sprint-discipline.yml",
            ".github/workflows/quality-tests.yml",
        ]

        for workflow in workflows:
            with open(workflow) as f:
                try:
                    yaml.safe_load(f)
                    print(f"      ✓ {workflow}")
                except yaml.YAMLError as e:
                    raise AssertionError(f"Invalid YAML in {workflow}: {e}") from e

    # TEST 4: Issue Templates Valid YAML
    def test_issue_templates_valid(self):
        """Verify issue templates are valid YAML"""
        import yaml

        templates = [
            ".github/ISSUE_TEMPLATE/sprint_story.yml",
            ".github/ISSUE_TEMPLATE/bug_report.yml",
        ]

        for template in templates:
            with open(template) as f:
                try:
                    data = yaml.safe_load(f)
                    assert "name" in data, f"{template} missing 'name' field"
                    assert "description" in data, f"{template} missing 'description'"
                    assert "body" in data, f"{template} missing 'body'"
                    print(f"      ✓ {template}")
                except yaml.YAMLError as e:
                    raise AssertionError(f"Invalid YAML in {template}: {e}") from e

    # TEST 5: Pre-Work Check Script Exists
    def test_pre_work_check_exists(self):
        """Verify pre-work check script exists and is executable"""
        script = Path("scripts/pre_work_check.sh")

        assert script.exists(), "pre_work_check.sh not found"
        assert os.access(script, os.X_OK), "pre_work_check.sh not executable"
        print("      ✓ Script exists and is executable")

    # TEST 6: Sprint Sync Script Imports
    def test_sprint_sync_imports(self):
        """Verify sprint sync script can be imported"""
        try:
            import github_sprint_sync  # noqa: F401

            print("      ✓ GitHubSprintSync class importable")
        except ImportError as e:
            # PyGithub might not be installed, but script should still import
            if "github" not in str(e).lower():
                raise AssertionError(f"Import error: {e}") from e
            print("      ⚠ PyGithub not installed (optional)")

    # TEST 7: Documentation Files Exist
    def test_documentation_complete(self):
        """Verify all documentation files exist"""
        docs = [
            "docs/GITHUB_SPRINT_INTEGRATION.md",
            "docs/SPRINT_DISCIPLINE_GUIDE.md",
            "SPRINT.md",
            "README.md",
        ]

        for doc in docs:
            assert Path(doc).exists(), f"Missing: {doc}"
            print(f"      ✓ {doc}")

    # TEST 8: GitHub Actions Required Fields
    def test_github_actions_structure(self):
        """Verify GitHub Actions have required fields"""
        import yaml

        with open(".github/workflows/sprint-discipline.yml") as f:
            workflow = yaml.safe_load(f)

        assert "name" in workflow, "Missing workflow name"
        # Note: YAML parses 'on:' as True (boolean), not 'on' (string key)
        assert True in workflow or "on" in workflow, "Missing trigger events"
        assert "jobs" in workflow, "Missing jobs"

        # Check sprint discipline job
        jobs = workflow["jobs"]
        assert "validate-sprint-discipline" in jobs, "Missing validation job"

        job = jobs["validate-sprint-discipline"]
        assert "steps" in job, "Job missing steps"
        assert len(job["steps"]) > 0, "Job has no steps"
        print("      ✓ Sprint discipline workflow properly structured")

    # TEST 9: PR Template Has Checklist
    def test_pr_template_structure(self):
        """Verify PR template has sprint discipline checklist"""
        with open(".github/PULL_REQUEST_TEMPLATE.md") as f:
            content = f.read()

        assert "Sprint Discipline Checklist" in content, "Missing checklist section"
        assert "Sprint Story Reference" in content, "Missing story reference check"
        assert "Acceptance Criteria Met" in content, "Missing AC check"
        assert "Closes #" in content, "Missing issue linking pattern"
        print("      ✓ PR template has all required checks")

    # TEST 10: Integration with Existing Skills
    def test_skills_system_integration(self):
        """Verify sprint discipline skills are in skills system"""
        with open("skills/blog_qa_skills.json") as f:
            skills = json.load(f)

        assert (
            "sprint_discipline" in skills["skills"]
        ), "sprint_discipline category missing"

        sprint_skills = skills["skills"]["sprint_discipline"]
        assert "patterns" in sprint_skills, "No patterns in sprint_discipline"

        patterns = sprint_skills["patterns"]
        assert len(patterns) == 6, f"Expected 6 patterns, found {len(patterns)}"

        # Check for critical patterns
        pattern_ids = [p["id"] for p in patterns]
        assert "work_without_planning" in pattern_ids, "Missing critical pattern"
        assert "scope_creep_mid_sprint" in pattern_ids, "Missing scope creep pattern"
        print("      ✓ Sprint discipline integrated into skills system")

    def run_all(self):
        """Run all tests"""
        print("=" * 60)
        print("GitHub Integration Test Suite")
        print("=" * 60)

        self.test(
            "Sprint validator detects active sprint",
            self.test_sprint_validator_active_sprint,
        )

        self.test("Sprint validator parses stories", self.test_sprint_validator_stories)

        self.test("GitHub Actions YAML valid", self.test_github_actions_yaml_valid)

        self.test("Issue templates valid", self.test_issue_templates_valid)

        self.test("Pre-work check script exists", self.test_pre_work_check_exists)

        self.test("Sprint sync script imports", self.test_sprint_sync_imports)

        self.test("Documentation complete", self.test_documentation_complete)

        self.test("GitHub Actions structure", self.test_github_actions_structure)

        self.test("PR template structure", self.test_pr_template_structure)

        self.test("Skills system integration", self.test_skills_system_integration)

        # Summary
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"\n✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"Total: {self.results['passed'] + self.results['failed']}")

        if self.results["failed"] == 0:
            print("\n🎉 ALL TESTS PASSED - GitHub integration fully operational!")
            return 0
        else:
            print(f"\n⚠️  {self.results['failed']} test(s) failed")
            return 1


if __name__ == "__main__":
    tester = GitHubIntegrationTests()
    exit_code = tester.run_all()
    sys.exit(exit_code)
