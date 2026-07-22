# ADR-0015: Local-First Verification — Retire GitHub Actions CI

**Status:** Accepted
**Date:** 2026-07-22
**Decision Maker:** Ouray Viney (Engineering Lead)
**Supersedes:** [ADR-0004](0004-python-version-constraint.md)
**Superseded by:**

## Context

[ADR-0014](0014-retire-paid-github-actions-generation.md) moved article
*generation* out of GitHub Actions and onto the Claude subscription, run locally.
The same reasoning applies to *verification*: the owner wants zero dependency on
external CI infrastructure, and prefers running on tools already installed.

The facts that make this practical:

- **`main` is not branch-protected** — no CI status check is required to merge
  today. CI has been advisory, not a gate.
- **Local tooling already exists** — a `Makefile` and `.pre-commit-config.yaml`
  run ruff, mypy, and pytest. They were merely *weaker* than `ci.yml` (single
  Python vs a 3.11+3.12 matrix; 40% coverage on `scripts` vs 70% on
  `src`+`scripts` plus a `src/quality` 90% gate; no destructive-change guard; no
  bandit).
- **GitHub Actions has been unreliable** — the content pipeline failed 8 weeks
  running (retired in ADR-0014), and Actions stopped triggering repo-wide during
  this work. (The repo is *public*, so Actions is free — this is about
  independence, not cost.)

The legacy multi-version test matrix (3.11 + 3.12) traces to
[ADR-0004](0004-python-version-constraint.md), which constrained the project for
**CrewAI** compatibility. CrewAI was removed ([ADR-0006](0006-agent-framework-selection.md));
that constraint is moot, and the matrix did not even match the 3.13 runtime.

## Decision

We will make **local tooling the source of truth for verification** and retire
the GitHub Actions quality workflows.

- `make ci-local` reproduces every gate `ci.yml` enforced — ruff format + lint,
  the bare-name-import check, mypy (advisory, as in CI), pytest with
  `--cov=src --cov=scripts --cov-fail-under=70` plus the `src/quality` 90%
  per-module gate, bandit, and the destructive-change guard. `.pre-commit-config.yaml`
  runs the same gates per commit. Run `make ci-local` before merging — **you are
  the gate** (`main` is unprotected).
- Delete `.github/workflows/ci.yml`, `quality-tests.yml`, and `sync-copilot.yml`
  (the last an auto-commit bot, not a gate).
- **Pin a single Python version** (`.python-version`), superseding ADR-0004: this
  is a solo, locally-run project, not a library shipped across interpreters, so
  the 3.11+3.12 matrix is retired.
- Free, non-gate Actions that don't touch verification — `docs.yml` (GitHub
  Pages) and `copilot-setup-steps.yml` — are **kept**; whether to retire GitHub
  Copilot entirely is a separate decision.

## Alternatives Considered

1. **Keep GitHub Actions as-is** — Rejected. It is an external dependency the
   owner wants to shed, it has been unreliable, and it duplicates checks that
   now run locally. Being free (public repo) does not make it independent.
2. **Hybrid: keep CI as an advisory backstop, add local gates too** — Rejected
   as the steady state. Two sources of truth drift; the local gate is the one
   the owner controls and runs. (Nothing stops re-adding a workflow later if the
   calculus changes — that is cheap.)
3. **Self-hosted runner** — Rejected. More infrastructure to own for a solo
   project whose whole direction is *less* external machinery.

## Consequences

- **Positive:** Verification depends only on tools already installed; no external
  CI to be flaky or gated. `make ci-local` is *stronger* than the old local
  tooling (coverage, guard, bandit ported in) and matches what `ci.yml` enforced.
  Retiring `sync-copilot.yml` ends the `[skip ci]` auto-commit merge-noise.
- **Negative:** No automatic check on push — the owner must run `make ci-local`
  before merging (a discipline, not a gate). Single Python version means a
  3.11-only regression could slip (accepted: no consumer needs 3.11).
- **Follow-up (B-011):** wire coverage/guard/bandit into pre-commit as
  non-optional; document the path in `CONTRIBUTING.md` + `CLAUDE.md`.
- **Revisit if:** the project gains contributors who need enforced pre-merge
  gates (add branch protection + a minimal workflow then), or is repackaged as a
  distributed library (multi-version testing would return).

## References

- [ADR-0014](0014-retire-paid-github-actions-generation.md) — retired paid GHA
  *generation*; this ADR extends the philosophy to *verification*.
- [ADR-0004](0004-python-version-constraint.md) — the CrewAI-era Python
  constraint this supersedes.
- `docs/specs/B-011-retire-ci-local-verification.md` — the executing spec.
- `Makefile` (`make ci-local`), `.pre-commit-config.yaml`.
