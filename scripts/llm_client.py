#!/usr/bin/env python3
"""
LLM Client Factory — OpenAI and Anthropic

Prefers Anthropic (Claude) when ANTHROPIC_API_KEY is set, falls back to
OpenAI when only OPENAI_API_KEY is available.

Environment Variables:
    ANTHROPIC_API_KEY: Anthropic API key (preferred)
    ANTHROPIC_MODEL: Anthropic model (default: claude-sonnet-4-20250514)
    OPENAI_API_KEY: OpenAI API key (fallback)
    OPENAI_MODEL: OpenAI model (default: gpt-4o)

Usage:
    from llm_client import create_llm_client, call_llm

    client = create_llm_client()
    response = call_llm(client, system_prompt, user_prompt)
"""

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

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
    """Unified interface for LLM providers."""

    def __init__(self, provider: str, client: Any, model: str):
        self.provider = provider
        self.client = client
        self.model = model

    def __repr__(self) -> str:
        return f"LLMClient(provider={self.provider}, model={self.model})"


def create_llm_client(max_retries: int = 3, base_delay: int = 1) -> LLMClient:
    """Create LLM client — prefers Anthropic, falls back to OpenAI.

    Args:
        max_retries: Number of retries on rate limit errors.
        base_delay: Base delay in seconds for exponential backoff.

    Returns:
        LLMClient configured for the available provider.

    Raises:
        ValueError: If neither API key is set.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("🤖 LLM Provider: anthropic")
        return _create_anthropic_client()

    if os.environ.get("OPENAI_API_KEY"):
        print("🤖 LLM Provider: openai")
        return _create_openai_client(max_retries, base_delay)

    raise ValueError(
        "[LLM_CLIENT] No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
    )


def _create_anthropic_client() -> LLMClient:
    """Create Anthropic client."""
    api_key = os.environ["ANTHROPIC_API_KEY"]

    try:
        from anthropic import Anthropic
    except ImportError as err:
        raise ImportError(
            "[LLM_CLIENT] anthropic package not installed. "
            "Install it: pip install anthropic"
        ) from err

    client = Anthropic(api_key=api_key)
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    print(f"   Model: {model}")
    return LLMClient("anthropic", client, model)


def _create_openai_client(max_retries: int, base_delay: int) -> LLMClient:
    """Create OpenAI client with retry logic."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "[LLM_CLIENT] OPENAI_API_KEY not set. "
            "Export it: export OPENAI_API_KEY='sk-...'"
        )

    try:
        from openai import OpenAI, RateLimitError
    except ImportError as err:
        raise ImportError(
            "[LLM_CLIENT] openai package not installed. Install it: pip install openai"
        ) from err

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
                    f"   ⚠ Rate limited. Retrying in {delay}s... "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
            else:
                raise ValueError(
                    f"[LLM_CLIENT] Rate limit exceeded after {max_retries} retries: {e}"
                ) from e
        except Exception as e:
            raise ValueError(
                f"[LLM_CLIENT] Failed to create OpenAI client: {e}"
            ) from e

    raise ValueError("[LLM_CLIENT] Unreachable")


def call_llm(
    llm_client: LLMClient,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 3000,
    temperature: float = 1.0,
) -> str:
    """Call LLM API (dispatches to correct provider).

    Args:
        llm_client: LLMClient instance.
        system_prompt: System/context prompt.
        user_prompt: User message.
        max_tokens: Maximum tokens in response.
        temperature: Sampling temperature (0-2).

    Returns:
        Response text from LLM.
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
    return _call_openai(
        llm_client.client,
        llm_client.model,
        system_prompt,
        user_prompt,
        max_tokens,
        temperature,
    )


def _call_anthropic(
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call Anthropic API."""
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    try:
        from token_usage import log_token_usage

        log_token_usage(
            model=model,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )
    except (ImportError, AttributeError, OSError) as exc:
        logger.warning("Could not log token usage: %s", exc)

    return response.content[0].text


def _call_openai(
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call OpenAI API."""
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    try:
        from token_usage import log_token_usage

        usage = response.usage
        if usage is not None:
            log_token_usage(
                model=model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
    except (ImportError, AttributeError, OSError) as exc:
        logger.warning("Could not log token usage: %s", exc)

    return response.choices[0].message.content


# Convenience function for backward compatibility
def create_client() -> LLMClient:
    """Alias for create_llm_client for backward compatibility."""
    return create_llm_client()


if __name__ == "__main__":
    print("Testing LLM Client Factory\n")

    try:
        client = create_llm_client()
        print(f"✅ Created: {client}")

        response = call_llm(
            client,
            "You are a helpful assistant.",
            "Say 'Hello, I am working!' and nothing else.",
            max_tokens=50,
        )
        print(f"\n✅ Test Response: {response}")

    except Exception as e:
        print(f"❌ Error: {e}")
