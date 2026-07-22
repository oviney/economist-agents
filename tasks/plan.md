# PLAN: Retire paid GitHub Actions; keyless local run only (B-009)

**Spec**: `docs/specs/B-009-retire-paid-github-actions.md` (approved — go to plan)
**ADR**: `docs/adr/0014-retire-paid-github-actions-generation.md` (Accepted, #449)
**Branch**: _to create_ — `chore/b-009-retire-paid-gha`
**Status**: T1 handed to owner (fail-fast gate). T2–T7 blocked until T1 passes.

## Goal restated

Make a keyless local/subscription run the only way articles are generated and
published, and remove every GitHub Actions workflow that requires a paid-AI key.
Doc + workflow changes only — **no `src/`/`scripts/` code changes expected**.

## Architecture decisions

- **Fail-fast ordering.** The riskiest assumption is that the keyless command
  actually produces an article end-to-end after 3 months of a dark pipeline.
  That real run is *also* the spec's acceptance gate. So it goes **first**, on
  current `main`, before we delete any paid automation. If it fails → STOP and
  re-spec (per spec: a non-working flow is a new finding, not scope creep).
- **Prove the exact documented command.** Task 1 runs
  `python -m src.economist_agents.flow` — the same command Tasks 5–6 will
  document as canonical — so the docs describe a verified path, not an assumed
  one.
- **`remediation-sync.yml` → retire, not patch.** It is a scheduled workflow
  whose queue processor triggers the deleted `content-pipeline.yml`; stripping
  only the trigger leaves a queue processor that can't act. Retiring it aligns
  with ADR-0014's "no unattended scheduled generation."
- **One PR, spec + plan included.** The approved spec and this plan land in the
  same B-009 PR as the changes they govern.

## Task list

### Phase 1 — Prove the keyless path (fail-fast gate)

- [ ] **T1** — Real keyless end-to-end run

### Checkpoint A (BLOCKING)
- [ ] T1 produced a publish-valid article + chart and opened a PR on
      `oviney/blog`. Blog-PR URL captured. **If T1 failed, stop and re-spec —
      do not proceed to deletions.**

### Phase 2 — Retire paid workflows + fix couplings

- [ ] **T2** — Delete `content-pipeline.yml`, `regenerate-image.yml`, retire `remediation-sync.yml`
- [ ] **T3** — Strip `OPENAI_API_KEY` from `ci.yml`
- [ ] **T4** — Strip key + remove cron from `blog-quality-audit.yml`

### Checkpoint B
- [ ] `grep -rE "ANTHROPIC_API_KEY|OPENAI_API_KEY|SERPER_API_KEY" .github/workflows/` → empty
- [ ] `grep -rE "content-pipeline\.yml|regenerate-image\.yml" .github/workflows/` → empty
- [ ] A green CI run confirms the `ci.yml` key removal is inert (tests mock APIs)

### Phase 3 — Make the run docs agree

- [ ] **T5** — Fix runbook + CLAUDE.md
- [ ] **T6** — Full README run-doc correction

### Checkpoint C
- [ ] Runbook names `python -m src.economist_agents.flow` as canonical
- [ ] No run doc (README/CLAUDE.md/runbook) advertises Serper, a required
      `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`/DALL-E

### Phase 4 — Land

- [ ] **T7** — Open the B-009 PR; record the T1 blog-PR URL; CI green; merge

### Checkpoint D (Complete)
- [ ] All spec Success Criteria (1–6) met; mark B-009 Done in BACKLOG.md

## Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Keyless flow doesn't actually run e2e (3 months dark) | High | T1 first, on `main`, before any deletion. Failure → stop + re-spec. |
| T1 needs subscription auth + `BLOG_REPO_TOKEN` and opens a real blog PR | Med | Human-in-the-loop: owner runs T1 (or explicitly authorises it); it is an outward action on `oviney/blog`. |
| Stripping `ci.yml` key breaks a test that reads it | Med | Verified by a green CI run (Checkpoint B), not assumed. Revert is one line. |
| `remediation-sync.yml` retirement removes wanted queue logic | Low | It cannot function without the deleted content pipeline; retire is the honest state. Flag in PR for owner review. |
| README correction drifts from CLAUDE.md/runbook wording | Low | T5 and T6 share one canonical command string; cross-check in Checkpoint C. |

## Parallelization

- T2 / T3 / T4 touch independent files — safe to do together within Phase 2.
- T5 / T6 are independent docs — parallelizable, but must post-date T1 (they
  document the command T1 proves).
- T1 gates everything; T7 depends on all.

## Open questions — RESOLVED

- **T1 execution** → **owner runs it.** Ouray runs `python -m
  src.economist_agents.flow` locally on the subscription and reports the result
  + blog-PR URL. It is not run in the agent environment (subscription auth +
  outward blog PR).
- **`remediation-sync.yml`** → **retire entirely** (confirmed). It cannot
  function without the deleted content pipeline.
