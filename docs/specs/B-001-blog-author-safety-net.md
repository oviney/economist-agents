# Spec: B-001 · Wire Stage 4 author safety net to `BLOG_AUTHOR`

> Backlog item: **B-001** (`type:refactor`, was #420). Slice 3 of the
> 2026-06-14 "clear the backlog" sprint. Follow-up from PR #416 (issue #401).

## Objective

The production author name must live in exactly one place (`BLOG_AUTHOR` in
`scripts/publication_validator.py:32`) and flow from there into every stage that
emits or checks it. Today the Stage 4 frontmatter safety net hard-codes the
author as a string literal:

```python
# src/agent_sdk/_shared.py:632
fm = fm.rstrip() + '\nauthor: "Ouray Viney"\n'
```

If `BLOG_AUTHOR` ever changes, this literal silently drifts and the safety net
will inject an author the publication validator then rejects. **Goal:**
interpolate `BLOG_AUTHOR` here so the constant is the single source of truth.

**Why it was deferred (the real work in this slice):** `_shared.py` carries a
pre-existing **ADR-002 violation** — `import anthropic` inside
`refine_image_metadata` (line 734). The `pre_commit_arch_check.py` gate blocks
*any* edit to a file that imports a prohibited LLM library directly, so we
cannot touch line 632 until the import is routed through a compliant module.

Success = the constant is wired, the ADR-002 gate passes on `_shared.py`, and
the existing author-contract tests become load-bearing against `BLOG_AUTHOR`.

## Scope

**In scope**
1. Add an async Anthropic client factory to `scripts/llm_client.py` (the sole
   LLM-client factory; already in `LLM_IMPORT_EXCEPTIONS`).
2. Replace `import anthropic` + `AsyncAnthropic(...)` in `_shared.py`'s
   `refine_image_metadata` with a call to that factory.
3. Interpolate `BLOG_AUTHOR` into the Stage 4 safety net at `_shared.py:632`.

**Out of scope** (non-negotiable — scope discipline)
- Extending `AgentRegistry` with async/vision support (the backlog's "route via
  AgentRegistry" note is aspirational; AgentRegistry has no async/vision path,
  and building one is disproportionate to this slice — see Decision below).
- Any behaviour change to vision refinement, frontmatter assembly, or the
  validator beyond removing the author literal.
- Refactoring the other exception-file violations (`featured_image_agent.py`,
  `visual_qa.py`).

## Decision: clear ADR-002 via the `llm_client.py` factory

**Chosen (human-confirmed):** Add a thin `create_async_anthropic_client()` to
`scripts/llm_client.py` and call it from `_shared.py`.

- `scripts/llm_client.py` is already an ADR-002 exception file and is *the* sole
  factory for LLM client creation — adding the async sibling of the existing
  `_create_anthropic_client()` keeps client construction in one compliant place.
- `_shared.py` then imports a plain function (`from scripts.llm_client import
  create_async_anthropic_client`) — no prohibited import remains, so the AST
  gate passes. Verified: `scripts/llm_client.py` imports nothing from `src/`, so
  no circular import is introduced.

**Rejected:** Extending `AgentRegistry` (too large for this slice; new async
provider + vision content-block helper + registry tests). Adding `_shared.py` to
`LLM_IMPORT_EXCEPTIONS` (entrenches the violation rather than fixing it; against
ADR-002 intent).

## Commands

```
Test (targeted):   .venv/bin/pytest tests/test_author_contract.py -q
Test (vision):     .venv/bin/pytest tests/ -k "refine_image or vision or _shared" -q
ADR-002 gate:      .venv/bin/python scripts/pre_commit_arch_check.py src/agent_sdk/_shared.py scripts/llm_client.py
Lint:              .venv/bin/ruff check src/agent_sdk/_shared.py scripts/llm_client.py
Full suite:        .venv/bin/pytest -q
```

## Code Style

New factory mirrors the existing `_create_anthropic_client()` (lazy import,
typed, docstring, raises a clear `ImportError`):

```python
def create_async_anthropic_client(api_key: str | None = None) -> Any:
    """Create an AsyncAnthropic client for async vision/messages calls.

    ADR-002 factory route: keeps the ``anthropic`` import inside this
    exception-listed factory so callers in ``src/`` need not import it directly.
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
```

Returns the raw `AsyncAnthropic` (not an `LLMClient` wrapper) because the caller
needs the async `messages.create` with image content blocks; the `LLMClient`
wrapper exists for the unified *sync* path and would not fit here.

Caller change in `_shared.py` `refine_image_metadata` (keeps the lazy-import
style already used in that function):

```python
# remove:  import anthropic as _anthropic
from scripts.llm_client import create_async_anthropic_client
...
client = create_async_anthropic_client(api_key)   # was _anthropic.AsyncAnthropic(api_key=api_key)
```

Safety-net change at `_shared.py:632`:

```python
from scripts.publication_validator import BLOG_AUTHOR   # lazy, inside apply_editorial_fixes
...
if "author:" not in fm:
    fm = fm.rstrip() + f'\nauthor: "{BLOG_AUTHOR}"\n'
```

## Testing Strategy

`tests/test_author_contract.py` already encodes the target behaviour. Two
changes make it load-bearing rather than describing the literal:

- `test_safety_net_emits_the_production_author_when_missing` (lines 43–53)
  already asserts the *observable* output equals `BLOG_AUTHOR` — it passes today
  by coincidence (literal == constant) and will pass by *construction* after the
  wiring. Update its docstring note that called out the not-yet-wired state.
- Add one regression test proving the link is dynamic: monkeypatch /
  parametrise so that a non-default author value flowing through the safety net
  proves it reads the constant, not a literal. (If patching the constant is
  awkward given import timing, assert via a comment-documented dynamic check
  that `apply_editorial_fixes` output author == imported `BLOG_AUTHOR`.)

Vision path: existing `_shared` / image-mode tests must still pass — they mock
the Anthropic client; confirm the mock target still resolves after the factory
swap (tests that patch `anthropic.AsyncAnthropic` or `_shared`'s client may need
their patch target updated to `scripts.llm_client.create_async_anthropic_client`).

TDD order: write/adjust the failing author test first, then wire the constant;
swap the client factory under the protection of the existing vision tests.

## Boundaries

- **Always:** run the ADR-002 gate + targeted tests + full suite before PR;
  branch off `main`; keep the diff to the three files above (+ test file).
- **Ask first:** any change to `AgentRegistry`, the gate's exception list, or
  the vision/frontmatter behaviour.
- **Never:** commit the `import anthropic` workaround as an exception entry;
  change `BLOG_AUTHOR`'s value; touch unrelated `_shared.py` helpers.

## Success Criteria

1. `scripts/pre_commit_arch_check.py src/agent_sdk/_shared.py` exits 0 (no
   `import anthropic` in `_shared.py`).
2. `_shared.py:632` interpolates `BLOG_AUTHOR`; grep for the `"Ouray Viney"`
   literal in `_shared.py` returns nothing.
3. `tests/test_author_contract.py` passes and at least one test fails if the
   safety net is reverted to a literal (proves the link is load-bearing).
4. Vision refinement behaviour unchanged: image-mode / `_shared` tests pass.
5. Full suite green; ruff clean; all CI checks green on the PR.

## Open Questions

_(none — design decision resolved; circular-import and gate-wiring facts verified.)_
