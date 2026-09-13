# Spec: B-011 · Retire GitHub Actions CI; local `make quality` + pre-commit is the verification path

> Backlog item: **B-011** (`type:chore`). Extends the ADR-0014 philosophy
> ("run locally on the subscription, not in paid/external CI") from *generation*
> to *verification*. **Scoping only — not yet approved to build.**

## Objective

Make **local tooling the source of truth for code verification**, with **no
dependency on GitHub Actions**. The user wants zero reliance on external/paywalled
infrastructure. (Note: this repo is *public*, so Actions is actually free — but
the goal is independence from it, not cost.) `main` is not branch-protected, so
no CI check is required to merge today; this formalises that reality.

**Success = a single local command reproduces every quality gate CI enforced,
the Actions quality workflows are removed, and the docs tell a contributor to run
that command before merging.**

## Assumptions (correct me before I plan)

1. **Retire the *quality* workflows** — `ci.yml` (Quality Gates) and
   `quality-tests.yml` (Quality System Tests). These are the CI gates that
   local tooling should replace.
2. **Retire `sync-copilot.yml`** — the bot that auto-commits
   `.github/copilot-instructions.md`. It has generated constant `[skip ci]`
   merge-noise all session (rebases, conflicts). Its output is a convenience
   file, not a gate. (Open Q1 confirms.)
3. **Parity, not regression.** Before deleting `ci.yml`, port its CI-only gates
   into `make quality` / pre-commit so verification rigor is preserved:
   coverage threshold (70% on `src`+`scripts`), the `src/quality` per-module
   90% gate, the Destructive Change Guard, and the bandit security scan. Today
   `make test` is only 40% on `scripts`.
4. **`blog-quality-audit.yml` stays** (already manual-only after B-009) —
   it's a free-token utility, not a CI gate.
5. **Not implementing here.** This produces the spec + backlog item; build is a
   later approved slice.

## Scope

**In:**
- Delete `.github/workflows/ci.yml`, `.github/workflows/quality-tests.yml`, and
  `.github/workflows/sync-copilot.yml`.
- **Port the CI-only gates to local tooling** so `make ci-local` matches CI:
  - raise coverage to `--cov=src --cov=scripts --cov-fail-under=70`;
  - add the `src/quality` per-module 90% gate (`coverage report --include='src/quality/*' --fail-under=90`);
  - add `scripts/destructive_change_guard.py` (adapt its git-diff base for local use — it currently reads a PR context);
  - add a `bandit` run (it's already a dependency).
- Wire the same into `.pre-commit-config.yaml` and make `pytest-coverage`
  non-optional.
- **Pin one Python version** via `.python-version` (single-version — see Q4) and
  drop the 3.11+3.12 matrix thinking.
- Document the local verification path in `CONTRIBUTING.md` + `CLAUDE.md`:
  "run `make ci-local` before merging; `main` is not protected — you are the gate."
- **ADR-0015** (local-first verification, companion to ADR-0014); mark
  **ADR-0004 Superseded** (its CrewAI rationale is gone).

**Out:**
- `docs.yml` (free GitHub Pages publish, not a gate) and
  `copilot-setup-steps.yml` (Copilot-agent infra, orthogonal) — **both kept**
  (Q2). Whether to retire GitHub Copilot entirely is a separate future decision.
- Adding branch protection (the opposite direction).

## Commands

```bash
make quality        # format + lint + type-check + test (today: single-version, 40% cov)
# Target end state — one command matching CI:
make ci-local       # ruff format+check, mypy, pytest (cov=src,scripts >=70 + src/quality >=90),
                    # destructive-change guard, bandit
pre-commit run --all-files   # the same gates, per-commit
```

## Project Structure (files touched)

```
.github/workflows/ci.yml             → DELETE
.github/workflows/quality-tests.yml  → DELETE
.github/workflows/sync-copilot.yml   → DELETE (Open Q1)
Makefile                             → add ci-local target (coverage 70 + src/quality 90 + guard + bandit)
.pre-commit-config.yaml              → make coverage non-optional; add bandit + destructive guard
scripts/destructive_change_guard.py  → local-invocation mode (diff base without PR context)
CONTRIBUTING.md, CLAUDE.md           → document the local verification path
docs/adr/0015-*.md (Open Q3)         → record the decision
```

## Testing Strategy

- The deliverable *is* the test harness. Verify by: `make ci-local` passes on a
  clean `main`; introducing a deliberate lint error / coverage drop / bandit
  finding each makes it fail; a known-good commit passes.
- Multi-version: see Open Q if we keep 3.11+3.12 locally (needs both pythons) or
  accept single-version.

## Boundaries

- **Always:** keep verification rigor at or above what `ci.yml` enforced —
  deleting a workflow must not silently lower a gate.
- **Ask first:** dropping multi-version testing; deleting `docs.yml` /
  `copilot-setup-steps.yml`; removing branch protection (there is none today).
- **Never:** delete a CI gate without its local equivalent in place first;
  reintroduce a paid/keyed dependency.

## Success Criteria

1. `make ci-local` (or `make quality`) reproduces every gate `ci.yml` enforced:
   ruff, mypy, tests at ≥70% (`src`+`scripts`) + `src/quality` ≥90%, destructive
   guard, bandit.
2. `ci.yml`, `quality-tests.yml` (and `sync-copilot.yml` per Q1) are deleted;
   `.github/workflows/` contains no quality-gate workflow.
3. `pre-commit run --all-files` runs the same gates and coverage is non-optional.
4. `CONTRIBUTING.md` + `CLAUDE.md` document "run `make ci-local` before merging;
   you are the gate."
5. No paid or external-infra dependency remains in the verification path.

## Open Questions — RESOLVED (2026-07-22)

1. **`sync-copilot.yml`** → **retire it.** It generated constant `[skip ci]`
   merge-noise all session; its output (`copilot-instructions.md`) is a
   convenience file, not a gate. Becomes manual if ever needed.
2. **`docs.yml` + `copilot-setup-steps.yml`** → **keep both.** Neither is a
   quality gate, neither is paywalled (GitHub Pages is free for public repos),
   and retiring them advances nothing. `docs.yml` gives a hosted ADR/docs site
   (`mkdocs serve` locally is a downgrade for no cost benefit).
   `copilot-setup-steps.yml` is Copilot-agent infra — orthogonal to
   verification; whether to keep GitHub Copilot at all is a **separate** decision,
   out of B-011 scope.
3. **ADR** → **yes, ADR-0015** (local-first verification), companion to
   ADR-0014. It should also note **ADR-0004 (Python ≤3.13 for CrewAI) is now
   moot** — CrewAI was removed (ADR-0006) — and mark it Superseded.
4. **Multi-version testing** → **single version, pinned.** The 3.11+3.12 CI
   matrix is legacy from ADR-0004 (CrewAI, now gone) and doesn't even match the
   runtime (which ran 3.13). This is a solo, locally-run project, not a library
   shipped across interpreters — no consumer needs 3.11 compat. Pin one version
   via `.python-version` (3.13 per the retired runtime, or the local 3.12) and
   test only that. Fold into scope: add `.python-version`.
