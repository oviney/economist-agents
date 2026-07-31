#!/usr/bin/env python3
"""LLM Client Factory — OpenAI and Anthropic

Prefers Anthropic (Claude) when ANTHROPIC_API_KEY is set, falls back to
OpenAI when only OPENAI_API_KEY is available.

Environment Variables:
    ANTHROPIC_API_KEY: Anthropic API key (preferred)
    ANTHROPIC_MODEL: Anthropic model (default: claude-sonnet-4-6)
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
    """Create an LLM client. Keyless by default (Operating Constraint #3).

    BUG-046: this used to require ``ANTHROPIC_API_KEY`` or ``OPENAI_API_KEY`` and
    raise ``ValueError`` when neither was set, which is why
    ``EconomistContentFlow`` Stage 1 could not run on the keyless stack — the
    documented workaround was to skip the flow and drive
    ``src.agent_sdk.pipeline`` with a manual topic instead.

    The Agent SDK provider is now the default, so "the only LLM auth is the
    Claude subscription" holds by construction rather than by discipline. A
    stray key left in the environment cannot silently start billing.

    The key-based providers remain reachable via ``LLM_PROVIDER`` because they
    pre-date the constraint, not because anything should reach for them. Naming
    one without its key is an error rather than a silent fallback — a fallback
    would make the request ambiguous exactly when the caller was being explicit.

    Args:
        max_retries: Number of retries on rate limit errors (key-based paths).
        base_delay: Base delay in seconds for exponential backoff.

    Returns:
        LLMClient for the selected provider.

    Raises:
        ValueError: If ``LLM_PROVIDER`` names an unknown provider, or names a
            key-based provider whose key is absent.

    """
    requested = os.environ.get("LLM_PROVIDER", "").strip().lower()

    if requested in ("", "agent_sdk"):
        logger.info("🤖 LLM Provider: agent_sdk (keyless, Claude subscription)")
        return _create_agent_sdk_client()

    if requested == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. "
                "Unset LLM_PROVIDER to use the keyless Agent SDK provider.",
            )
        logger.info("🤖 LLM Provider: anthropic (legacy paid path)")
        return _create_anthropic_client()

    if requested == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. "
                "Unset LLM_PROVIDER to use the keyless Agent SDK provider.",
            )
        logger.info("🤖 LLM Provider: openai (legacy paid path)")
        return _create_openai_client(max_retries, base_delay)

    raise ValueError(
        f"Unknown LLM_PROVIDER={requested!r}. "
        "Valid values: agent_sdk (default), anthropic, openai.",
    )


def _create_agent_sdk_client() -> LLMClient:
    """Build the keyless client that runs on the Claude subscription.

    There is no credential and no SDK object to construct here — the Agent SDK's
    ``query()`` is called per request in `_call_agent_sdk`, so the client is
    just the provider tag and the model name.

    Returns:
        An ``agent_sdk`` LLMClient.

    """
    model = os.environ.get("AGENT_SDK_MODEL", "claude-sonnet-4-6")
    return LLMClient(provider="agent_sdk", client=None, model=model)


def _legacy_key_based_client(max_retries: int = 3, base_delay: int = 1) -> LLMClient:
    """Preserve the old auto-detect order for callers that still want it.

    Kept because deleting it is a separate decision from making keyless the
    default, and nothing in-tree calls it today.

    Returns:
        LLMClient for whichever key is present.

    Raises:
        ValueError: If neither API key is set.

    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _create_anthropic_client()

    if os.environ.get("OPENAI_API_KEY"):
        print("🤖 LLM Provider: openai")
        return _create_openai_client(max_retries, base_delay)

    raise ValueError(
        "[LLM_CLIENT] No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.",
    )


def _call_agent_sdk(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 3000,
    temperature: float = 1.0,
) -> str:
    """Call Claude through the Agent SDK — no API key, no metered billing.

    Runs on the authenticated `claude` CLI / Claude subscription, which is the
    only LLM auth this repo permits (Operating Constraint #3).

    ``max_tokens`` and ``temperature`` are accepted for interface parity with the
    key-based providers but are not forwarded: `ClaudeAgentOptions` exposes
    neither, and silently pretending to honour them would be worse than plainly
    not doing so. Callers use them as advisory ceilings, and no in-tree caller
    depends on either being enforced.

    Args:
        system_prompt: System/context prompt.
        user_prompt: User message.
        max_tokens: Ignored; see above.
        temperature: Ignored; see above.

    Returns:
        The assistant's text, or ``""`` when the SDK yields nothing.

    Raises:
        ImportError: If claude_agent_sdk is not installed.

    """
    import asyncio

    try:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            TextBlock,
            query,
        )
    except ImportError as err:
        raise ImportError(
            "[LLM_CLIENT] claude_agent_sdk not installed. "
            "Install it: pip install claude-agent-sdk",
        ) from err

    async def _run() -> str:
        options = ClaudeAgentOptions(
            model=os.environ.get("AGENT_SDK_MODEL", "claude-sonnet-4-6"),
            system_prompt=system_prompt,
            max_turns=1,
            permission_mode="bypassPermissions",
            allowed_tools=[],
            mcp_servers={},
        )
        parts: list[str] = []
        async for message in query(prompt=user_prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
        return "".join(parts).strip()

    return asyncio.run(_run())


def _create_anthropic_client() -> LLMClient:
    """Create Anthropic client."""
    api_key = os.environ["ANTHROPIC_API_KEY"]

    try:
        from anthropic import Anthropic
    except ImportError as err:
        raise ImportError(
            "[LLM_CLIENT] anthropic package not installed. "
            "Install it: pip install anthropic",
        ) from err

    client = Anthropic(api_key=api_key)
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    print(f"   Model: {model}")
    return LLMClient("anthropic", client, model)


def create_async_anthropic_client(api_key: str | None = None) -> Any:
    """Create an ``AsyncAnthropic`` client for async vision/messages calls.

    ADR-002 factory route: keeps the ``anthropic`` import inside this
    exception-listed factory so callers in ``src/`` (e.g. the Stage 4 vision
    refinement helper) need not import ``anthropic`` directly.

    Args:
        api_key: Anthropic API key. Falls back to ``ANTHROPIC_API_KEY`` when
            not provided.

    Returns:
        A raw ``anthropic.AsyncAnthropic`` instance (not an ``LLMClient``
        wrapper — callers drive ``messages.create`` with async image blocks).

    Raises:
        ImportError: If the ``anthropic`` package is not installed.

    """
    key = api_key or os.environ["ANTHROPIC_API_KEY"]

    try:
        from anthropic import AsyncAnthropic
    except ImportError as err:
        raise ImportError(
            "[LLM_CLIENT] anthropic package not installed. "
            "Install it: pip install anthropic",
        ) from err

    return AsyncAnthropic(api_key=key)


def _create_openai_client(max_retries: int, base_delay: int) -> LLMClient:
    """Create OpenAI client with retry logic."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "[LLM_CLIENT] OPENAI_API_KEY not set. "
            "Export it: export OPENAI_API_KEY='sk-...'",
        )

    try:
        from openai import OpenAI, RateLimitError
    except ImportError as err:
        raise ImportError(
            "[LLM_CLIENT] openai package not installed. Install it: pip install openai",
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
                    f"(attempt {attempt + 1}/{max_retries})",
                )
                time.sleep(delay)
            else:
                raise ValueError(
                    f"[LLM_CLIENT] Rate limit exceeded after {max_retries} retries: {e}",
                ) from e
        except Exception as e:
            raise ValueError(f"[LLM_CLIENT] Failed to create OpenAI client: {e}") from e

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
    if llm_client.provider == "agent_sdk":
        return _call_agent_sdk(system_prompt, user_prompt, max_tokens, temperature)

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
        from scripts.token_usage import log_token_usage

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
        from scripts.token_usage import log_token_usage

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
