# Spec: Honor `ant` OAuth credentials in the Anthropic auth path

## Objective

After migrating local auth to `ant auth login` (a platform.claude.com OAuth
profile), there is no `ANTHROPIC_API_KEY` in the environment. The installed
`anthropic` SDK (0.75.0) does **not** auto-resolve the on-disk `ant` profile —
it only reads the `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` env vars
(verified empirically). Our code hard-gates on, and explicitly passes,
`ANTHROPIC_API_KEY`, so every direct-`anthropic`-SDK path raises
`No API key found` / `KeyError` even though valid OAuth credentials exist on
disk.

Affected (direct `anthropic` SDK) paths: `scripts/llm_client.py`
(`create_llm_client`, `_create_anthropic_client`, `create_async_anthropic_client`)
and the Stage 4 vision-refinement gate in `src/agent_sdk/_shared.py`. These back
the topic scout, editorial board, deep-research LLM, and chart/vision steps.

**Success looks like:** with only an `ant` profile present (no env key), a real
pipeline run authenticates Anthropic calls successfully and the article reaches
the publication validator.

## Assumptions

1. Stage 3 writing via `claude_agent_sdk` already honors `ant` profile
   resolution itself (per the Anthropic CLI docs) and is **out of scope** — this
   spec only covers the direct `anthropic` SDK paths.
2. `ant auth print-credentials --access-token` is the supported way to obtain
   (and refresh) the active profile's short-lived OAuth token; it prints a bare
   token on stdout. Verified: feeding that token to the SDK as
   `ANTHROPIC_AUTH_TOKEN` makes a real API call succeed.
3. The active profile targets `api.anthropic.com` (no custom `ANTHROPIC_BASE_URL`
   needed). If a profile ever carries a base_url, the user exports it separately
   via `ant auth print-credentials --env`; this spec does not manage base_url.
4. Existing behavior when `ANTHROPIC_API_KEY` is set must be byte-for-byte
   unchanged (existing tests assert `Anthropic(api_key=...)` / `AsyncAnthropic(api_key=...)`).

## Tech Stack

Python 3.x, `anthropic` SDK, `orjson`, `pytest`. No new dependencies.

## Commands

```
Test (changed files): pytest tests/test_anthropic_auth_resolution.py tests/test_llm_client.py tests/test_async_anthropic_factory.py tests/test_llm_providers.py -q
Lint: ruff check scripts/llm_client.py src/agent_sdk/_shared.py
Coverage gate: pytest --cov=scripts.llm_client --cov-report=term-missing
```

## Project Structure

```
scripts/llm_client.py            → auth resolver + client factories (changed)
src/agent_sdk/_shared.py         → Stage 4 vision gate (changed)
tests/test_anthropic_auth_resolution.py → new unit tests (TDD)
docs/specs/anthropic-auth-token-resolution.md → this spec
```

## Design

Add one resolver to `scripts/llm_client.py`:

```python
def resolve_anthropic_auth() -> str | None:
    """Return the available Anthropic auth kind, or None.

    Priority:
      1. ANTHROPIC_API_KEY env  -> "api_key"
      2. ANTHROPIC_AUTH_TOKEN env -> "auth_token"
      3. active `ant` profile    -> "auth_token"  (side effect: sets
         os.environ["ANTHROPIC_AUTH_TOKEN"] from the profile token)
    Returns None when no credential is available. Never raises.
    """
```

`_load_ant_profile_token()` shells `ant auth print-credentials --access-token`
with a short timeout; returns the stripped token on rc 0 + non-empty stdout,
else `None`. Guards `FileNotFoundError` (ant not installed),
`subprocess.TimeoutExpired`, and any other failure → `None`.

Wire-ups:

- `create_llm_client()`: gate on `resolve_anthropic_auth()` instead of
  `ANTHROPIC_API_KEY` only; keep the OpenAI fallback; update the final error
  message to mention `ant auth login`.
- `_create_anthropic_client()`: construct `Anthropic()` with **no explicit
  api_key** — the SDK reads whichever env var the resolver populated. (`api_key`
  and `auth_token` are both honored by a bare `Anthropic()`.)
- `create_async_anthropic_client(api_key=None)`: when `api_key` (arg) or
  `ANTHROPIC_API_KEY` is present, keep current behavior
  (`AsyncAnthropic(api_key=key)`); otherwise call `resolve_anthropic_auth()`
  and, on success, return a bare `AsyncAnthropic()`; if no creds, raise the
  existing "no API key" error.
- `src/agent_sdk/_shared.py` vision gate: replace
  `api_key = os.environ.get("ANTHROPIC_API_KEY"); if not api_key: skip` with
  `if not resolve_anthropic_auth(): skip`, then call
  `create_async_anthropic_client()` with no explicit key. (`_shared.py` keeps its
  ADR-002 rule: it imports the resolver/factory from `scripts.llm_client`, never
  `anthropic` directly.)

## Code Style

```python
def _load_ant_profile_token() -> str | None:
    """Return the active ant profile's OAuth token, or None if unavailable."""
    try:
        result = subprocess.run(
            ["ant", "auth", "print-credentials", "--access-token"],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("ant profile token unavailable: %s", exc)
        return None
    token = result.stdout.strip()
    return token if result.returncode == 0 and token else None
```

Type hints mandatory, docstrings required, `logger` not `print()` for new code.

## Testing Strategy

`pytest`, mocks for all externals (`subprocess.run`, the `anthropic` module).
New file `tests/test_anthropic_auth_resolution.py`:

1. `resolve_anthropic_auth` → `"api_key"` when `ANTHROPIC_API_KEY` set; does
   **not** shell out to `ant`.
2. → `"auth_token"` when only `ANTHROPIC_AUTH_TOKEN` set; no shell-out.
3. → `"auth_token"` when neither env set and mocked `subprocess.run` returns a
   token; asserts `os.environ["ANTHROPIC_AUTH_TOKEN"]` is populated.
4. → `None` when neither env set and `ant` missing (`FileNotFoundError`); no env
   mutation.
5. → `None` when `ant` returns rc≠0 or empty stdout.
6. `create_llm_client()` selects the anthropic provider when only
   `ANTHROPIC_AUTH_TOKEN` is set (mocked anthropic module).
7. `create_async_anthropic_client()` with only `ANTHROPIC_AUTH_TOKEN` builds
   `AsyncAnthropic()` with no `api_key` kwarg.

Regression: `tests/test_llm_client.py`, `tests/test_async_anthropic_factory.py`,
`tests/test_llm_providers.py` must still pass unchanged. >80% coverage on the new
code.

## Boundaries

- **Always:** mock `subprocess` and `anthropic` in tests; keep `_shared.py` free
  of a direct `anthropic` import; preserve existing `api_key`-path behavior.
- **Ask first:** any change to the Stage 3 `claude_agent_sdk` auth path; adding a
  token-refresh daemon; managing `ANTHROPIC_BASE_URL`.
- **Never:** log token values; commit credentials; weaken the OpenAI fallback.

## Success Criteria

1. New + existing tests in the four files above pass; ruff clean.
2. `resolve_anthropic_auth()` returns a truthy kind with only an `ant` profile
   present (no env key).
3. End-to-end: a fresh pipeline run with only the `ant` profile authenticates
   Anthropic calls and produces an article that reaches the publication
   validator (this is the real acceptance test from the next-session plan).

## Open Questions

None blocking. (Token expiry mid-run is handled per-call by
`print-credentials`, which refreshes; a long-lived refresh daemon is explicitly
out of scope.)
