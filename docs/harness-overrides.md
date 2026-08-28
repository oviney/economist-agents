# Harness overrides — accepted complexity

**Owner:** Ouray Viney · **Sensor:** `scripts/complexity_sensor.py` (B-032)
**Spec:** `docs/specs/harness-engineering.md` · **Audit:** `docs/reviews/harness-engineering-assessment-2026-07-29.md`

---

## What this file is

The complexity sensor does not silently pass or silently suppress. When it fires, the agent
has exactly two legitimate responses:

1. **Refactor** — split the function, hoist a guard clause, name a helper.
2. **Record an override here**, with a one-line justification.

A bare `# noqa: C901` is **not** a legitimate response. The whole point of the register is
that accepted complexity is *visible at review time*. Boeckeler's framing (SE Radio 730):
the reason nobody tunes a static-analysis baseline by hand is that it is too tedious, and
the reason the resulting noise gets ignored is that the exceptions are invisible. An agent
will happily do the tedious part — so the exceptions become a short, reviewable list
instead of a scatter of suppressions nobody reads.

**Read this file as the owner's review queue.** Every line is a decision to re-examine.

## Format

One bullet per override. The backticked key must be exactly `path::function` — that is what
the sensor matches on, so a typo silently grants no exemption (fail-closed by design).

```markdown
- `scripts/foo.py::bar` — dispatch table; splitting it would obscure the mapping
```

## Active overrides

- `scripts/sync_copilot_context.py::format_anti_patterns_section` — three parallel
  group-by-and-emit blocks (defects, QA skills, architecture); pre-existing and untouched by
  B-035 Task 3(b), which changed only `update_copilot_instructions`. Splitting it is a
  worthwhile cleanup but is not this bug fix's scope. **Review queue: pay down when this
  formatter is next edited for its own sake.**
- `scripts/sync_copilot_context.py::extract_architecture_patterns` — a line-oriented
  markdown parser; the branch count is the grammar. Same provenance as above: pre-existing,
  not touched by Task 3(b).
- `scripts/llm_client.py::_call_anthropic` — 6 args (client, model, system, user,
  max_tokens, temperature). Pre-existing; it is the provider ABI that `call_llm` dispatches
  to, so the signature is the interface rather than an accumulation. Untouched by BUG-046,
  which only added a keyless branch alongside it.
- `scripts/llm_client.py::_call_openai` — same signature, same reason, same provenance.

### Recorded by B-042 (2026-08-01)

All six are **pre-existing** and none was introduced by B-042; they became live because the
sensor is scoped to files an agent touches and B-042 touched these files. Four were not
modified at all, and the two that were each took a single added line. Two got *smaller*.
Recorded rather than refactored because refactoring a function this change did not otherwise
alter would bury the diff a reviewer needs to read.

- `scripts/deploy_to_blog.py::deploy` — linear script (clone → copy → validate → commit → push).
  Extracted `_copy_chart_assets` to deduplicate asset handling with `deploy_review`.
- `scripts/deploy_to_blog.py::deploy_review` — review branch deploy script, shares `_copy_chart_assets`.
- `scripts/deploy_to_blog.py::<module>` — deploy script linear statement and parameter bounds.
- `scripts/economist_agent.py::generate_economist_post` — legacy orchestrator flow.
- `scripts/economist_agent.py::run_visual_qa_agent` — legacy visual QA analyzer.
- `scripts/economist_agent.py::<module>` — legacy economist agent statements.
- `scripts/editorial_board.py::run_editorial_board` — multi-persona evaluation consensus loop.
- `scripts/editorial_board.py::<module>` — editorial board statement bounds.
- `scripts/featured_image_agent.py::generate_featured_image` — image generation parameter interface.
- `scripts/featured_image_agent.py::<module>` — image generation parameter bounds.
- `scripts/github_issue_claim.py::parse_claim_comment` — structured claim parser with early returns.
- `scripts/github_issue_claim.py::<module>` — claim parser return bounds.
- `scripts/publication_validator.py::_check_image_contract` — untouched by B-042. A
  field-by-field frontmatter contract check; the branch count is the number of fields.
- `src/agent_sdk/_shared.py::apply_editorial_fixes` — untouched except that B-042 **removed**
  a call from it (the unconditional chart embed), so it is one statement shorter than before.
  It is a pipeline of independent text fixes; the length is the number of fixes.
- `src/agent_sdk/_shared.py::audit_article_stats` — untouched by B-042.
- `src/agent_sdk/stage3_runner.py::_collect_text` — untouched by B-042. The 9 arguments are
  the Agent SDK call surface (model, budget, turns, timeout, label, tools…).
- `src/agent_sdk/stage3_runner.py::run_stage3` — B-042 **cut this from 83 statements to 64**
  by deleting the graphics stage and the hero draw, and dropped it below the C901 and
  PLR0912 thresholds it used to exceed. Still over the statement limit. Left recorded rather
  than pushed further in the same change.

## Day-one baseline (NOT overrides)

The audit measured the following on `src/` + `scripts/` at the time the sensor landed.
These are **not** exempted: the sensor is scoped to files an agent touches, so this backlog
is *recorded* rather than retroactively enforced. Each entry becomes live the first time
something edits that file — which is the right moment to pay it down.

```
41  C901     complex-structure         worst: generate_economist_post (33 > 10),
                                       validate (28), review_writer_output (24),
                                       apply_editorial_fixes (21), run_editorial_board (20)
28  PLR0912  too-many-branches
21  PLR0913  too-many-arguments
18  PLR0915  too-many-statements
 8  PLR0911  too-many-return-statements
```

Reproduce with:

```bash
.venv/bin/ruff check --select C901,PLR0911,PLR0912,PLR0913,PLR0915 \
  --no-fix --statistics src scripts
```

## Raising the threshold

`max-complexity` lives in `ruff.toml` under `[lint.mccabe]` — one number, one place.
Raising it is an **ask-first** decision per the spec's Boundaries: it weakens the sensor for
every file at once, which is precisely the move that turns a gate into decoration.
