"""Claude Code harness hooks (B-030).

Every computational sensor in this repo — ruff, mypy, pytest, bandit, four custom guards —
fired at the *owner's* gate: `pre-commit`, `pre-push`, `make ci-local`. An agent could
write hundreds of lines, end its turn with the tree red, and no signal would ever reach it;
the owner discovered it later, with the agent's context already stale. The audit
(`docs/reviews/harness-engineering-assessment-2026-07-29.md`) graded that **F**, because the
sensor inventory was strong and entirely unwired.

These modules are the wiring. Each one is invoked by `.claude/settings.json`, reads the
harness's JSON payload from stdin, and writes a JSON response to stdout.

Two invariants hold across all of them:

1. **Exit 0, always.** A hook that raises would break the session it is meant to protect.
   Failure degrades to *no sensor*, never to a blocked developer.
2. **Anything that blocks is bounded.** The `Stop` gate blocks at most once per session;
   an unbounded blocking `Stop` hook is a trap, not a gate.
"""
