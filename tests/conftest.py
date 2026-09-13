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


# ---------------------------------------------------------------------------
# BUG-082: no test may mutate the real repo's runtime state.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent

#: Real, gitignored runtime state that a test must never touch. The first entry
#: is the live clone of ``oviney/blog``: a fixture written there once sat in
#: ``_posts/`` on a test-created branch, one commit away from the live site.
_GUARDED_PATHS = (
    "temp_blog_repo/_posts",
    "temp_blog_repo/_review",
    "temp_blog_repo/assets",
    "temp_blog_repo/.git/HEAD",
    "logs",
    "output/posts",
    "output/quarantine",
)


def _state_snapshot() -> dict[str, int]:
    """Map every guarded file (one level deep) to its mtime, for paths that exist."""
    snap: dict[str, int] = {}
    for rel in _GUARDED_PATHS:
        p = _REPO_ROOT / rel
        if p.is_file():
            snap[rel] = p.stat().st_mtime_ns
        elif p.is_dir():
            for child in p.iterdir():
                snap[f"{rel}/{child.name}"] = child.stat().st_mtime_ns
    return snap


@pytest.fixture(autouse=True)
def _no_real_state_mutation(request: pytest.FixtureRequest) -> None:
    """Fail the test that writes into the real clone, ``logs/`` or ``output/`` (BUG-082).

    Every test that needs a filesystem gets one under ``tmp_path``. This guard
    is the sensor: it compares a cheap mtime snapshot of the real state before
    and after each test, so the culprit is named rather than discovered months
    later as an untracked file in the blog's ``_posts/``.
    """
    before = _state_snapshot()
    yield
    after = _state_snapshot()
    if before != after:
        changed = sorted(
            k for k in before.keys() | after.keys() if before.get(k) != after.get(k)
        )
        pytest.fail(
            "BUG-082: this test mutated real repo state outside tmp_path: "
            + ", ".join(changed)
        )
