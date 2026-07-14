# SPEC: Reconcile the supported Python version policy (B-004)

**Status**: DRAFT — awaiting human decision (see §3) then LGTM before implementation
**Backlog item**: `B-004` (see [`BACKLOG.md`](../../BACKLOG.md))
**Date**: 2026-07-14
**Related**: [ADR-0004](../adr/0004-python-version-constraint.md) (now obsolete rationale),
[ADR-0006](../adr/0006-agent-framework-selection.md) (removed CrewAI)

---

## 1. Objective

The repository has **no single source of truth** for which Python versions it supports,
and the four places that imply one disagree. Establish one authoritative policy and make
CI, docs, packaging, and the ADR record agree with it.

## 2. Context — the inconsistency

Discovered while reconciling the docs (PR #445). Current state:

| Source | Claims | Location |
|--------|--------|----------|
| CI test matrix | Python **3.11 and 3.12** only | `.github/workflows/ci.yml:64` (`python-version: ['3.11', '3.12']`); lint/quality/coverage jobs pin `3.11` |
| Docs | Python **3.13.x**, "3.14+ untested" | `README.md`, `CONTRIBUTING.md` |
| Packaging | **Nothing** — no floor or ceiling declared | no `requires-python` in `pyproject.toml`/`setup.*` |
| ADR-0004 | Constrain to **≤3.13** *for CrewAI compatibility* | `docs/adr/0004-python-version-constraint.md` |

Two independent problems:

1. **Disagreement**: CI proves the suite runs on 3.11/3.12, yet the docs tell a
   contributor they need 3.13.x. A newcomer on 3.11 is told (wrongly) they can't run it,
   or a newcomer on 3.13 runs a version CI never exercises.
2. **Obsolete rationale**: ADR-0004's *entire justification* is CrewAI compatibility, and
   CrewAI was removed in Phase 2 ([ADR-0006](../adr/0006-agent-framework-selection.md)).
   The ≤3.13 ceiling may no longer be needed at all — it needs re-deciding on current facts,
   not inheriting.

> Note: PR #445 aligned the docs to ADR-0004/CONTRIBUTING's stated "3.13.x" so the docs at
> least stopped contradicting *each other*. This spec resolves the deeper disagreement
> between docs, CI, packaging, and the ADR. It does **not** revisit any other content.

## 3. Decision required (human LGTM before implementation)

Pick the supported-version policy. This is a product/maintenance call, not a mechanical one:

- **Option A — Support 3.11–3.13 (widest).** Add 3.13 to the CI matrix; docs say "3.11+";
  `requires-python = ">=3.11"`. Pro: matches what CI already proves plus room to grow;
  most contributor-friendly. Con: three versions to keep green.
- **Option B — Standardise on 3.13 only.** Bump CI matrix (and pinned jobs) to 3.13; docs
  already say 3.13.x; `requires-python = ">=3.13,<3.14"`. Pro: one version, matches current
  docs. Con: drops the 3.11/3.12 coverage CI has today; requires bumping every pinned job.
- **Option C — Support 3.11–3.12 (match CI as-is).** Revert docs to "3.11/3.12"; leave CI;
  `requires-python = ">=3.11,<3.13"`. Pro: zero CI change, lowest risk. Con: docs move
  *backwards* from 3.13; contradicts ADR-0004's "tested with 3.13.11".

**Recommendation: Option A** — it's the only option consistent with everything CI already
demonstrates while leaving 3.13 (which ADR-0004 says was tested) supported. But the choice
is the maintainer's; do not implement until it is made.

## 4. Acceptance criteria

Once the policy (§3) is chosen, "done" means **all four sources agree**:

- **AC1** — `requires-python` is declared in `pyproject.toml` matching the chosen policy.
- **AC2** — `.github/workflows/ci.yml` test matrix (and any pinned single-version jobs)
  matches the policy; CI is green on every version in the policy.
- **AC3** — `README.md` and `CONTRIBUTING.md` state the policy verbatim and identically.
- **AC4** — A new ADR (or an amendment to ADR-0004) records the decision **on current
  grounds** (CrewAI removed), and marks ADR-0004's CrewAI rationale superseded. Follows
  [`skills/adr-governance`](../../skills/adr-governance/SKILL.md) numbering.
- **AC5** — `grep -rniE 'python *3\.1[0-9]|requires-python' README.md CONTRIBUTING.md pyproject.toml .github/workflows/ci.yml` shows no version that disagrees with the policy.

## 5. Boundaries

### Always do
- Make the decision in §3 explicit and LGTM'd **before** editing anything.
- Change all four sources in one slice so they never disagree again.

### Never do
- Silently pick a version by editing only one file.
- Widen support to an untested version (e.g. add 3.14 to docs without adding it to CI).
- Re-open or re-touch anything from PR #445 beyond the version-policy strings.

## 6. Suggested approach (for the implementing session)

1. Run [`skills/using-agent-skills`](../../skills/using-agent-skills/SKILL.md) → this is a
   spec with a pending decision, so resolve §3 with the maintainer first.
2. On LGTM, follow [`skills/incremental-implementation`](../../skills/incremental-implementation/SKILL.md):
   one slice touching `pyproject.toml`, `ci.yml`, `README.md`, `CONTRIBUTING.md`, and the ADR.
3. Verify AC2 by pushing and watching CI on every version in the policy.
