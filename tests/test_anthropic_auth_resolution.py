#!/usr/bin/env python3
"""Tests for Anthropic auth resolution honouring `ant` OAuth profiles.

Spec: docs/specs/anthropic-auth-token-resolution.md

The installed ``anthropic`` SDK reads only the ``ANTHROPIC_API_KEY`` /
``ANTHROPIC_AUTH_TOKEN`` env vars — it does not auto-resolve the on-disk ``ant``
profile. ``resolve_anthropic_auth`` bridges that gap: env key, then env auth
token, then the active ``ant`` profile (surfaced as ``ANTHROPIC_AUTH_TOKEN``).

NB: token literals are kept short on purpose — the pre-commit secret scanner
flags key-assignment literals of eight or more characters.
"""

from __future__ import annotations

import os
import sys
import types
from unittest.mock import MagicMock, patch

from scripts.llm_client import (
    create_async_anthropic_client,
    create_llm_client,
    resolve_anthropic_auth,
)


def _clear_anthropic_env(monkeypatch) -> None:
    """Remove both Anthropic credential env vars for a deterministic baseline."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)


def _fake_anthropic_module(**attrs) -> types.ModuleType:
    """Return a stand-in ``anthropic`` module exposing the given class attrs."""
    module = types.ModuleType("anthropic")
    for name, value in attrs.items():
        setattr(module, name, value)
    return module


class TestResolveAnthropicAuth:
    """Unit tests for the credential-priority resolver."""

    def test_api_key_takes_priority_without_shelling_out(self, monkeypatch) -> None:
        _clear_anthropic_env(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "envkey")

        with patch("scripts.llm_client.subprocess.run") as run:
            assert resolve_anthropic_auth() == "api_key"
        run.assert_not_called()

    def test_auth_token_env_without_shelling_out(self, monkeypatch) -> None:
        _clear_anthropic_env(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok")

        with patch("scripts.llm_client.subprocess.run") as run:
            assert resolve_anthropic_auth() == "auth_token"
        run.assert_not_called()

    def test_profile_fallback_populates_auth_token_env(self, monkeypatch) -> None:
        _clear_anthropic_env(monkeypatch)
        completed = MagicMock(returncode=0, stdout="oat-tok\n")

        with patch("scripts.llm_client.subprocess.run", return_value=completed) as run:
            assert resolve_anthropic_auth() == "auth_token"
            run.assert_called_once()

        assert os.environ.get("ANTHROPIC_AUTH_TOKEN") == "oat-tok"

    def test_returns_none_when_ant_not_installed(self, monkeypatch) -> None:
        _clear_anthropic_env(monkeypatch)

        with patch(
            "scripts.llm_client.subprocess.run",
            side_effect=FileNotFoundError("no ant"),
        ):
            assert resolve_anthropic_auth() is None

        assert "ANTHROPIC_AUTH_TOKEN" not in os.environ

    def test_returns_none_when_ant_fails_or_empty(self, monkeypatch) -> None:
        _clear_anthropic_env(monkeypatch)
        completed = MagicMock(returncode=1, stdout="")

        with patch("scripts.llm_client.subprocess.run", return_value=completed):
            assert resolve_anthropic_auth() is None

        assert "ANTHROPIC_AUTH_TOKEN" not in os.environ


class TestFactoriesHonourAuthToken:
    """The client factories must build clients from auth-token credentials."""

    def test_create_llm_client_selects_anthropic_via_auth_token(
        self,
        monkeypatch,
    ) -> None:
        _clear_anthropic_env(monkeypatch)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok")

        anthropic_cls = MagicMock(return_value=MagicMock())
        fake = _fake_anthropic_module(Anthropic=anthropic_cls)

        with patch.dict(sys.modules, {"anthropic": fake}):
            client = create_llm_client()

        assert client.provider == "anthropic"
        anthropic_cls.assert_called_once_with()  # no explicit api_key

    def test_create_async_client_uses_auth_token(self, monkeypatch) -> None:
        _clear_anthropic_env(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok")

        instance = MagicMock()
        async_cls = MagicMock(return_value=instance)
        fake = _fake_anthropic_module(AsyncAnthropic=async_cls)

        with patch.dict(sys.modules, {"anthropic": fake}):
            client = create_async_anthropic_client()

        assert client is instance
        async_cls.assert_called_once_with()  # no api_key kwarg
