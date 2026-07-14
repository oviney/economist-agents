#!/usr/bin/env python3
"""The deprecated scripts/economist_agent.py path must fail loudly and helpfully
when run keyless (B-006 T4), pointing at the subscription pipeline instead of
raising a raw client error deep in the run.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

import scripts.economist_agent as ea


def test_abort_if_keyless_exits_with_guidance(capsys) -> None:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
    }
    with patch.dict(os.environ, env, clear=True), pytest.raises(SystemExit) as exc:
        ea._abort_if_keyless()
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "src.agent_sdk.pipeline" in err
    assert "--research-mode claude_web" in err


def test_abort_if_keyless_noop_when_key_present() -> None:
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "x"}):
        # Must not raise when a key is available.
        ea._abort_if_keyless()
