# SPEC: Delete or archive dead files in scripts/ (issue #327)

**Status**: APPROVED (staff engineer review applied 2026-05-10; amended 2026-05-12)
**GitHub issue**: oviney/economist-agents#327
**Date**: 2026-05-10 (amended 2026-05-12 — see [ADR-0010](docs/adr/0010-scripts-to-src-migration.md))

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
| `agent_metrics.py` | tests/test_quality_dashboard.py (4× `patch("agent_metrics.…")`) † |
| `agent_registry.py` | imported by src/manager.py |
| `agent_reviewer.py` | agents/writer_agent.py:31, agents/research_agent.py:25, tests/test_quality_system.py:19 † |
| `agent_trace_logger.py` | tests/test_agent_trace_logger.py |
| `architecture_audit.py` | 15 tests in test_architecture_audit.py ✱ |
| `arxiv_search.py` | imported by mcp_servers/web_researcher_server.py |
| `article_archive.py` | imported by mcp_servers/ |
| `article_evaluator.py` | imported by src/economist_agents/flow.py |
| `audit_composite_scores.py` | tests/test_audit_composite_scores.py |
| `blog_quality_audit.py` | called by blog-quality-audit.yml |
| `chart_metrics.py` | agents/graphics_agent.py:31 † |
| `citation_verifier.py` | tests/test_citation_verifier.py |
| `content_intelligence.py` | tests/test_content_intelligence.py |
| `context_manager.py` | 28 tests in test_context_manager.py ✱ |
| `continuous_burndown.py` | 2 tests in test_continuous_burndown.py ✱ |
| `defect_prevention_rules.py` | soft dep of publication_validator.py (try/except import) |
| `defect_tracker.py` | tests/test_quality_dashboard.py (3× `patch("scripts.defect_tracker.…")`) † |
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
| `governance.py` | agents/writer_agent.py:32, agents/research_agent.py:26 † |
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
| `schema_validator.py` | tests/test_quality_system.py:20; doc ref in mcp_servers/publication_validator_server.py † |
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
| `validate_closed_loop.py` | tests/test_closed_loop_validation.py (3× subprocess) † |
| `validate_skills.py` | called by quality-tests.yml |
| `tools/github_project_tool.py` | used by agent skills |
| `tools/__init__.py` | package |
| `benchmarks/measure_sm_effectiveness.py` | called by nightly-eval.yml |
| `benchmarks/__init__.py` | package |
| `__init__.py` | package |

✱ = moved from ARCHIVE to KEEP by staff engineer review (archiving would break pytest)
† = moved from ARCHIVE to KEEP after second staff-engineer pass on 2026-05-12;
    `agents/` and several live tests import these modules via the
    `scripts/` sys.path hack. See [ADR-0010](docs/adr/0010-scripts-to-src-migration.md)
    for the follow-up migration that will allow these to be properly archived.

---

### ARCHIVE — move to `scripts/archived/`

Utilities with no live `src/` callers, no CI workflow caller, and no live
test file. Preserves git history; does not break any import.

| File |
|---|
| `agent_dashboard.py` |
| `architecture_review.py` |
| `backlog_groomer.py` |
| `blog_qa_agent.py` |
| `calculate_quality_score.py` |
| `ci_health_monitor.py` |
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
| `migrate_backlog_to_github.py` |
| `production_health_check.py` |
| `secure_env.py` |
| `skill_synthesizer.py` |
| `sprint_ceremony_tracker.py` | ✱ moved from KEEP (cited test file does not exist)
| `update_badges.py` |
| `update_readme_badges.py` |
| `update_sprint_docs.py` |
| `validate_agile_discipline.py` |
| `validate_badges.py` |
| `validate_documentation_accuracy.py` |
| `validate_editor_fixes.py` |
| `validate_environment.py` |
| `validate_sprint_report.py` |
| `visual_qa.py` |
| `visual_qa_zones.py` |
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

**Total: 22 delete, 38 archive, 60 keep.** (Updated 2026-05-12: 7 modules
moved ARCHIVE→KEEP after second staff-engineer pass found live callers in
`agents/` and test files — see ADR-0010 for follow-up migration plan.)

---

## 3. Acceptance Criteria

**AC1** — All 22 DELETE files are removed.

**AC2** — All 38 ARCHIVE files are in `scripts/archived/`. No `src/`,
`agents/`, `mcp_servers/`, or live-test import is broken.

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
