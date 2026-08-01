"""Config invariants for the harness (B-031, B-034).

Every finding these tests guard was, at the time of the audit, a *live* defect that no test
would have caught — because they are defects in the sensors themselves, and nothing was
watching the watchers. That is the gap this file closes.

The rule they all serve: **a sensor that cannot fail is worse than no sensor, because it
manufactures confidence.** Each assertion below corresponds to a specific way this repo had
already broken that rule.
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

import orjson
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Keys forbidden as a requirement by CLAUDE.md constraints #1-#3.
FORBIDDEN_KEYS = (
    "OPENAI_API_KEY",
    "SERPER_API_KEY",
    "GEMINI_API_KEY",
    "TAVILY_API_KEY",
    "BRAVE_API_KEY",
)


@pytest.fixture(scope="module")
def precommit_config() -> dict:
    """Parse .pre-commit-config.yaml once for the whole module."""
    return yaml.safe_load(
        (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"),
    )


@pytest.fixture(scope="module")
def precommit_hooks(precommit_config: dict) -> list[dict]:
    """Flatten every hook definition across every repo entry."""
    return [hook for repo in precommit_config["repos"] for hook in repo["hooks"]]


class TestHooksPointAtRealScripts:
    """A hook whose entry script does not exist is not a gate (B-036).

    `badge-validation` ran `python3 scripts/validate_badges.py`, but that script
    was archived to `scripts/archived/` in #327/#343. The hook survived because
    its entry was `bash -c '... || true'` — so it swallowed both the stale-badge
    failures it was meant to catch *and* the "no such file" error proving it had
    no implementation at all.

    B-031 removed the `|| true`, which correctly turned a silent phantom into a
    loud one: the next push failed. That is the sensor working. This test
    generalises the lesson, because the same shape can recur for any hook.
    """

    def test_every_local_hook_entry_script_exists(self, precommit_config: dict) -> None:
        missing = []
        for repo in precommit_config["repos"]:
            if repo.get("repo") != "local":
                continue
            for hook in repo["hooks"]:
                for token in str(hook.get("entry", "")).split():
                    is_script = token.endswith((".py", ".sh"))
                    if is_script and not (REPO_ROOT / token).exists():
                        missing.append(f"{hook['id']} → {token}")

        assert not missing, (
            "pre-commit hooks reference scripts that do not exist: "
            f"{missing}. A hook that cannot run is not a gate."
        )


class TestNoInertSensors:
    """B-031: four pre-commit hooks could not fail. None may again."""

    def test_no_hook_swallows_its_own_failure(
        self, precommit_hooks: list[dict]
    ) -> None:
        """`badge-validation` was `bash -c '... || true'` — structurally always green.

        Its stated purpose was preventing BUG-023 (stale badges), so the one hook that
        existed to catch a specific past defect was incapable of catching it.
        """
        offenders = [
            hook["id"]
            for hook in precommit_hooks
            if "|| true" in str(hook.get("entry", ""))
            or "|| exit 0" in str(hook.get("entry", ""))
        ]

        assert offenders == [], f"hooks that cannot fail: {offenders}"

    def test_no_duplicate_hook_ids(self, precommit_hooks: list[dict]) -> None:
        """`validate-skills` was registered twice under one id, with a duplicated key."""
        counts = collections.Counter(hook["id"] for hook in precommit_hooks)
        duplicates = [hook_id for hook_id, n in counts.items() if n > 1]

        assert duplicates == [], f"duplicate hook ids: {duplicates}"

    def test_no_hook_is_stranded_on_manual_stage(
        self,
        precommit_hooks: list[dict],
    ) -> None:
        """mypy and pytest-coverage sat on `stages: [manual]`, so they never ran.

        `manual` alone means the hook is invisible to `git commit` and `git push`. A hook
        nobody invokes is documentation wearing a gate's clothing.
        """
        stranded = [
            hook["id"] for hook in precommit_hooks if hook.get("stages") == ["manual"]
        ]

        assert stranded == [], f"hooks that never run: {stranded}"

    def test_coverage_threshold_has_exactly_one_value(self) -> None:
        """`make test` said 40 while `make ci-local` said 70 — two numbers, one gate."""
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

        thresholds = set(re.findall(r"--cov-fail-under=(\d+)", makefile))

        assert len(thresholds) == 1, (
            f"Makefile declares conflicting coverage thresholds: {sorted(thresholds)}"
        )


class TestNoForbiddenKeys:
    """B-034: the harness must not offer the agent tools its guides forbid."""

    def test_mcp_json_requires_no_api_key(self) -> None:
        """`.mcp.json` shipped image-generator (OPENAI) and web-researcher (SERPER).

        Both were prohibited by CLAUDE.md and already retired in code (ADR-0014, #438) —
        the config had simply not caught up, so the agent was shown a DALL-E tool sitting
        beside the guide banning it.
        """
        raw = (REPO_ROOT / ".mcp.json").read_text(encoding="utf-8")

        present = [key for key in FORBIDDEN_KEYS if key in raw]

        assert present == [], f"forbidden keys in .mcp.json: {present}"

    def test_no_mcp_server_declares_an_env_requirement(self) -> None:
        """Belt and braces: any `env` block is a key requirement in disguise."""
        config = orjson.loads((REPO_ROOT / ".mcp.json").read_bytes())

        with_env = [
            name for name, server in config["mcpServers"].items() if server.get("env")
        ]

        assert with_env == [], f"MCP servers requiring env: {with_env}"


class TestHooksAreWired:
    """B-030: the hooks must exist, be committed, and point at real scripts."""

    @pytest.fixture(scope="class")
    def settings(self) -> dict:
        path = REPO_ROOT / ".claude" / "settings.json"
        assert path.is_file(), "project .claude/settings.json must be committed"
        return orjson.loads(path.read_bytes())

    @pytest.mark.parametrize(
        "event",
        ["PostToolUse", "PreToolUse", "Stop", "SessionStart"],
    )
    def test_event_is_wired(self, settings: dict, event: str) -> None:
        assert settings["hooks"].get(event), f"{event} has no hook"

    def test_every_hook_command_references_the_launcher(self, settings: dict) -> None:
        for event, entries in settings["hooks"].items():
            for entry in entries:
                for hook in entry["hooks"]:
                    assert "run_hook.sh" in hook["command"], (
                        f"{event} hook bypasses the launcher: {hook['command']}"
                    )

    def test_launcher_exists_and_is_executable(self) -> None:
        launcher = REPO_ROOT / "scripts" / "hooks" / "run_hook.sh"

        assert launcher.is_file()
        assert launcher.stat().st_mode & 0o111, "launcher must be executable"

    def test_every_referenced_hook_module_exists(self, settings: dict) -> None:
        """A typo'd module name would make the hook silently no-op — the exact failure
        mode this whole item exists to eliminate."""
        pattern = re.compile(r"run_hook\.sh\"?\s+(\w+)")
        for entries in settings["hooks"].values():
            for entry in entries:
                for hook in entry["hooks"]:
                    match = pattern.search(hook["command"])
                    assert match, f"cannot parse hook module: {hook['command']}"
                    module = REPO_ROOT / "scripts" / "hooks" / f"{match.group(1)}.py"
                    assert module.is_file(), f"missing hook module: {module}"

    def test_settings_json_is_not_gitignored(self) -> None:
        """Hooks are team policy. If the file is ignored, the policy is one laptop's."""
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

        assert "!.claude/settings.json" in gitignore

    def test_sensor_history_is_gitignored(self) -> None:
        """Runtime snapshots are data, not source."""
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

        assert "logs/sensor_history.jsonl" in gitignore


class TestComplexityThreshold:
    """B-032: one threshold, in one place."""

    def test_ruff_toml_owns_the_threshold(self) -> None:
        ruff_toml = (REPO_ROOT / "ruff.toml").read_text(encoding="utf-8")

        assert "[lint.mccabe]" in ruff_toml
        assert re.search(r"max-complexity\s*=\s*\d+", ruff_toml)

    def test_override_register_exists(self) -> None:
        """The escape hatch the sensor's message promises must actually be there."""
        assert (REPO_ROOT / "docs" / "harness-overrides.md").is_file()
