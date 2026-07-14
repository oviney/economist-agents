# TODO: Repo Process Consolidation — ✅ COMPLETE

**Plan**: [`tasks/plan.md`](./plan.md) · **Spec**: [`docs/specs/repo-process-consolidation.md`](../docs/specs/repo-process-consolidation.md)
**Branch/PR**: `claude/repo-process-agent-skills-p0h0op` → #444

The autonomous-Scrum regime (Regime B) is retired; the agent-skills lifecycle + `BACKLOG.md`
are the single process model. ~9,000 lines removed across two waves.

## Wave 1 — Safe retirement ✅
- [x] **W1-0** Spec correction + plan/todo (coupling audit)
- [x] **W1-A** Stale snapshots (SPRINT_15 set, SPRINT_10 cert, 3 badge JSONs) + README badges
- [x] **W1-B** `skills/sprint-management/` + `skills/scrum-master/` + mkdocs nav (validate_skills 37/37)
- [x] **W1-C** `sprint-discipline.yml` + `sprint-sync.yml` + sprint step from `quality-tests.yml`
- [x] **W1-D** `GEMINI.md` → pointer

## Wave 2 — Entangled retirement ✅
- [x] **W2-A** AgentRegistry: `agent_registry.py`, dead `src/manager.py`, 10 personas, `AGENTS.md`,
  registry-only tests, SM benchmark, `nightly-eval.yml`. Guardrail re-anchored on `llm_client.py`
  factory (50 tests pass). **ADR-0012 supersedes ADR-002.** (−5,655 lines)
- [x] **W2-B** Autonomous agents: `po/sm/orchestrator_agent`, `continuous_burndown`, `sprint_validator`
  + `mcp_servers/orchestrator_server.py` + `src/backlog/` package + their tests; `SPRINT.md`;
  dead sprint state JSONs. KEEP boundary verified (feedback_loop/quality_dashboard pass).
- [x] **W2-C** Collapsed root `copilot-instructions.md` → pointer; deleted orphan
  `sync_copilot_pre_commit.sh`. **Reclassified KEEP:** `sync-copilot.yml` + `sync_copilot_context.py`
  + `.github/copilot-instructions.md` are wired into the closed-loop quality validator.
- [x] **W2-D** Deleted root `SPEC.md`, `.github/BACKLOG.md`, `.github/{GITHUB_PROJECT_SETUP,MIGRATE_BACKLOG_QUICKSTART}.md`,
  sprint ISSUE_TEMPLATEs; replaced Regime-B PR template; corrected README (persona table,
  `.github/agents` discovery, registry examples, Sprint-15 status) + dangling SPRINT.md links.
- [x] **Doc-debt** Deleted wholesale Regime-B orchestration/template docs (`AGENT_ORCHESTRATION_PROMPTS.md`,
  `MISSION_TEMPLATE_USAGE.md`, `scripts/templates/`).

## Reclassified KEEP during the audit (NOT Regime B)
`skills_manager.py`/`skills_gap_analyzer.py`, `feedback_loop.py`, `quality_dashboard.py`,
`sync_copilot_context.py` + `.github/copilot-instructions.md`, `sprint_history.json`,
`escalations.json`, `remediation-sync.yml`, `.deployment_state`, `agent_loader.py` + `agents/*.yaml`.

## Remaining (minor, optional follow-ups)
- [ ] `scripts/tools/github_project_tool.py` + `docs/GITHUB_PROJECT_TOOL.md` — orphaned GitHub-Projects
  tool (no live importer); code-scope removal, left for a separate call.
- [ ] Historical docs with stale `agent_registry` mentions (`docs/guides/IMPLEMENTATION_ROADMAP.md`,
  ADR-0005, `docs/archive/**`, SPRINT/EPIC/STORY records) — left as immutable history by design.
- [ ] **CI gate:** #444 needs "Approve and run workflows" to validate the full suite (env here can't
  build the `sgmllib3k`/feedparser wheel).
