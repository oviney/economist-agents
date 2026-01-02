"""Tests for scripts/llm_client.py - Unified LLM Client Factory.

Target: 80%+ coverage (71+ of 89 statements)
Current: 20% (18 statements)
Impact: 46.7% → 51%+ overall project coverage
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# Import functions from llm_client
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from llm_client import (
    LLMClient,
    call_llm,
    create_llm_client,
)

# ═══════════════════════════════════════════════════════════════════════════
# TEST FIXTURES
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="Test response from Claude")]
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test response from GPT"))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def clean_env():
    """Clean environment for testing (no API keys)."""
    env_keys = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "LLM_PROVIDER",
        "ANTHROPIC_MODEL",
        "OPENAI_MODEL",
    ]
    old_values = {key: os.environ.get(key) for key in env_keys}

    # Clear all keys
    for key in env_keys:
        os.environ.pop(key, None)

    yield

    # Restore old values
    for key, value in old_values.items():
        if value is not None:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)


def mock_anthropic_import(mock_client):
    """Helper to mock anthropic module import."""
    mock_module = MagicMock()
    mock_module.Anthropic.return_value = mock_client
    mock_module.RateLimitError = type("RateLimitError", (Exception,), {})

    # Handle both dict and module forms of __builtins__
    import builtins

    original_import = builtins.__import__

    def custom_import(name, *args, **kwargs):
        if name == "anthropic":
            return mock_module
        return original_import(name, *args, **kwargs)

    return patch("builtins.__import__", side_effect=custom_import)


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
    """Test LLM client creation with various configurations."""

    def test_creates_anthropic_client_when_key_present(
        self, clean_env, mock_anthropic_client, capsys
    ):
        """Test that Anthropic client is created when ANTHROPIC_API_KEY is set."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

        with mock_anthropic_import(mock_anthropic_client):
            client = create_llm_client()

            assert isinstance(client, LLMClient)
            assert client.provider == "anthropic"
            assert client.model == "claude-sonnet-4-20250514"

            # Verify console output
            captured = capsys.readouterr()
            assert "LLM Provider: anthropic" in captured.out
            assert "Model: claude-sonnet-4-20250514" in captured.out

    def test_creates_openai_client_when_only_openai_key(
        self, clean_env, mock_openai_client, capsys
    ):
        """Test that OpenAI client is created when only OPENAI_API_KEY is set."""
        os.environ["OPENAI_API_KEY"] = "sk-test-key"

        with mock_openai_import(mock_openai_client):
            client = create_llm_client()

            assert isinstance(client, LLMClient)
            assert client.provider == "openai"
            assert client.model == "gpt-4o"

            captured = capsys.readouterr()
            assert "LLM Provider: openai" in captured.out
            assert "Model: gpt-4o" in captured.out

    def test_anthropic_priority_when_both_keys_present(
        self, clean_env, mock_anthropic_client
    ):
        """Test that Anthropic is preferred when both API keys exist."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"
        os.environ["OPENAI_API_KEY"] = "sk-test-key"

        with mock_anthropic_import(mock_anthropic_client):
            client = create_llm_client()
            assert client.provider == "anthropic"

    def test_raises_error_when_no_keys(self, clean_env):
        """Test that ValueError is raised when no API keys are present."""
        with pytest.raises(ValueError) as exc_info:
            create_llm_client()

        assert "[LLM_CLIENT] No API key found" in str(exc_info.value)
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)
        assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_returns_client_object_with_correct_interface(
        self, clean_env, mock_anthropic_client
    ):
        """Test that returned LLMClient has the expected interface."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

        with mock_anthropic_import(mock_anthropic_client):
            client = create_llm_client()

            # Check LLMClient interface
            assert hasattr(client, "provider")
            assert hasattr(client, "client")
            assert hasattr(client, "model")
            assert callable(getattr(client, "__repr__", None))

            # Test __repr__
            repr_str = repr(client)
            assert "LLMClient" in repr_str
            assert "anthropic" in repr_str
            assert "claude-sonnet-4-20250514" in repr_str


# ═══════════════════════════════════════════════════════════════════════════
# TEST RETRY LOGIC
# ═══════════════════════════════════════════════════════════════════════════


class TestRetryLogic:
    """Test exponential backoff retry logic for rate limiting."""

    def test_retries_on_rate_limit_with_exponential_backoff(
        self, clean_env, mock_anthropic_client
    ):
        """Test that rate limit errors during client creation trigger exponential backoff retries."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

        mock_module = MagicMock()
        # Make RateLimitError class available on the module
        RateLimitErrorClass = type("RateLimitError", (Exception,), {})
        mock_module.RateLimitError = RateLimitErrorClass

        # Mock the Anthropic constructor to fail twice then succeed
        mock_module.Anthropic.side_effect = [
            RateLimitErrorClass("Rate limited"),
            RateLimitErrorClass("Rate limited again"),
            mock_anthropic_client,
        ]

        import builtins

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "anthropic":
                return mock_module
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=custom_import),
            patch("time.sleep") as mock_sleep,
        ):
            # Client creation will trigger retries
            client = create_llm_client(max_retries=3, base_delay=1)

            # Verify client was created after retries
            assert client is not None
            assert client.provider == "anthropic"

            # Verify exponential backoff delays: 1s, 2s
            assert mock_sleep.call_count == 2
            mock_sleep.assert_has_calls([call(1.0), call(2.0)])

    def test_respects_max_retries_limit(self, clean_env, mock_anthropic_client):
        """Test that retry logic stops after max_retries attempts."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

        mock_module = MagicMock()
        RateLimitErrorClass = type("RateLimitError", (Exception,), {})
        mock_module.RateLimitError = RateLimitErrorClass

        # Always fail with rate limit error
        mock_module.Anthropic.side_effect = RateLimitErrorClass("Always rate limited")

        import builtins

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "anthropic":
                return mock_module
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=custom_import),
            patch("time.sleep"),
            pytest.raises(ValueError, match="Rate limit exceeded after 2 retries"),
        ):
            # Should raise after max_retries attempts
            create_llm_client(max_retries=2, base_delay=1)

    def test_exponential_backoff_sequence(self, clean_env, mock_anthropic_client):
        """Test correct exponential backoff sequence (1s, 2s, 4s)."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

        mock_module = MagicMock()
        RateLimitErrorClass = type("RateLimitError", (Exception,), {})
        mock_module.RateLimitError = RateLimitErrorClass

        # Fail 3 times then succeed
        mock_module.Anthropic.side_effect = [
            RateLimitErrorClass("Rate limited"),
            RateLimitErrorClass("Rate limited"),
            RateLimitErrorClass("Rate limited"),
            mock_anthropic_client,
        ]

        import builtins

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "anthropic":
                return mock_module
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=custom_import),
            patch("time.sleep") as mock_sleep,
        ):
            create_llm_client(max_retries=5, base_delay=1)

            # Verify exponential sequence: 1s, 2s, 4s
            assert mock_sleep.call_count == 3
            mock_sleep.assert_has_calls([call(1.0), call(2.0), call(4.0)])

    def test_no_retry_on_non_rate_limit_errors(self, clean_env, mock_anthropic_client):
        """Test that non-rate-limit errors are not retried."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

        # Different error type (not RateLimitError)
        mock_anthropic_client.messages.create.side_effect = ValueError("API Error")

        mock_module = MagicMock()
        mock_module.Anthropic.return_value = mock_anthropic_client
        mock_module.RateLimitError = type("RateLimitError", (Exception,), {})

        import builtins

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "anthropic":
                return mock_module
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=custom_import),
            patch("time.sleep") as mock_sleep,
        ):
            client = create_llm_client()

            # Should raise immediately without retries
            with pytest.raises(ValueError):
                call_llm(client, "system", "user", max_tokens=100)

            # Verify no sleep calls (no retries)
            mock_sleep.assert_not_called()

    def test_custom_base_delay_parameter(self, clean_env, mock_anthropic_client):
        """Test that custom base_delay parameter affects retry timing."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

        mock_module = MagicMock()
        RateLimitErrorClass = type("RateLimitError", (Exception,), {})
        mock_module.RateLimitError = RateLimitErrorClass

        # Fail once then succeed
        mock_module.Anthropic.side_effect = [
            RateLimitErrorClass("Rate limited"),
            mock_anthropic_client,
        ]

        import builtins

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "anthropic":
                return mock_module
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=custom_import),
            patch("time.sleep") as mock_sleep,
        ):
            create_llm_client(max_retries=3, base_delay=0.5)

            # Verify custom delay (0.5s instead of 1s)
            mock_sleep.assert_called_once_with(0.5)


# ═══════════════════════════════════════════════════════════════════════════
# TEST ENVIRONMENT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════


class TestEnvironmentValidation:
    """Test API key validation and environment variable handling."""

    def test_empty_string_api_key_treated_as_missing(self, clean_env):
        """Test that empty string API keys are treated as missing."""
        os.environ["ANTHROPIC_API_KEY"] = ""
        os.environ["OPENAI_API_KEY"] = ""

        with pytest.raises(ValueError) as exc_info:
            create_llm_client()

        assert "[LLM_CLIENT] No API key found" in str(exc_info.value)

    def test_missing_api_key_error_message(self, clean_env):
        """Test that missing API key error message is helpful."""
        with pytest.raises(ValueError) as exc_info:
            create_llm_client()

        error_msg = str(exc_info.value)
        assert "[LLM_CLIENT]" in error_msg
        assert "ANTHROPIC_API_KEY" in error_msg
        assert "OPENAI_API_KEY" in error_msg

    def test_provider_validation_happens_before_client_creation(self, clean_env):
        """Test that provider validation happens early."""
        # No API keys set
        with pytest.raises(ValueError):
            create_llm_client()

        # Validation should happen before any import attempts


# ═══════════════════════════════════════════════════════════════════════════
# TEST PROVIDER SELECTION
# ═══════════════════════════════════════════════════════════════════════════


class TestProviderSelection:
    """Test provider selection logic."""

    def test_anthropic_selected_when_key_present(
        self, clean_env, mock_anthropic_client, capsys
    ):
        """Test Anthropic is selected when ANTHROPIC_API_KEY exists."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"

        with mock_anthropic_import(mock_anthropic_client):
            client = create_llm_client()
            assert client.provider == "anthropic"

            captured = capsys.readouterr()
            assert "LLM Provider: anthropic" in captured.out

    def test_openai_selected_when_only_openai_key(
        self, clean_env, mock_openai_client, capsys
    ):
        """Test OpenAI is selected when only OPENAI_API_KEY exists."""
        os.environ["OPENAI_API_KEY"] = "sk-test"

        with mock_openai_import(mock_openai_client):
            client = create_llm_client()
            assert client.provider == "openai"

            captured = capsys.readouterr()
            assert "LLM Provider: openai" in captured.out

    def test_provider_logged_to_console(self, clean_env, mock_anthropic_client, capsys):
        """Test that selected provider is logged to console."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"

        with mock_anthropic_import(mock_anthropic_client):
            create_llm_client()
            captured = capsys.readouterr()

            # Check for provider and model logs
            assert "LLM Provider:" in captured.out
            assert "anthropic" in captured.out
            assert "Model:" in captured.out


# ═══════════════════════════════════════════════════════════════════════════
# TEST ERROR HANDLING
# ═══════════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Test error handling for various failure scenarios."""

    def test_unsupported_provider_raises_error(self, clean_env):
        """Test that unsupported provider raises clear error."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"

        with mock_anthropic_import(Mock()):
            client = create_llm_client()

            # Manually set to unsupported provider
            client.provider = "unsupported"

            with pytest.raises(ValueError) as exc_info:
                call_llm(client, "system", "prompt", max_tokens=100)

            assert "Unsupported provider" in str(exc_info.value)

    def test_import_error_for_missing_anthropic_package(self, clean_env):
        """Test graceful handling when anthropic package not installed."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"

        # Mock import to raise ImportError
        import builtins

        original_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("No module named 'anthropic'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=failing_import):
            with pytest.raises(ImportError) as exc_info:
                create_llm_client()

            assert "anthropic" in str(exc_info.value).lower()

    def test_import_error_for_missing_openai_package(self, clean_env):
        """Test graceful handling when openai package not installed."""
        os.environ["OPENAI_API_KEY"] = "sk-test"

        # Mock import to raise ImportError
        import builtins

        original_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("No module named 'openai'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=failing_import):
            with pytest.raises(ImportError) as exc_info:
                create_llm_client()

            assert "openai" in str(exc_info.value).lower()


# ═══════════════════════════════════════════════════════════════════════════
# TEST EXPLICIT PROVIDER PARAMETER
# ═══════════════════════════════════════════════════════════════════════════


class TestExplicitProvider:
    """Test explicit provider parameter in create_llm_client()."""

    def test_explicit_anthropic_provider(self, clean_env, mock_anthropic_client):
        """Test explicit provider='anthropic' parameter."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"

        with mock_anthropic_import(mock_anthropic_client):
            client = create_llm_client(provider="anthropic")
            assert client.provider == "anthropic"

    def test_explicit_openai_provider(self, clean_env, mock_openai_client):
        """Test explicit provider='openai' parameter."""
        os.environ["OPENAI_API_KEY"] = "sk-test"

        with mock_openai_import(mock_openai_client):
            client = create_llm_client(provider="openai")
            assert client.provider == "openai"

    def test_explicit_provider_overrides_detection(self, clean_env, mock_openai_client):
        """Test that explicit provider overrides automatic detection."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        os.environ["OPENAI_API_KEY"] = "sk-test"

        # Explicitly request OpenAI despite Anthropic key being present
        with mock_openai_import(mock_openai_client):
            client = create_llm_client(provider="openai")
            assert client.provider == "openai"


# ═══════════════════════════════════════════════════════════════════════════
# TEST CUSTOM MODEL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════


class TestCustomModelConfiguration:
    """Test custom model configuration via environment variables."""

    def test_custom_anthropic_model(self, clean_env, mock_anthropic_client):
        """Test ANTHROPIC_MODEL environment variable."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        os.environ["ANTHROPIC_MODEL"] = "claude-3-opus-20240229"

        with mock_anthropic_import(mock_anthropic_client):
            client = create_llm_client()
            assert client.model == "claude-3-opus-20240229"

    def test_custom_openai_model(self, clean_env, mock_openai_client):
        """Test OPENAI_MODEL environment variable."""
        os.environ["OPENAI_API_KEY"] = "sk-test"
        os.environ["OPENAI_MODEL"] = "gpt-3.5-turbo"

        with mock_openai_import(mock_openai_client):
            client = create_llm_client()
            assert client.model == "gpt-3.5-turbo"


# ═══════════════════════════════════════════════════════════════════════════
# TEST CALL_LLM UNIFIED INTERFACE
# ═══════════════════════════════════════════════════════════════════════════


class TestCallLLM:
    """Test call_llm() unified interface."""

    def test_call_llm_with_anthropic_client(self, mock_anthropic_client):
        """Test call_llm delegates to Anthropic correctly."""
        client = LLMClient(
            "anthropic", mock_anthropic_client, "claude-sonnet-4-20250514"
        )

        response = call_llm(
            client,
            "You are helpful",
            "What is 2+2?",
            max_tokens=100,
        )

        assert response == "Test response from Claude"
        mock_anthropic_client.messages.create.assert_called_once()

    def test_call_llm_with_openai_client(self, mock_openai_client):
        """Test call_llm delegates to OpenAI correctly."""
        client = LLMClient("openai", mock_openai_client, "gpt-4o")

        response = call_llm(
            client,
            "You are helpful",
            "What is 2+2?",
            max_tokens=100,
        )

        assert response == "Test response from GPT"
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_call_llm_with_unsupported_provider(self, mock_anthropic_client):
        """Test call_llm raises error for unsupported provider."""
        client = LLMClient("gemini", mock_anthropic_client, "gemini-pro")

        with pytest.raises(ValueError) as exc_info:
            call_llm(client, "system", "user", max_tokens=100)

        assert "Unsupported provider: gemini" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════
# TEST LLM_PROVIDER ENV VAR
# ═══════════════════════════════════════════════════════════════════════════


class TestLLMProviderEnvVar:
    """Test LLM_PROVIDER environment variable behavior."""

    def test_llm_provider_anthropic(self, clean_env, mock_anthropic_client):
        """Test LLM_PROVIDER=anthropic forces Anthropic."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        os.environ["OPENAI_API_KEY"] = "sk-test"
        os.environ["LLM_PROVIDER"] = "anthropic"

        with mock_anthropic_import(mock_anthropic_client):
            client = create_llm_client()
            assert client.provider == "anthropic"

    def test_llm_provider_openai(self, clean_env, mock_openai_client):
        """Test LLM_PROVIDER=openai forces OpenAI."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        os.environ["OPENAI_API_KEY"] = "sk-test"
        os.environ["LLM_PROVIDER"] = "openai"

        with mock_openai_import(mock_openai_client):
            client = create_llm_client()
            assert client.provider == "openai"

    def test_llm_provider_invalid(self, clean_env, mock_anthropic_client):
        """Test LLM_PROVIDER with invalid value raises error."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        os.environ["LLM_PROVIDER"] = "gemini"

        # Should raise ValueError for unsupported provider
        with pytest.raises(ValueError, match="Unsupported provider: gemini"):
            create_llm_client()

    def test_llm_provider_overrides_key_priority(self, clean_env, mock_openai_client):
        """Test LLM_PROVIDER overrides default Anthropic priority."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        os.environ["OPENAI_API_KEY"] = "sk-test"
        os.environ["LLM_PROVIDER"] = "openai"

        with mock_openai_import(mock_openai_client):
            client = create_llm_client()
            # Should be OpenAI despite Anthropic key being present
            assert client.provider == "openai"


# ═══════════════════════════════════════════════════════════════════════════
# TEST OPENAI RETRY LOGIC
# ═══════════════════════════════════════════════════════════════════════════


class TestOpenAIRetryLogic:
    """Test retry logic for OpenAI provider."""

    def test_openai_retries_on_rate_limit(self, clean_env, mock_openai_client):
        """Test OpenAI client retries on rate limit errors during client creation."""
        os.environ["OPENAI_API_KEY"] = "sk-test"

        mock_module = MagicMock()
        RateLimitErrorClass = type("RateLimitError", (Exception,), {})
        mock_module.RateLimitError = RateLimitErrorClass

        # Fail once then succeed at client creation
        mock_module.OpenAI.side_effect = [
            RateLimitErrorClass("Rate limited"),
            mock_openai_client,
        ]

        import builtins

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "openai":
                return mock_module
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=custom_import),
            patch("time.sleep") as mock_sleep,
        ):
            client = create_llm_client(max_retries=3)

            # Verify client created and retry happened
            assert client is not None
            assert client.provider == "openai"
            mock_sleep.assert_called_once()

    def test_openai_exponential_backoff(self, clean_env, mock_openai_client):
        """Test OpenAI client uses exponential backoff during client creation."""
        os.environ["OPENAI_API_KEY"] = "sk-test"

        mock_module = MagicMock()
        RateLimitErrorClass = type("RateLimitError", (Exception,), {})
        mock_module.RateLimitError = RateLimitErrorClass

        # Fail twice then succeed
        mock_module.OpenAI.side_effect = [
            RateLimitErrorClass("Rate limited"),
            RateLimitErrorClass("Rate limited"),
            mock_openai_client,
        ]

        import builtins

        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "openai":
                return mock_module
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=custom_import),
            patch("time.sleep") as mock_sleep,
        ):
            create_llm_client(max_retries=3, base_delay=1)

            # Verify backoff: 1s, 2s
            assert mock_sleep.call_count == 2
            mock_sleep.assert_has_calls([call(1.0), call(2.0)])
