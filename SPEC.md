# SPEC: Delete or archive dead files in scripts/ (issue #327)

**Status**: APPROVED (staff engineer review applied 2026-05-10; amended 2026-05-12; ADR-0010 implemented 2026-05-15 via #344)
**GitHub issue**: oviney/economist-agents#327 (ADR-0010 follow-up: #344)
**Date**: 2026-05-10 (amended 2026-05-12 — see [ADR-0010](docs/adr/0010-scripts-to-src-migration.md); 2026-05-15 — †-rows migrated to src/ via #344)

---

## 1. Objective

`scripts/` contains 115 Python files of mixed vintage. This spec classifies
every file precisely and defines what to delete, archive, and keep. The
classification was reviewed by a staff engineer; corrections are incorporated
below.

---

## 2. Classification

### KEEP — confirmed live (no change)

| File | Why live |
|---|---|
| `ab_topic_scout_comparison.py` | 29 tests in test_ab_topic_scout_comparison.py ✱ |
| `agent_loader.py` | tests/test_agent_loader.py |
| `agent_registry.py` | imported by src/manager.py |
| `agent_trace_logger.py` | tests/test_agent_trace_logger.py |
| `architecture_audit.py` | 15 tests in test_architecture_audit.py ✱ |
| `arxiv_search.py` | imported by mcp_servers/web_researcher_server.py |
| `article_archive.py` | imported by mcp_servers/ |
| `article_evaluator.py` | imported by src/economist_agents/flow.py |
| `audit_composite_scores.py` | tests/test_audit_composite_scores.py |
| `blog_quality_audit.py` | called by blog-quality-audit.yml |
| `citation_verifier.py` | tests/test_citation_verifier.py |
| `content_intelligence.py` | tests/test_content_intelligence.py |
| `context_manager.py` | 28 tests in test_context_manager.py ✱ |
| `continuous_burndown.py` | 2 tests in test_continuous_burndown.py ✱ |
| `defect_prevention_rules.py` | soft dep of publication_validator.py (try/except import) |
| `deploy_to_blog.py` | tests/test_deploy_to_blog.py |
| `destructive_change_guard.py` | called by ci.yml |
| `economist_agent.py` | 34 tests in test_economist_agent.py ✱ (deprecated; warning in main()) |
| `editorial_board.py` | tests/test_editorial_board.py |
| `editorial_judge.py` | called by content-pipeline.yml |
| `featured_image_agent.py` | called by regenerate-image.yml |
| `feedback_loop.py` | tests/test_feedback_loop.py |
| `frontmatter_schema.py` | imported by src/economist_agents/flow.py |
| `ga4_etl.py` | tests/test_ga4_etl.py |
| `generate_chart.py` | 29 tests in test_generate_chart.py ✱ |
| `github_issue_claim.py` | tests/test_github_issue_claim.py |
| `google_search.py` | imported by mcp_servers/web_researcher_server.py |
| `gsc_etl.py` | tests/test_gsc_etl.py |
| `index_published_articles.py` | tests/test_index_published_articles.py |
| `llm_client.py` | tests/test_llm_client.py; imported by agent_registry |
| `orchestrator_agent.py` | imported by mcp_servers/orchestrator_agent_server.py |
| `po_agent.py` | tests/test_po_agent.py |
| `pre_commit_arch_check.py` | tested by test_pre_commit_arch_check.py |
| `publication_validator.py` | imported by src/agent_sdk/stage4_runner.py |
| `quality_dashboard.py` | tests/test_quality_dashboard.py |
| `quality_metrics.py` | called by content-pipeline.yml |
| `record_metrics.py` | called by content-pipeline.yml |
| `skills_gap_analyzer.py` | tests/test_skills_gap_analyzer.py |
| `skills_manager.py` | 7 tests in test_closed_loop_validation.py ✱ |
| `sm_agent.py` | tests/test_sm_agent.py |
| `spend_report.py` | tests/test_spend_report.py |
| `sprint_validator.py` | called by quality-tests.yml |
| `sync_copilot_context.py` | called by sync-copilot.yml |
| `token_usage.py` | tests/test_token_usage.py |
| `topic_scout.py` | tests/test_topic_scout.py |
| `topic_scout_reproducibility.py` | tests/test_topic_scout_reproducibility.py |
| `topic_trend_grounding.py` | tests/test_topic_trend_grounding.py |
| `validate_skills.py` | called by quality-tests.yml |
| `tools/github_project_tool.py` | used by agent skills |
| `tools/__init__.py` | package |
| `benchmarks/measure_sm_effectiveness.py` | called by nightly-eval.yml |
| `benchmarks/__init__.py` | package |
| `__init__.py` | package |

✱ = moved from ARCHIVE to KEEP by staff engineer review (archiving would break pytest)

---

### MIGRATED — moved to `src/` per [ADR-0010](docs/adr/0010-scripts-to-src-migration.md)

The 12 entries previously marked `†` in the KEEP table were domain
modules with live callers in `agents/`, live tests, and KEEP scripts.
They could not be archived without breaking those callers, and the
callers relied on the bare-name import path enabled by the `scripts/`
`sys.path` hack. Issue #344 implemented ADR-0010 on 2026-05-15:

| Old path | New path | Subpackage |
|---|---|---|
| `scripts/agent_reviewer.py` | `src/quality/agent_reviewer.py` | quality |
| `scripts/agent_metrics.py` | `src/quality/agent_metrics.py` | quality |
| `scripts/chart_metrics.py` | `src/quality/chart_metrics.py` | quality |
| `scripts/defect_tracker.py` | `src/quality/defect_tracker.py` | quality |
| `scripts/governance.py` | `src/quality/governance.py` | quality |
| `scripts/schema_validator.py` | `src/quality/schema_validator.py` | quality |
| `scripts/validate_closed_loop.py` | `src/quality/validate_closed_loop.py` | quality |
| `scripts/visual_qa_zones.py` | `src/quality/visual_qa_zones.py` | quality |
| `scripts/backlog_groomer.py` | `src/backlog/backlog_groomer.py` | backlog |
| `scripts/ci_health_monitor.py` | `src/backlog/ci_health_monitor.py` | backlog |
| `scripts/migrate_backlog_to_github.py` | `src/backlog/migrate_backlog_to_github.py` | backlog |
| `scripts/validate_documentation_accuracy.py` | `src/backlog/validate_documentation_accuracy.py` | backlog |

The `sys.path.insert(0, str(SCRIPTS_DIR))` hack at
`tests/test_architecture_compliance.py:22` was removed as part of
#344 after all callers were updated to use the new fully-qualified
import paths.

---

### ARCHIVE — move to `scripts/archived/`

Utilities with no live `src/` callers, no CI workflow caller, and no live
test file. Preserves git history; does not break any import.

| File |
|---|
| `agent_dashboard.py` |
| `architecture_review.py` |
| `blog_qa_agent.py` |
| `calculate_quality_score.py` |
| `crewai_agents.py` |
| `editor_agent_diagnostic.py` |
| `evaluate_architecture_options.py` |
| `evaluate_fresh_data_options.py` |
| `generate_coverage_badge.py` |
| `generate_sample_metrics.py` |
| `generate_sprint_badge.py` |
| `generate_tests_badge.py` |
| `github_project_v2_validator.py` |
| `integration_health_check.py` |
| `lint_adrs.py` |
| `measure_sm_agent.py` |
| `metrics_dashboard.py` |
| `metrics_report.py` |
| `production_health_check.py` |
| `secure_env.py` |
| `skill_synthesizer.py` |
| `sprint_ceremony_tracker.py` | ✱ moved from KEEP (cited test file does not exist)
| `update_badges.py` |
| `update_readme_badges.py` |
| `update_sprint_docs.py` |
| `validate_agile_discipline.py` |
| `validate_badges.py` |
| `validate_editor_fixes.py` |
| `validate_environment.py` |
| `validate_sprint_report.py` |
| `visual_qa.py` |
| `web_research.py` | ✱ moved from KEEP (cited test file does not exist; superseded by MCP)
| `templates/mission_template.py` |

✱ = moved from KEEP to ARCHIVE by staff engineer review

---

### DELETE — confirmed dead

| File | Reason |
|---|---|
| `fix_story11_import.py` | one-time fix script |
| `fix_typo.py` | one-time fix script |
| `run_dev_crew.py` | sprint execution artefact |
| `run_dev_sprint_crew.py` | sprint execution artefact |
| `run_meta_sprint.py` | sprint execution artefact |
| `run_story2_crew.py` | sprint execution artefact |
| `run_story7_crew.py` | sprint execution artefact |
| `run_story10_crew.py` | sprint execution artefact |
| `run_story10_fix.py` | sprint execution artefact |
| `run_story11_crew.py` | sprint execution artefact |
| `spike_crewai_baseline.py` | CrewAI experiment |
| `test_agent_integration.py` | scripts/test_*.py, not collected by pytest |
| `test_dev_crew_workflow.py` | scripts/test_*.py, not collected by pytest |
| `test_full_workflow_streamlined.py` | scripts/test_*.py, not collected by pytest |
| `test_gap_analyzer.py` | scripts/test_*.py, not collected by pytest |
| `test_git_operations_direct.py` | scripts/test_*.py, not collected by pytest |
| `test_hybrid_approach_validation.py` | scripts/test_*.py, not collected by pytest |
| `test_metrics.py` | scripts/test_*.py, not collected by pytest |
| `test_real_debug_story.py` | scripts/test_*.py, not collected by pytest |
| `test_setup.py` | scripts/test_*.py, not collected by pytest |
| `test_simple_git_workflow.py` | scripts/test_*.py, not collected by pytest |
| `test_sprint_15_orchestration.py` | scripts/test_*.py, not collected by pytest |

**Total: 22 delete, 33 archive, 65 keep.** (Updated 2026-05-12: 12 modules
moved ARCHIVE→KEEP after staff-engineer review surfaced live callers in
`agents/`, live tests, and KEEP scripts (`continuous_burndown.py`,
`economist_agent.py`) — see ADR-0010 for follow-up migration plan.)

---

## 3. Acceptance Criteria

**AC1** — All 22 DELETE files are removed.

**AC2** — All 33 ARCHIVE files are in `scripts/archived/`. No `src/`,
`agents/`, `mcp_servers/`, scripts/ (KEEP), or live-test import is broken.

**AC3** — `pytest tests/ -q` passes with the same count (±0).

**AC4** — `grep -rn "from scripts\." src/` returns only KEEP files.

**AC5** — The crewai-import guard (`TestNoCrewAIInSrcOrTests`) passes.

**AC6** — The 4 deleted `run_story*.py` entries are removed from
`ALLOWED_FILES` in `tests/test_architecture_compliance.py`.

---

## 4. Boundaries

### Always do
- Run `pytest tests/ -q` after DELETE batch and again after ARCHIVE batch.
- Verify AC4 grep before committing.

### Never do
- Delete any KEEP file.
- Edit any `src/` import as part of this change.
- Archive and delete the same file.
- Touch `scripts/archived/legacy_sync/` (already archived).
