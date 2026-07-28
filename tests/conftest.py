"""Pytest configuration and shared fixtures for economist-agents tests."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from tests import _netguard as netguard


def pytest_configure(config: pytest.Config) -> None:
    """Register the network opt-out marker (BUG-058)."""
    config.addinivalue_line(
        "markers",
        "allow_network: permit real outbound sockets in this test (must be justified)",
    )


@pytest.fixture(autouse=True)
def _no_network(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Block real outbound sockets so no test can depend on a third party (BUG-058).

    ``tests/test_economist_agent.py`` patched the LLM boundary but not the arXiv
    provider or the citation verifier, so six tests made live HTTP calls. That
    file alone took **10m24s**, and because arXiv answers with HTTP 429 under
    repeated runs the cost is *unbounded and nondeterministic* — the gate got
    slower the more it was used, and failed outright offline.

    `make ci-local` is the only merge gate (ADR-0015), so its runtime must not be
    set by someone else's rate limiter. Loopback is still allowed (local servers
    and IPC are legitimate); opt out deliberately with
    ``@pytest.mark.allow_network``.

    Sibling of :func:`_hermetic_env` — same "local verification is hermetic"
    contract, one layer lower.
    """
    if request.node.get_closest_marker("allow_network"):
        return
    netguard.install(monkeypatch)
    netguard.install_model_guard(monkeypatch)


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate every test from ambient credentials in a developer's `.env`.

    A local `.env` with `BLOG_REPO_*` (as the keyless runbook uses) otherwise
    leaks in: `_deploy_to_blog` would see credentials and attempt a real
    `git clone` of the blog repo over the network — breaking no-credential
    assertions and, in the kickoff path, hanging the suite. Paid AI keys are
    cleared too so tests never accidentally hit a live provider. Tests that need
    a value set it explicitly via `monkeypatch.setenv` (which wins over this).
    B-011 / ADR-0015: local verification must be hermetic.
    """
    for var in (
        "BLOG_REPO_OWNER",
        "BLOG_OWNER",
        "BLOG_REPO_NAME",
        "BLOG_REPO",
        "BLOG_REPO_TOKEN",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "SERPER_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create temporary output directory for tests.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to temporary output directory

    """
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "charts").mkdir()
    return output_dir


@pytest.fixture
def mock_anthropic_client() -> Mock:
    """Create mock Anthropic client for testing.

    Returns:
        Mock Anthropic client with messages.create method

    """
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text='{"data": "test"}')]
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_openai_client() -> Mock:
    """Create mock OpenAI client for testing.

    Returns:
        Mock OpenAI client with chat.completions.create method

    """
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content='{"data": "test"}'))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_research_data() -> dict:
    """Sample research agent output for testing.

    Returns:
        Dictionary with research data structure

    """
    return {
        "headline_stat": {
            "value": "80% of teams use AI testing",
            "source": "Gartner 2024 Survey",
            "year": "2024",
            "verified": True,
        },
        "data_points": [
            {
                "stat": "50% reduction in test maintenance",
                "source": "Industry Report",
                "year": "2024",
                "verified": True,
            },
        ],
        "chart_data": {
            "title": "AI Adoption in Testing",
            "type": "line",
            "data": [{"year": 2023, "value": 60}, {"year": 2024, "value": 80}],
        },
    }
