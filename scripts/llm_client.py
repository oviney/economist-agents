#!/usr/bin/env python3
"""
Unified LLM Client Factory

Supports multiple LLM providers (Anthropic Claude, OpenAI) with a unified interface.
Automatically handles rate limiting, retries, and provider-specific quirks.

Environment Variables:
    LLM_PROVIDER: 'anthropic' (default) or 'openai'
    ANTHROPIC_API_KEY: For Claude models
    OPENAI_API_KEY: For OpenAI models
    ANTHROPIC_MODEL: Claude model (default: claude-sonnet-4-20250514)
    OPENAI_MODEL: OpenAI model (default: gpt-4o)

Usage:
    from llm_client import create_llm_client, call_llm

    client = create_llm_client()  # Auto-detects provider
    response = call_llm(client, system_prompt, user_prompt)
"""

import os
import time
from typing import Any

# Try to load from .env file (secure)
try:
    from pathlib import Path

    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, use system env vars


class LLMClient:
    """Unified interface for LLM providers"""

    def __init__(self, provider: str, client: Any, model: str):
        self.provider = provider
        self.client = client
        self.model = model

    def __repr__(self):
        return f"LLMClient(provider={self.provider}, model={self.model})"


def create_llm_client(
    provider: str | None = None, max_retries: int = 3, base_delay: int = 1
) -> LLMClient:
    """
    Create LLM client with automatic provider detection and retry logic.

    Args:
        provider: 'anthropic', 'openai', or None (auto-detect from env)
        max_retries: Number of retries on rate limit errors
        base_delay: Base delay in seconds for exponential backoff

    Returns:
        LLMClient with unified interface

    Raises:
        ValueError: If API key missing or provider unsupported
    """
    # Auto-detect provider
    if provider is None:
        provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
        if not provider:
            # Default to anthropic if ANTHROPIC_API_KEY exists, else openai
            if os.environ.get("ANTHROPIC_API_KEY"):
                provider = "anthropic"
            elif os.environ.get("OPENAI_API_KEY"):
                provider = "openai"
            else:
                raise ValueError(
                    "[LLM_CLIENT] No API key found. Set either:\n"
                    "  export ANTHROPIC_API_KEY='sk-ant-...'\n"
                    "  export OPENAI_API_KEY='sk-...'"
                )

    print(f"🤖 LLM Provider: {provider}")

    if provider == "anthropic":
        return _create_anthropic_client(max_retries, base_delay)
    elif provider == "openai":
        return _create_openai_client(max_retries, base_delay)
    else:
        raise ValueError(
            f"[LLM_CLIENT] Unsupported provider: {provider}. "
            "Choose 'anthropic' or 'openai'"
        )


def _create_anthropic_client(max_retries: int, base_delay: int) -> LLMClient:
    """Create Anthropic Claude client with retry logic"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "[LLM_CLIENT] ANTHROPIC_API_KEY not set. "
            "Export it: export ANTHROPIC_API_KEY='sk-ant-...'"
        )

    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "[LLM_CLIENT] anthropic package not installed. "
            "Install it: pip install anthropic"
        )

    # Retry logic for rate limits
    for attempt in range(max_retries):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
            print(f"   Model: {model}")
            return LLMClient("anthropic", client, model)
        except anthropic.RateLimitError as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                print(
                    f"   ⚠ Rate limited. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
            else:
                raise ValueError(
                    f"[LLM_CLIENT] Rate limit exceeded after {max_retries} retries: {e}"
                )
        except Exception as e:
            raise ValueError(f"[LLM_CLIENT] Failed to create Anthropic client: {e}")


def _create_openai_client(max_retries: int, base_delay: int) -> LLMClient:
    """Create OpenAI client with retry logic"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "[LLM_CLIENT] OPENAI_API_KEY not set. "
            "Export it: export OPENAI_API_KEY='sk-...'"
        )

    try:
        from openai import OpenAI, RateLimitError
    except ImportError:
        raise ImportError(
            "[LLM_CLIENT] openai package not installed. Install it: pip install openai"
        )

    # Retry logic for rate limits
    for attempt in range(max_retries):
        try:
            client = OpenAI(api_key=api_key)
            model = os.environ.get("OPENAI_MODEL", "gpt-4o")
            print(f"   Model: {model}")
            return LLMClient("openai", client, model)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                print(
                    f"   ⚠ Rate limited. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
            else:
                raise ValueError(
                    f"[LLM_CLIENT] Rate limit exceeded after {max_retries} retries: {e}"
                )
        except Exception as e:
            raise ValueError(f"[LLM_CLIENT] Failed to create OpenAI client: {e}")


def call_llm(
    llm_client: LLMClient,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 3000,
    temperature: float = 1.0,
) -> str:
    """
    Call LLM with unified interface across providers.

    Args:
        llm_client: LLMClient instance
        system_prompt: System/context prompt
        user_prompt: User message
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (0-2)

    Returns:
        Response text from LLM
    """
    if llm_client.provider == "anthropic":
        return _call_anthropic(
            llm_client.client,
            llm_client.model,
            system_prompt,
            user_prompt,
            max_tokens,
            temperature,
        )
    elif llm_client.provider == "openai":
        return _call_openai(
            llm_client.client,
            llm_client.model,
            system_prompt,
            user_prompt,
            max_tokens,
            temperature,
        )
    else:
        raise ValueError(f"Unsupported provider: {llm_client.provider}")


def _call_anthropic(
    client,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call Anthropic Claude API"""
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


def _call_openai(
    client,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call OpenAI API"""
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


# Convenience function for backward compatibility
def create_client(provider: str | None = None) -> LLMClient:
    """Alias for create_llm_client for backward compatibility"""
    return create_llm_client(provider)


if __name__ == "__main__":
    # Test the client
    print("Testing LLM Client Factory\n")

    try:
        client = create_llm_client()
        print(f"✅ Created: {client}")

        # Simple test
        response = call_llm(
            client,
            "You are a helpful assistant.",
            "Say 'Hello, I am working!' and nothing else.",
            max_tokens=50,
        )
        print(f"\n✅ Test Response: {response}")

    except Exception as e:
        print(f"❌ Error: {e}")
