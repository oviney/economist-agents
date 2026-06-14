#!/usr/bin/env python3
"""Unit tests for ``create_async_anthropic_client`` (B-001, ADR-002 route).

``src/agent_sdk/_shared.py`` must not import ``anthropic`` directly — it is not
in the arch-check ``LLM_IMPORT_EXCEPTIONS`` list. This factory lives in the
exception-listed ``scripts/llm_client.py`` so the Stage 4 vision-refinement
helper can obtain an ``AsyncAnthropic`` client without a prohibited import.

NB: key values here are kept short on purpose — the pre-commit secret scanner
flags key-assignment literals of eight or more characters.
"""

from __future__ import annotations

import os
import types
from unittest.mock import MagicMock, patch

import pytest

from scripts.llm_client import create_async_anthropic_client


def _fake_anthropic_module(async_class: MagicMock) -> types.ModuleType:
    """Return a stand-in ``anthropic`` module exposing *async_class*."""
    module = types.ModuleType("anthropic")
    module.AsyncAnthropic = async_class  # type: ignore[attr-defined]
    return module


def test_returns_async_anthropic_client_built_from_env_key() -> None:
    """Factory returns the AsyncAnthropic instance, keyed from the env var."""
    import sys

    instance = MagicMock()
    async_class = MagicMock(return_value=instance)

    with (
        patch.dict(os.environ, {"ANTHROPIC_API_KEY": "envkey"}),
        patch.dict(sys.modules, {"anthropic": _fake_anthropic_module(async_class)}),
    ):
        client = create_async_anthropic_client()

    assert client is instance
    async_class.assert_called_once_with(api_key="envkey")


def test_explicit_api_key_overrides_env() -> None:
    """An explicit api_key argument wins over the environment variable."""
    import sys

    instance = MagicMock()
    async_class = MagicMock(return_value=instance)

    with (
        patch.dict(os.environ, {"ANTHROPIC_API_KEY": "envkey"}),
        patch.dict(sys.modules, {"anthropic": _fake_anthropic_module(async_class)}),
    ):
        client = create_async_anthropic_client(api_key="argkey")

    assert client is instance
    async_class.assert_called_once_with(api_key="argkey")


def test_raises_import_error_when_anthropic_missing() -> None:
    """A clear ImportError is raised when the anthropic package is absent."""
    import builtins
    import sys

    real_import = builtins.__import__

    def _blocked_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "anthropic":
            raise ImportError("no anthropic")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    with (
        patch.dict(os.environ, {"ANTHROPIC_API_KEY": "envkey"}),
        patch.dict(sys.modules, {"anthropic": None}),
        patch.object(builtins, "__import__", _blocked_import),
        pytest.raises(ImportError, match="anthropic package not installed"),
    ):
        create_async_anthropic_client()
