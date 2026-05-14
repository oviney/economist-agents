# ADR-0010: Migrate domain modules from scripts/ to src/

**Status:** Proposed
**Date:** 2026-05-12
**Decision Maker:** Staff engineer (review on #327)
**Supersedes:** —
**Superseded by:** —

## Context

Issue #327 (delete or archive ~80 dead files in `scripts/`) executed a
classification pass over the 115-file `scripts/` directory. The first
staff-engineer review (2026-05-10) approved a 44-file ARCHIVE set under
the spec boundary "do not edit any `src/` import." A second pre-execution
review on 2026-05-12 found that **seven** of those 44 files cannot be
archived without breaking live callers — and the callers are not in
`src/`, so they slipped past the first review's grep:

| Module | Live caller(s) |
|---|---|
| `scripts/agent_reviewer.py` | `agents/writer_agent.py:31`, `agents/research_agent.py:25`, `tests/test_quality_system.py:19` |
| `scripts/governance.py` | `agents/writer_agent.py:32`, `agents/research_agent.py:26` |
| `scripts/chart_metrics.py` | `agents/graphics_agent.py:31` |
| `scripts/schema_validator.py` | `tests/test_quality_system.py:20`; doc reference in `mcp_servers/publication_validator_server.py` |
| `scripts/agent_metrics.py` | `tests/test_quality_dashboard.py` (4× `patch("agent_metrics.…")`) |
| `scripts/defect_tracker.py` | `tests/test_quality_dashboard.py` (3× `patch("scripts.defect_tracker.…")`) |
| `scripts/validate_closed_loop.py` | `tests/test_closed_loop_validation.py` (3× subprocess invocation) |

All seven are imported via the bare-name `sys.path` hack established in
`tests/test_architecture_compliance.py:22` (and implicitly relied on at
runtime by the agent loader). The `agents/` modules use
`from agent_reviewer import …`, not `from scripts.agent_reviewer import …`,
because `scripts/` is prepended to `sys.path` before import.

Four of the seven (`governance`, `agent_reviewer`, `chart_metrics`, plus
`schema_validator`'s validator role) carry **real domain semantics**:
governance tracking, quality review, chart instrumentation, schema
contracts. These are not script utilities — they are application
components that happen to live under `scripts/` for historical reasons.

## Decision

We will migrate domain modules out of `scripts/` and into appropriate
`src/` subpackages, then remove the `sys.path.insert(scripts/)` hack.
Specifically:

1. Relocate the seven KEEP-by-caller modules from `scripts/` to a new
   `src/economist_agents/quality/` (or similar) subpackage, with proper
   `__init__.py` and absolute imports.
2. Update `agents/writer_agent.py`, `agents/research_agent.py`,
   `agents/graphics_agent.py`, `tests/test_quality_system.py`,
   `tests/test_quality_dashboard.py`, and `tests/test_closed_loop_validation.py`
   to use the new import paths.
3. Remove `sys.path.insert(0, str(SCRIPTS_DIR))` from
   `tests/test_architecture_compliance.py` once nothing depends on it.
4. After this migration, re-open issue #327's archive scope and move the
   seven modules to `scripts/archived/` under the now-unblocked path.

This is intentionally **out of scope for #327**. #327 is a cleanup
ticket; rewriting agent imports is application architecture work and
deserves its own spec, review, and rollback plan.

## Alternatives Considered

1. **Refactor the callers inside #327's PR.** Rejected — violates the
   spec §4 boundary against editing application imports, doubles the
   blast radius of a cleanup ticket, and conflates two different risk
   profiles (delete dead code vs. relocate live code) in one review.

2. **Leave the seven in `scripts/` forever.** Rejected — accepts the
   architectural debt indefinitely. Future cleanup passes will re-flag
   these same seven files, and the `sys.path` hack continues to mask
   import-graph problems.

3. **Move the seven to `scripts/archived/` and add `scripts/archived/`
   to `sys.path`.** Rejected — defeats the purpose of archiving (the
   modules are still importable from anywhere) and doubles down on the
   `sys.path` hack rather than removing it.

## Consequences

- **Positive:** Removes the `sys.path` hack. Makes domain modules
  discoverable in `src/` where engineers expect them. Unblocks the
  final 7 archive moves under #327. Tightens the architecture
  compliance test (no more bare-name imports from `scripts/`).
- **Negative:** Touches six live files across `agents/` and `tests/`.
  Carries real regression risk — mocks patched on `agent_metrics.…`
  and `scripts.defect_tracker.…` paths must be updated in lockstep.
- **Follow-up:** Open a new issue tracking this ADR's implementation,
  link it as "depends on" / "follow-up to" #327. After implementation,
  amend SPEC.md or open a #327-followup spec to archive the seven.
- **Revisit if:** Anthropic Agent SDK or a future framework re-introduces
  a `sys.path` convention that makes co-locating these modules with
  `scripts/` more natural again.

## References

- Issue: oviney/economist-agents#327
- Spec: [SPEC.md](../../SPEC.md) §2 KEEP table — entries marked †
- Architecture compliance test: `tests/test_architecture_compliance.py:22`
  (the `sys.path.insert` to be removed)
- ADR-0002: agent-registry-pattern (related — the seven modules predate
  the registry pattern and never got migrated)
