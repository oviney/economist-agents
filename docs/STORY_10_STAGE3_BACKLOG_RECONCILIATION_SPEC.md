# Spec: Story 10 Stage 3 Backlog Reconciliation

## Objective
Resolve the highest-priority uncompleted backlog item, Story 10: Phase 2 Migration (Stage 3 Content Gen). The original January 2026 task asks for a CrewAI Stage 3 migration, but ADR-0006 superseded ADR-0003 and selected Anthropic Agent SDK as the production runtime. Success means the backlog no longer directs engineers to reintroduce CrewAI for Stage 3, and active guardrails protect the current Agent SDK runtime.

## Tech Stack
- Python 3.13
- Pytest
- ADR-0006 Agent Framework Selection
- `src.agent_sdk.stage3_runner`
- `src.agent_sdk.stage4_runner`
- `.github/BACKLOG.md`

## Commands
- Targeted tests: `.venv/bin/pytest tests/test_destructive_change_guard.py tests/test_architecture_compliance.py::TestNoCrewAIInSrcOrTests -q`
- Lint touched files: `.venv/bin/ruff check scripts/destructive_change_guard.py tests/test_destructive_change_guard.py`
- Diff hygiene: `git diff --check`

## Project Structure
- `.github/BACKLOG.md` - authoritative backlog file because `docs/BACKLOG.md` is absent
- `docs/adr/0006-agent-framework-selection.md` - framework decision that supersedes the CrewAI migration
- `scripts/destructive_change_guard.py` - critical-file deletion guard
- `tests/test_destructive_change_guard.py` - regression tests for the guard

## Testing Strategy
Use deterministic tests to prove the destructive-change guard tracks current production runtime files. Use the existing architecture compliance test to prove live `src/` and `tests/` code remains free of CrewAI imports.

## Boundaries
- Always: follow ADR-0006; keep Stage 3 on Agent SDK.
- Ask first: reintroducing `src/crews/`, CrewAI dependencies, or a new orchestration framework.
- Never: implement the superseded CrewAI migration while ADR-0006 is accepted.

## Success Criteria
- Story 10 is no longer an uncompleted P1 backlog item.
- The duplicate Stage 3 CrewAI migration backlog entry is no longer ready work.
- No active test imports deleted `src.crews.stage3_crew`.
- Destructive-change guard protects current Agent SDK Stage 3/4 files.
