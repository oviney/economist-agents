"""Shared stdin/stdout plumbing for the harness hooks (B-030).

The harness speaks to a hook over pipes: a JSON object on stdin, a JSON object on stdout.
That makes stdout a *return channel*, not a log — so anything diagnostic must go to stderr
or it corrupts the response. This module centralises both halves plus the never-crash
wrapper, so no individual hook has to remember either rule.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import Any

import orjson

logger = logging.getLogger(__name__)

#: A hook handler: harness payload in, response payload out.
Handler = Callable[[dict[str, Any]], dict[str, Any]]


def read_payload(raw: str | None = None) -> dict[str, Any]:
    """Parse the harness payload, tolerating anything.

    Args:
        raw: JSON text. Reads stdin when omitted.

    Returns:
        The parsed object, or ``{}`` for malformed input, non-object JSON, or a read
        failure. A hook with no payload does nothing, which is the correct degradation.

    """
    if raw is None:
        try:
            raw = sys.stdin.read()
        except OSError as exc:  # pragma: no cover — stdin closed under us
            logger.warning("hook could not read stdin: %s", exc)
            return {}

    if not raw or not raw.strip():
        return {}

    try:
        parsed = orjson.loads(raw)
    except orjson.JSONDecodeError:
        logger.warning("hook received malformed JSON on stdin")
        return {}

    return parsed if isinstance(parsed, dict) else {}


def emit_payload(payload: dict[str, Any]) -> None:
    """Write a hook response to stdout — the harness's only return channel.

    An empty payload writes nothing at all: emitting a bare ``{}`` would put noise in the
    transcript on every silent success, and a hook that is quiet when clean is the
    difference between a sensor and the alert nobody reads.

    Args:
        payload: The response object.

    """
    if not payload:
        return
    sys.stdout.write(orjson.dumps(payload).decode())


def run(handler: Handler) -> int:
    """Execute ``handler`` under the never-crash guarantee.

    Args:
        handler: Function taking the harness payload and returning a response.

    Returns:
        Always 0. A hook must not be able to fail the tool call it observes; on any
        unexpected exception the response is dropped and the session continues.

    """
    try:
        emit_payload(handler(read_payload()))
    except Exception as exc:  # noqa: BLE001 — the whole point is to swallow everything
        logger.warning("hook failed, degrading to no-op: %s", exc)
    return 0
