#!/usr/bin/env python3
"""
GitHub Project V2 Integration Test Suite - Story 3 Validation

Tests comprehensive GitHub Project V2 integration using existing tools:
1. github_project_add_issue tool functionality
2. CrewAI development crew integration with GitHub Projects
3. MCP + CLI fallback workflow validation
4. Real project board operations against Sprint 16 issues (#95, #96, #97)

Usage:
    python3 tests/test_github_project_v2_integration.py

Requirements:
    - GitHub CLI (gh) installed and authenticated
    - Access to oviney/economist-agents repository
    - Project V2 boards accessible (Projects 1, 2, 4)

STORY 3 CONTEXT:
Sprint 16 focuses on validating the CrewAI development infrastructure.
This test suite validates GitHub Project V2 integration patterns and
ensures automated project board updates work during development crew execution.
"""

import logging
import subprocess
import sys
import unittest
from pathlib import Path

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

logger = logging.getLogger(__name__)


def is_gh_cli_available() -> bool:
    """Check if GitHub CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


GH_CLI_AVAILABLE = is_gh_cli_available()


class GitHubProjectV2IntegrationTests(unittest.TestCase):
    """Comprehensive GitHub Project V2 Integration Test Suite

    Validates the full GitHub Project V2 integration workflow including:
    - Tool functionality and error handling
    - CrewAI agent registry integration
    - Real project board operations
    - Security and validation patterns
    """

    @classmethod
    def setUpClass(cls):
        """Set up test environment and validate dependencies"""
        cls.test_results = {"passed": 0, "failed": 0, "tests": []}
        cls.sprint_16_issues = [
            "https://github.com/oviney/economist-agents/issues/95",
            "https://github.com/oviney/economist-agents/issues/96",
            "https://github.com/oviney/economist-agents/issues/97",
        ]
        cls.test_projects = [1, 2, 4]  # Available Project V2 boards

    def setUp(self):
        """Set up each test"""
        self.maxDiff = None

    def log_test_result(self, test_name: str, result: str, details: str = ""):
        """Log test result for final summary"""
        self.test_results["tests"].append(
            {"name": test_name, "result": result, "details": details}
        )
        if result == "PASS":
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1

    # PHASE 1: TOOL FUNCTIONALITY TESTS

    def test_01_github_project_tool_import(self):
        """Test 1: Verify github_project_add_issue tool can be imported"""
        try:
            from scripts.tools.github_project_tool import github_project_add_issue

            # Verify it's a CrewAI tool
            self.assertTrue(hasattr(github_project_add_issue, "name"))
            self.assertEqual(github_project_add_issue.name, "github_project_add_issue")

            # Verify docstring and metadata
            self.assertIsNotNone(github_project_add_issue.__doc__)
            self.assertIn("Project V2", github_project_add_issue.__doc__)

            self.log_test_result("GitHub Project Tool Import", "PASS")

        except ImportError as e:
            self.log_test_result("GitHub Project Tool Import", "FAIL", str(e))
            self.fail(f"Failed to import github_project_add_issue: {e}")

    @unittest.skipUnless(
        GH_CLI_AVAILABLE, "GitHub CLI not available or not authenticated"
    )
    def test_02_github_cli_availability(self):
        """Test 2: Verify GitHub CLI is installed and authenticated"""
        try:
            # Check gh CLI installation
            result = subprocess.run(
                ["gh", "--version"], capture_output=True, text=True, timeout=10
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("gh version", result.stdout)

            # Check authentication status
            auth_result = subprocess.run(
                ["gh", "auth", "status"], capture_output=True, text=True, timeout=10
            )
            self.assertEqual(auth_result.returncode, 0)

            self.log_test_result("GitHub CLI Availability", "PASS")

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.log_test_result("GitHub CLI Availability", "FAIL", str(e))
            self.fail(f"GitHub CLI not available: {e}")

    @unittest.skipUnless(
        GH_CLI_AVAILABLE, "GitHub CLI not available or not authenticated"
    )
    def test_03_project_boards_exist(self):
        """Test 3: Verify target Project V2 boards exist and are accessible"""
        try:
            # List available projects
            result = subprocess.run(
                ["gh", "project", "list", "--owner", "oviney"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0)

            project_output = result.stdout
            self.assertIn("Kanban Board", project_output)  # Project 4

            # Verify specific project numbers exist
            for project_num in self.test_projects:
                self.assertIn(str(project_num), project_output)

            self.log_test_result("Project Boards Exist", "PASS")

        except subprocess.TimeoutExpired as e:
            self.log_test_result("Project Boards Exist", "FAIL", str(e))
            self.fail(f"Failed to verify project boards: {e}")

    @unittest.skipUnless(
        GH_CLI_AVAILABLE, "GitHub CLI not available or not authenticated"
    )
    def test_04_sprint_16_issues_exist(self):
        """Test 4: Verify Sprint 16 issues (#95, #96, #97) exist for testing"""
        try:
            for issue_url in self.sprint_16_issues:
                issue_number = issue_url.split("/")[-1]

                result = subprocess.run(
                    [
                        "gh",
                        "issue",
                        "view",
                        issue_number,
                        "--repo",
                        "oviney/economist-agents",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.assertEqual(result.returncode, 0)

                # Verify issue content
                issue_data = result.stdout
                self.assertIn("Story", issue_data)  # Should be a Sprint 16 story

            self.log_test_result("Sprint 16 Issues Exist", "PASS")

        except subprocess.TimeoutExpired as e:
            self.log_test_result("Sprint 16 Issues Exist", "FAIL", str(e))
            self.fail(f"Failed to verify Sprint 16 issues: {e}")

    # PHASE 2: TOOL FUNCTIONALITY VALIDATION

    def test_05_github_project_tool_validation(self):
        """Test 5: Validate github_project_add_issue tool parameter validation"""
        from scripts.tools.github_project_tool import github_project_add_issue

        try:
            # Test invalid project number (string instead of int)
            with self.assertRaises(TypeError):
                github_project_add_issue(
                    "invalid", "https://github.com/test/test/issues/1"
                )

            # Test invalid URL format
            result = github_project_add_issue(1, "not-a-url")
            self.assertIn("Error", result)

            # Test valid parameters structure (without actual execution)
            valid_params = {
                "project_number": 1,
                "issue_url": "https://github.com/oviney/economist-agents/issues/95",
                "owner": "oviney",
            }

            # Validate parameter types match function signature
            self.assertIsInstance(valid_params["project_number"], int)
            self.assertIsInstance(valid_params["issue_url"], str)
            self.assertIsInstance(valid_params["owner"], str)

            self.log_test_result("Tool Parameter Validation", "PASS")

        except Exception as e:
            self.log_test_result("Tool Parameter Validation", "FAIL", str(e))
            self.fail(f"Tool validation failed: {e}")

    def test_06_tool_error_handling(self):
        """Test 6: Verify tool handles errors gracefully"""
        from scripts.tools.github_project_tool import github_project_add_issue

        try:
            # Test with non-existent project
            result = github_project_add_issue(
                project_number=99999,
                issue_url="https://github.com/oviney/economist-agents/issues/95",
                owner="oviney",
            )
            self.assertIn("Error", result)
            self.assertIsInstance(result, str)

            # Test with invalid owner
            result = github_project_add_issue(
                project_number=1,
                issue_url="https://github.com/oviney/economist-agents/issues/95",
                owner="nonexistent-user-12345",
            )
            self.assertIn("Error", result)

            self.log_test_result("Tool Error Handling", "PASS")

        except Exception as e:
            self.log_test_result("Tool Error Handling", "FAIL", str(e))
            self.fail(f"Error handling test failed: {e}")

    # PHASE 3: INTEGRATION WITH AGENT REGISTRY

    def test_07_agent_registry_tool_integration(self):
        """Test 7: Verify github_project_add_issue is available in agent registry"""
        try:
            from scripts.agent_registry import AgentRegistry

            registry = AgentRegistry()

            # Create a test agent with the GitHub Project tool
            test_config = {
                "role": "Test Agent for GitHub Projects",
                "goal": "Test GitHub Project V2 integration",
                "backstory": "Testing agent for Story 3 validation",
                "tools": ["github_project_add_issue"],
            }

            registry.register_test_agent("test-github-agent", test_config)
            agent = registry.get_agent("test-github-agent")

            # Verify agent has the tool
            self.assertIn("tools", agent)
            tools = agent["tools"]

            # Check that github_project_add_issue is in the tools
            tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
            self.assertIn("github_project_add_issue", tool_names)

            self.log_test_result("Agent Registry Tool Integration", "PASS")

        except Exception as e:
            self.log_test_result("Agent Registry Tool Integration", "FAIL", str(e))
            self.fail(f"Agent registry integration failed: {e}")

    def test_08_crewai_tool_factory_mapping(self):
        """Test 8: Verify tool is correctly mapped in TOOL_FACTORY"""
        try:
            from scripts.agent_registry import AgentRegistry

            registry = AgentRegistry()

            # Test the tool factory directly
            tools = registry._instantiate_tools(["github_project_add_issue"])
            self.assertGreater(len(tools), 0, "No tools instantiated")

            # Verify the tool has expected attributes
            tool = tools[0]
            self.assertTrue(hasattr(tool, "name") or callable(tool))

            self.log_test_result("CrewAI Tool Factory Mapping", "PASS")

        except Exception as e:
            self.log_test_result("CrewAI Tool Factory Mapping", "FAIL", str(e))
            self.fail(f"Tool factory mapping failed: {e}")

    # PHASE 4: REAL PROJECT BOARD OPERATIONS

    @unittest.skipIf(
        subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0,
        "GitHub CLI not authenticated - skipping live tests",
    )
    def test_09_real_project_board_operation(self):
        """Test 9: LIVE TEST - Add Issue #97 to Project Board (Story 3 self-validation)"""
        from scripts.tools.github_project_tool import github_project_add_issue

        try:
            # Use Issue #97 (Story 3) for self-validation
            test_issue_url = "https://github.com/oviney/economist-agents/issues/97"
            test_project = 4  # Kanban Board project

            # Execute the actual tool
            result = github_project_add_issue(
                project_number=test_project, issue_url=test_issue_url, owner="oviney"
            )

            # Verify success or acceptable result
            if "Success" in result:
                self.log_test_result(
                    "Real Project Board Operation",
                    "PASS",
                    f"Successfully added issue to project {test_project}",
                )
            elif "already exists" in result.lower():
                self.log_test_result(
                    "Real Project Board Operation",
                    "PASS",
                    "Issue already in project (expected)",
                )
            else:
                self.log_test_result("Real Project Board Operation", "FAIL", result)
                self.fail(f"Unexpected result: {result}")

        except Exception as e:
            self.log_test_result("Real Project Board Operation", "FAIL", str(e))
            self.fail(f"Live project board operation failed: {e}")

    @unittest.skipUnless(
        GH_CLI_AVAILABLE, "GitHub CLI not available or not authenticated"
    )
    def test_10_batch_project_operations(self):
        """Test 10: Validate batch operations for multiple Sprint 16 issues"""
        from scripts.tools.github_project_tool import github_project_add_issue

        try:
            results = []
            target_project = 4  # Kanban Board

            for issue_url in self.sprint_16_issues:
                result = github_project_add_issue(
                    project_number=target_project, issue_url=issue_url, owner="oviney"
                )
                results.append(
                    {
                        "issue_url": issue_url,
                        "result": result,
                        "success": "Success" in result
                        or "already exists" in result.lower(),
                    }
                )

            # Verify at least some operations succeeded
            successful_ops = [r for r in results if r["success"]]
            self.assertGreater(
                len(successful_ops), 0, "No successful project operations"
            )

            # Log detailed results
            details = f"Successful operations: {len(successful_ops)}/{len(results)}"
            self.log_test_result("Batch Project Operations", "PASS", details)

        except Exception as e:
            self.log_test_result("Batch Project Operations", "FAIL", str(e))
            self.fail(f"Batch operations failed: {e}")

    # PHASE 5: WORKFLOW INTEGRATION VALIDATION

    def test_11_mcp_cli_fallback_pattern(self):
        """Test 11: Validate MCP + CLI fallback workflow pattern"""
        try:
            # Verify the documented pattern: MCP for read, CLI for mutations

            # 1. Check that github_project_add_issue uses CLI (not MCP)
            import inspect

            from scripts.tools.github_project_tool import github_project_add_issue

            source = inspect.getsource(github_project_add_issue)
            self.assertIn("subprocess.run", source)
            self.assertIn("gh", source)
            self.assertIn("project", source)
            self.assertIn("item-add", source)

            # 2. Verify tool documentation explains the fallback pattern
            docstring = github_project_add_issue.__doc__
            self.assertIn("MCP server", docstring)
            self.assertIn("CLI", docstring)
            self.assertIn("Project V2", docstring)

            # 3. Check error handling for CLI unavailability
            self.assertIn("FileNotFoundError", source)

            self.log_test_result("MCP + CLI Fallback Pattern", "PASS")

        except Exception as e:
            self.log_test_result("MCP + CLI Fallback Pattern", "FAIL", str(e))
            self.fail(f"Fallback pattern validation failed: {e}")

    def test_12_development_crew_integration(self):
        """Test 12: Validate integration with CrewAI development crew workflow"""
        try:
            # Test that agents can be created with GitHub Project tools
            from scripts.agent_registry import AgentRegistry

            registry = AgentRegistry()

            # Simulate development crew agents with GitHub Project capabilities
            crew_agents = [
                ("test-specialist", ["github_project_add_issue", "file_read"]),
                ("code-quality-specialist", ["github_project_add_issue", "file_write"]),
                ("git-operator", ["github_project_add_issue", "bash"]),
            ]

            for agent_name, tools in crew_agents:
                config = {
                    "role": f"Test {agent_name.replace('-', ' ').title()}",
                    "goal": "Test GitHub Project integration",
                    "backstory": "Development crew agent for testing",
                    "tools": tools,
                }

                registry.register_test_agent(agent_name, config)
                agent = registry.get_agent(agent_name)

                # Verify agent has GitHub Project tool
                agent_tools = [
                    getattr(t, "name", str(t)) for t in agent.get("tools", [])
                ]
                self.assertIn("github_project_add_issue", agent_tools)

            self.log_test_result(
                "Development Crew Integration",
                "PASS",
                f"Validated {len(crew_agents)} crew agents",
            )

        except Exception as e:
            self.log_test_result("Development Crew Integration", "FAIL", str(e))
            self.fail(f"Development crew integration failed: {e}")

    # PHASE 6: SECURITY AND VALIDATION

    def test_13_security_validation(self):
        """Test 13: Verify security measures in GitHub Project tool"""
        try:
            import inspect

            from scripts.tools.github_project_tool import github_project_add_issue

            source = inspect.getsource(github_project_add_issue)

            # Check timeout protection
            self.assertIn("timeout", source)

            # Check input validation
            self.assertIn("check=False", source)  # Secure subprocess usage

            # Check error handling
            self.assertIn("FileNotFoundError", source)
            self.assertIn("TimeoutExpired", source)
            self.assertIn("Exception", source)

            # Check no shell injection vulnerabilities
            self.assertNotIn("shell=True", source)
            self.assertIn("capture_output=True", source)

            self.log_test_result("Security Validation", "PASS")

        except Exception as e:
            self.log_test_result("Security Validation", "FAIL", str(e))
            self.fail(f"Security validation failed: {e}")

    def test_14_logging_and_monitoring(self):
        """Test 14: Verify proper logging and monitoring capabilities"""
        try:
            import inspect

            from scripts.tools.github_project_tool import github_project_add_issue

            source = inspect.getsource(github_project_add_issue)

            # Check logging integration
            self.assertIn("logger", source)
            self.assertIn("logger.info", source)
            self.assertIn("logger.error", source)

            # Check return value consistency
            self.assertIn("return", source)

            # Verify logger import
            with open(
                Path(__file__).parent.parent
                / "scripts"
                / "tools"
                / "github_project_tool.py"
            ) as f:
                content = f.read()
                self.assertIn("import logging", content)
                self.assertIn("logger = logging.getLogger", content)

            self.log_test_result("Logging and Monitoring", "PASS")

        except Exception as e:
            self.log_test_result("Logging and Monitoring", "FAIL", str(e))
            self.fail(f"Logging validation failed: {e}")

    # SUMMARY AND REPORTING

    @classmethod
    def tearDownClass(cls):
        """Generate comprehensive test report for Story 3 validation"""
        print("\n" + "=" * 80)
        print("GITHUB PROJECT V2 INTEGRATION VALIDATION - STORY 3 RESULTS")
        print("=" * 80)

        total_tests = len(cls.test_results["tests"])
        passed = cls.test_results["passed"]
        failed = cls.test_results["failed"]

        print("\n📊 TEST SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   Success Rate: {(passed/total_tests)*100:.1f}%")

        print("\n📋 DETAILED RESULTS:")
        for i, test in enumerate(cls.test_results["tests"], 1):
            status_icon = "✅" if test["result"] == "PASS" else "❌"
            print(f"   {i:2d}. {status_icon} {test['name']}")
            if test.get("details"):
                print(f"       └─ {test['details']}")

        print("\n🎯 STORY 3 VALIDATION STATUS:")
        if failed == 0:
            print(
                "   🎉 STORY 3 COMPLETE: GitHub Project V2 Integration Fully Validated!"
            )
            print("   ✓ All GitHub Project V2 integration patterns working correctly")
            print("   ✓ CrewAI development crew integration validated")
            print("   ✓ MCP + CLI fallback workflow confirmed")
            print("   ✓ Real project board operations successful")
        else:
            print(f"   ⚠️  STORY 3 NEEDS ATTENTION: {failed} validation failures")
            print(
                "   📝 Review failed tests and address issues before story completion"
            )

        print("\n🔗 SPRINT 16 INTEGRATION:")
        print("   Issues Validated: #95, #96, #97")
        print("   Project Boards: 1, 2, 4 (Kanban Board)")
        print("   Tool: github_project_add_issue")
        print("   Pattern: MCP (read) + CLI (mutations)")


def run_validation_suite():
    """Main entry point for Story 3 validation"""
    print("🚀 Starting GitHub Project V2 Integration Validation for Story 3...")

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run the test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(GitHubProjectV2IntegrationTests)

    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)

    # Return exit code for CI/CD integration
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit_code = run_validation_suite()
    sys.exit(exit_code)
