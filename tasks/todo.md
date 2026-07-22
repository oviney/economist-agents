# TODO: Retire paid GitHub Actions; keyless local run only (B-009)

**Plan**: [`tasks/plan.md`](./plan.md) · **Spec**: [`docs/specs/B-009-retire-paid-github-actions.md`](../docs/specs/B-009-retire-paid-github-actions.md)
**Status**: ⚠️ RE-SPEC'D after T1 (2026-07-21). T1 failed the fail-fast gate:
`flow.py` is not keyless (BUG-046), the keyless writer produces no article within
budget (BUG-047), + an async bug (BUG-048). Work split into **B-009 Track A**
(retire paid/broken/false machinery — the tasks below, minus the flow.py claims)
and **B-010 Track B** (fix keyless generation; owns the live-run acceptance gate).
The T1 task below is DONE (it ran and produced these findings). Task breakdown
will be regenerated when a track is built.

## Tasks (dependency-ordered)

- [ ] **T1 — Prove the keyless path end-to-end** _(gate; run on current `main`)_
  - Acceptance: `python -m src.economist_agents.flow` (env: `IS_SANDBOX=1`,
    `BLOG_REPO_TOKEN`) generates a publish-valid article + chart (`chart_only`,
    keyless deterministic research) **and** opens a PR on `oviney/blog`.
  - Verify: blog-PR URL exists; article passes `publication_validator`.
  - Files: none in this repo (produces a PR on `oviney/blog`).
  - **Runner: OWNER** — Ouray runs it locally on the subscription, reports result + blog-PR URL.
  - Depends: none. **Scope: S (externally gated).**
  - ⛔ If this fails → STOP, do not start T2. Re-open the spec (a non-working
    flow invalidates the core assumption).

- [ ] **T2 — Retire the scheduled paid-generation workflows**
  - Acceptance: `content-pipeline.yml`, `regenerate-image.yml`, and
    `remediation-sync.yml` all deleted (remediation-sync confirmed full retire —
    it triggers the deleted content pipeline).
  - Verify: `grep -rE "content-pipeline\.yml|regenerate-image\.yml" .github/workflows/`
    → empty; `git rm` recorded.
  - Files: 3 workflow files (delete).
  - Depends: T1 (Checkpoint A). Scope: S.

- [ ] **T3 — Strip `OPENAI_API_KEY` from `ci.yml`**
  - Acceptance: no paid-AI secret in `ci.yml`; test step runs keyless.
  - Verify: a green CI run on the B-009 branch (tests mock APIs — proven, not assumed).
  - Files: `.github/workflows/ci.yml`.
  - Depends: T1. Scope: XS.

- [ ] **T4 — Strip key + remove cron from `blog-quality-audit.yml`**
  - Acceptance: no `OPENAI_API_KEY`; no `schedule:` block; `workflow_dispatch`
    (with `dry_run`) retained.
  - Verify: `grep -n "schedule\|OPENAI_API_KEY" .github/workflows/blog-quality-audit.yml`
    → only unrelated matches / none.
  - Files: `.github/workflows/blog-quality-audit.yml`.
  - Depends: T1. Scope: XS.

- [ ] **T5 — Fix runbook + CLAUDE.md**
  - Acceptance: `docs/keyless-pipeline-runbook.md` names `python -m
    src.economist_agents.flow` as the canonical keyless generate+publish command
    (keeps the `pipeline` command as generate-only); CLAUDE.md's
    `OPENAI_API_KEY | DALL-E 3` env row removed/corrected; both point at the runbook.
  - Verify: runbook shows the flow command; `grep -n "DALL" CLAUDE.md` → none in
    a "supported path" sense.
  - Files: `docs/keyless-pipeline-runbook.md`, `CLAUDE.md`.
  - Depends: T1 (documents the proven command). Scope: S.

- [ ] **T6 — Full README run-doc correction**
  - Acceptance: README no longer says "via Serper" (~L29), no env-table rows for
    required `ANTHROPIC_API_KEY` / `SERPER_API_KEY` / `OPENAI_API_KEY`+DALL·E
    (~L82-84, ~L175-176); the Usage block names the canonical `flow` command,
    not the non-publishing `pipeline` + hero handshake (~L92-104); points at runbook.
  - Verify: `grep -niE "serper|dall" README.md` → none; Usage shows the flow command.
  - Files: `README.md`.
  - Depends: T1. Scope: S (~20-30 lines).

- [ ] **T7 — Open the B-009 PR and land**
  - Acceptance: one PR bundling the spec, plan, workflow deletions/strips, and
    doc fixes; description records the T1 blog-PR URL and both `grep` guards;
    CI green; merged; B-009 marked Done in `BACKLOG.md`.
  - Verify: all spec Success Criteria (1–6); PR checks green on the real commit.
  - Files: `BACKLOG.md` (mark Done) + the PR itself.
  - Depends: T2–T6. Scope: S.

## Checkpoints

- **A (after T1, BLOCKING):** keyless path proven; blog-PR URL captured, else stop.
- **B (after T2–T4):** no paid keys, no dangling workflow refs, CI green.
- **C (after T5–T6):** all run docs agree on the keyless `flow` command.
- **D (after T7):** spec Success Criteria met; B-009 Done.
