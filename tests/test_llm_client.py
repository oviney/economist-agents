"""Tests for scripts/llm_client.py - OpenAI LLM Client Factory.

Target: 80%+ coverage for OpenAI-only functionality
"""

import contextlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import functions from llm_client
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scripts.llm_client import (
    LLMClient,
    call_llm,
    create_llm_client,
)

# ═══════════════════════════════════════════════════════════════════════════
# TEST FIXTURES
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test response from GPT"))]
    mock_usage = Mock()
    mock_usage.prompt_tokens = 100
    mock_usage.completion_tokens = 50
    mock_usage.total_tokens = 150
    mock_response.usage = mock_usage
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def clean_env():
    """Clean environment for testing."""
    # Store original env vars
    original_vars = {}
    # LLM_PROVIDER and ANTHROPIC_API_KEY added with BUG-046: the keyless
    # agent_sdk provider is now the default, so these tests must name the
    # legacy provider they mean to exercise rather than inferring it from a key.
    for key in [
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "ANTHROPIC_API_KEY",
        "LLM_PROVIDER",
    ]:
        original_vars[key] = os.environ.get(key)
        if key in os.environ:
            del os.environ[key]

    yield

    # Restore original environment
    for key, value in original_vars.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


def mock_openai_import(mock_client):
    """Helper to mock openai module import."""
    mock_module = MagicMock()
    mock_module.OpenAI.return_value = mock_client
    mock_module.RateLimitError = type("RateLimitError", (Exception,), {})

    # Handle both dict and module forms of __builtins__
    import builtins

    original_import = builtins.__import__

    def custom_import(name, *args, **kwargs):
        if name == "openai":
            return mock_module
        return original_import(name, *args, **kwargs)

    return patch("builtins.__import__", side_effect=custom_import)


# ═══════════════════════════════════════════════════════════════════════════
# TEST CLIENT CREATION
# ═══════════════════════════════════════════════════════════════════════════


class TestClientCreation:
    """Test OpenAI LLM client creation."""

    def test_creates_openai_client_when_key_present(
        self,
        clean_env,
        mock_openai_client,
        capsys,
        caplog,
    ):
        """Test that OpenAI client is created when OPENAI_API_KEY is set."""
        os.environ["OPENAI_API_KEY"] = "sk-test-key"
        os.environ["LLM_PROVIDER"] = "openai"  # BUG-046: keyless is the default now

        with mock_openai_import(mock_openai_client), caplog.at_level("INFO"):
            client = create_llm_client()

            assert isinstance(client, LLMClient)
            assert client.provider == "openai"
            assert client.model == "gpt-4o"

            # The provider announcement moved from print() to logger.info()
            # with BUG-046 — CLAUDE.md mandates logger over print.
            assert "LLM Provider: openai" in caplog.text
            assert "Model: gpt-4o" in capsys.readouterr().out

    def test_no_api_key_yields_the_keyless_provider(self, clean_env):
        """No key is the *normal* case now, not an error (BUG-046).

        This asserted `ValueError: No API key found`. That behaviour was the
        defect: Operating Constraint #3 says the only LLM auth is the Claude
        subscription, and requiring a key contradicted it — which is why
        `EconomistContentFlow` Stage 1 could not run keyless.
        """
        client = create_llm_client()

        assert client.provider == "agent_sdk"
        assert client.client is None

    def test_naming_a_paid_provider_without_its_key_still_errors(self, clean_env):
        """Explicit request, absent credential — say so rather than fall back."""
        os.environ["LLM_PROVIDER"] = "openai"

        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            create_llm_client()

    def test_custom_model_configuration(self, clean_env, mock_openai_client):
        """Test custom model configuration via environment variable."""
        os.environ["OPENAI_API_KEY"] = "sk-test-key"
        os.environ["LLM_PROVIDER"] = "openai"  # BUG-046: keyless is the default now
        os.environ["OPENAI_MODEL"] = "gpt-3.5-turbo"

        with mock_openai_import(mock_openai_client):
            client = create_llm_client()
            assert client.model == "gpt-3.5-turbo"

    def test_anthropic_default_model_is_sonnet_4_6(self):
        """Default Anthropic model is claude-sonnet-4-6 when ANTHROPIC_MODEL is unset."""
        import types

        mock_anthropic_instance = MagicMock()
        fake_module = types.ModuleType("anthropic")
        fake_module.Anthropic = MagicMock(  # type: ignore[attr-defined]
            return_value=mock_anthropic_instance,
        )

        # LLM_PROVIDER is required now: a key alone no longer selects a provider,
        # because the keyless agent_sdk path is the default (BUG-046).
        env = {"ANTHROPIC_API_KEY": "sk-ant-test", "LLM_PROVIDER": "anthropic"}
        with (
            patch.dict(os.environ, env, clear=True),
            patch.dict(sys.modules, {"anthropic": fake_module}),
        ):
            client = create_llm_client()

        assert isinstance(client, LLMClient)
        assert client.provider == "anthropic"
        assert client.model == "claude-sonnet-4-6"


# ═══════════════════════════════════════════════════════════════════════════
# TEST ERROR HANDLING
# ═══════════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_missing_openai_package(self, clean_env):
        """Test behavior when openai package is not installed."""
        os.environ["OPENAI_API_KEY"] = "sk-test-key"
        os.environ["LLM_PROVIDER"] = "openai"  # BUG-046: keyless is the default now

        def mock_import(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("No module named 'openai'")
            return __builtins__["__import__"](name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=mock_import),
            pytest.raises(ImportError, match="openai package not installed"),
        ):
            create_llm_client()

    def test_rate_limit_retry_logic(self, clean_env, capsys):
        """Test rate limiting retry logic."""
        os.environ["OPENAI_API_KEY"] = "sk-test-key"
        os.environ["LLM_PROVIDER"] = "openai"  # BUG-046: keyless is the default now

        mock_module = MagicMock()
        rate_limit_error = type("RateLimitError", (Exception,), {})
        mock_module.RateLimitError = rate_limit_error

        # Mock client creation to raise rate limit error twice, then succeed
        call_count = 0
        mock_client = Mock()

        def mock_openai_constructor(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise rate_limit_error("Rate limit exceeded")
            return mock_client

        mock_module.OpenAI = mock_openai_constructor

        with (
            patch("builtins.__import__", return_value=mock_module),
            patch("time.sleep"),  # Speed up test
        ):
            client = create_llm_client(max_retries=3, base_delay=1)
            assert isinstance(client, LLMClient)
            assert client.client == mock_client

        captured = capsys.readouterr()
        assert "Rate limited. Retrying" in captured.out


# ═══════════════════════════════════════════════════════════════════════════
# TEST LLM CALLING
# ═══════════════════════════════════════════════════════════════════════════


class TestCallLLM:
    """Test the call_llm function."""

    def test_call_llm_with_openai_client(self, clean_env, mock_openai_client):
        """Test calling LLM with OpenAI client."""
        llm_client = LLMClient("openai", mock_openai_client, "gpt-4o")

        response = call_llm(
            llm_client,
            "You are a helpful assistant.",
            "Say hello",
            max_tokens=100,
            temperature=0.7,
        )

        assert response == "Test response from GPT"
        mock_openai_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o",
            max_tokens=100,
            temperature=0.7,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello"},
            ],
        )

    def test_call_llm_default_parameters(self, clean_env, mock_openai_client):
        """Test call_llm with default parameters."""
        llm_client = LLMClient("openai", mock_openai_client, "gpt-4o")

        call_llm(llm_client, "System prompt", "User prompt")

        mock_openai_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o",
            max_tokens=3000,
            temperature=1.0,
            messages=[
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "User prompt"},
            ],
        )


# ═══════════════════════════════════════════════════════════════════════════
# TEST INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Test end-to-end integration scenarios."""

    def test_full_workflow(self, clean_env, mock_openai_client, capsys):
        """Test complete workflow from client creation to LLM call."""
        os.environ["OPENAI_API_KEY"] = "sk-test-key"
        os.environ["LLM_PROVIDER"] = "openai"  # BUG-046: keyless is the default now

        with mock_openai_import(mock_openai_client):
            # Create client
            client = create_llm_client()

            # Call LLM
            response = call_llm(
                client,
                "You are an expert.",
                "Explain quantum physics briefly.",
            )

            assert response == "Test response from GPT"
            assert client.provider == "openai"
            assert client.model == "gpt-4o"

            # Provider selection is logged, not printed, since BUG-046. The
            # client's own repr carries the same fact and is what callers see.
            assert repr(client) == "LLMClient(provider=openai, model=gpt-4o)"

    def test_llm_client_repr(self):
        """Test LLMClient string representation."""
        mock_client = Mock()
        llm_client = LLMClient("openai", mock_client, "gpt-4o")

        expected = "LLMClient(provider=openai, model=gpt-4o)"
        assert repr(llm_client) == expected


# ═══════════════════════════════════════════════════════════════════════════
# TEST MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════


def test_main_execution_success(clean_env, mock_openai_client, capsys):
    """Test the main execution block when run as script."""
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    os.environ["LLM_PROVIDER"] = "openai"  # BUG-046: keyless is the default now

    with mock_openai_import(mock_openai_client):
        # Import and execute the main block
        from scripts import llm_client

        # Simulate running as main
        with (
            patch("scripts.llm_client.__name__", "__main__"),
            contextlib.suppress(SystemExit),
        ):
            # This would normally be executed when script is run directly
            exec(
                """
if __name__ == "__main__":
    print("Testing LLM Client Factory\\n")
    try:
        client = create_llm_client()
        print(f"✅ Created: {client}")
        response = call_llm(
            client,
            "You are a helpful assistant.",
            "Say 'Hello, I am working!' and nothing else.",
            max_tokens=50,
        )
        print(f"\\n✅ Test Response: {response}")
    except Exception as e:
        print(f"❌ Error: {e}")
""",
                {
                    "create_llm_client": llm_client.create_llm_client,
                    "call_llm": llm_client.call_llm,
                    "__name__": "__main__",
                },
            )

    captured = capsys.readouterr()
    assert "Testing LLM Client Factory" in captured.out
    assert "✅ Created: LLMClient(provider=openai, model=gpt-4o)" in captured.out
    assert "✅ Test Response: Test response from GPT" in captured.out


def test_main_execution_failure(clean_env, capsys):
    """The main block prints an error when client creation fails.

    BUG-046 changed what "fails" means here. A missing key is no longer a
    failure — it selects the keyless agent_sdk provider — so this test used to
    fall through to a **real** subscription call via `call_llm` and hang the
    suite. The case that still fails is naming a paid provider without its key,
    which is what this now exercises.
    """
    os.environ["LLM_PROVIDER"] = "openai"

    # Import the module
    from scripts import llm_client

    with (
        patch("scripts.llm_client.__name__", "__main__"),
        contextlib.suppress(SystemExit),
    ):
        exec(
            """
if __name__ == "__main__":
    print("Testing LLM Client Factory\\n")
    try:
        client = create_llm_client()
        print(f"✅ Created: {client}")
        response = call_llm(
            client,
            "You are a helpful assistant.",
            "Say 'Hello, I am working!' and nothing else.",
            max_tokens=50,
        )
        print(f"\\n✅ Test Response: {response}")
    except Exception as e:
        print(f"❌ Error: {e}")
""",
            {
                "create_llm_client": llm_client.create_llm_client,
                "call_llm": llm_client.call_llm,
                "__name__": "__main__",
            },
        )

    captured = capsys.readouterr()
    assert "Testing LLM Client Factory" in captured.out
    assert "❌ Error:" in captured.out
    assert "OPENAI_API_KEY" in captured.out
