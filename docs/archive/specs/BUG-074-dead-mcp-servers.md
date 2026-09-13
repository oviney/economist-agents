# BUG-074 · Five MCP servers are configured, enabled, and dead

**Status:** APPROVED — owner LGTM 2026-09-01
**Date:** 2026-09-01
**Backlog:** BUG-074 (MEDIUM)

## Objective

Every Python MCP server in `.mcp.json` fails `CONNECTION_CLOSED` at session
start, including this session. Make them start.

## Root cause — verified in both directions

`.mcp.json` launches each server with `python3`, the system interpreter:

```
$ python3 -c "import mcp"
ModuleNotFoundError: No module named 'mcp'

$ .venv/bin/python -c "import mcp"     # no output — imports fine
```

All five import cleanly under the venv interpreter and none under `python3`:

| Server | `.venv/bin/python` | `python3` |
|---|---|---|
| `article-evaluator` | imports OK | ModuleNotFoundError |
| `style-memory` | imports OK | ModuleNotFoundError |
| `publication-validator` | imports OK | ModuleNotFoundError |
| `web-researcher` | imports OK | ModuleNotFoundError |
| `published-topics` | imports OK | ModuleNotFoundError |

## Three corrections to the BACKLOG entry

The entry was written from inference. Two of its claims are false, and a third
failure it names has a different cause entirely.

1. **`web-researcher` is not Serper and needs no key.** The entry calls it a
   "dormant paid surface" and recommends dropping it. Its own docstring says it
   exposes "free arXiv academic search and page-fetching … without a paid
   web-search API", and the code confirms it: `search_arxiv` via
   `scripts/arxiv_search`, and `fetch_page` via `requests`. There is no Serper
   call and no API key. It gets fixed like the other four.
2. **`image-generator` is not in `.mcp.json`.** The entry names it as a second
   paid surface a blanket fix would revive. `mcp_servers/image_generator_server.py`
   exists on disk and does want `OPENAI_API_KEY`, but it is not configured, not
   enabled, and not started. Nothing revives it.
   → **There is no paid surface among the configured servers, so the "decide
   first" fork the entry raises does not exist.** All five are keyless and the
   fix is uniform. `tests/test_harness_config.py::test_mcp_json_requires_no_api_key`
   already guards the file against regaining one.
3. **The entry says six servers; five are Python.** The sixth failure this
   session is `playwright`, and it is a different bug — see below.

## Two failures that are *not* this bug

Both were found while verifying the above. Neither is fixed here; both get
backlog entries.

- **`playwright`** runs `npx @playwright/mcp@latest --extension` and fails on
  the Node version, not Python:
  `EBADENGINE required: { node: '>=20' }, current: { node: 'v18.19.1' }`.
  Fixing it means upgrading Node (root) or pinning an older `@playwright/mcp`.
- **`plugin:github:github`** fails with
  `400 Authorization header is badly formatted` — a plugin credential problem,
  not a `.mcp.json` entry at all.

## What this is worth — stated honestly, because it is less than it looks

These servers are **not** pipeline infrastructure. `src/agent_sdk/stage3_runner.py`
builds its research tools in-process with `create_sdk_mcp_server`, and reaches
style memory by importing `src.tools.style_memory_tool` directly. The pipeline
runs correctly today with all five dead, which is why this went unnoticed.

What the fix buys is the *agent session's* toolset: an interactive session
currently has no `publication-validator`, no `published-topics` dedupe check,
and no `style-memory` lookup, and silently does the work by hand instead. That
is worth a one-line-per-server fix. It is not worth more than that, and this
spec does not propose more.

## Scope

**In:**
- `.mcp.json`: `python3` → `.venv/bin/python` for all five Python servers.
- A regression test in `tests/test_harness_config.py` asserting no server is
  launched with a bare `python3`.
- Correct the BUG-074 backlog entry (the three errors above) and close it.
- File the two out-of-scope failures as their own entries.

**Out:**
- `playwright` / the Node upgrade. Separate cause, needs root.
- The `github` plugin credential. Separate surface.
- `image_generator_server.py` and `blog_deployer_server.py` on disk but
  unconfigured. Deleting dormant code is a decision, not a bug fix.
- Making any server a pipeline dependency. They are session tools.

## Design

Change the interpreter, nothing else:

```diff
-  "command": "python3",
+  "command": ".venv/bin/python",
   "args": ["mcp_servers/article_evaluator_server.py"]
```

**Why a relative path, not absolute.** The existing `args` are already relative
(`mcp_servers/article_evaluator_server.py`) and they resolve — the servers were
found and started, then died importing `mcp`. That is direct evidence the
server process cwd is the repo root, so `.venv/bin/python` resolves by the same
mechanism. An absolute `/home/ouray/...` would break on any other machine, which
matters because CLAUDE.md keeps these constraints in the repo precisely so they
survive a machine change.

## Testing strategy

`tests/test_harness_config.py` already owns assertions about `.mcp.json`
(`test_mcp_json_requires_no_api_key`, `test_no_mcp_server_declares_an_env_requirement`).
The new test goes beside them: every `mcpServers[*].command` that names a Python
interpreter must be `.venv/bin/python`, never bare `python3`.

A test that starts each server over stdio would be stronger, but it is a
multi-second subprocess per server in a suite that already runs 2:10. The
import-level failure is the entire bug, and the config assertion catches the
regression that caused it.

## Success criteria

1. All five Python servers connect at session start — no `CONNECTION_CLOSED`.
   *Verified by the owner restarting the session; I cannot observe my own
   MCP startup mid-session.*
2. `tests/test_harness_config.py` fails if any server regains a bare `python3`.
3. `make ci-local` shows no new failures against the recorded baseline
   (2788 passed / 9 skipped / 1 pre-existing `test_python_version_consistency`
   failure / 84%).
4. `.mcp.json` still declares no API key and no `env` block — the two existing
   guards stay green.

## Boundaries

- **Always:** keep paths relative; run `make ci-local` before commit.
- **Ask first:** deleting any `mcp_servers/*.py`, adding a server to
  `.mcp.json`, or touching the `github` plugin credential.
- **Never:** configure a server that needs an API key (constraints #1–#3);
  hardcode an absolute machine path.

## Open questions

None. Criterion 1 needs your session restart to confirm, which is a
verification step, not an unresolved decision.
