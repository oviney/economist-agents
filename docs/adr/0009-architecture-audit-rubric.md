# ADR-0009: Architecture Audit Rubric and Calibration Discipline

**Status:** Accepted
**Date:** 2026-04-26
**Decision Maker:** Architect agent (review by staff engineer)
**Supersedes:** —
**Superseded by:** —

## Context

STORY-055 added an "AI Architect" agent and a deterministic audit (`scripts/architecture_audit.py`) that scores every `.github/agents/*.agent.md` file on a six-dimension rubric and emits a JSON + Markdown compliance report. The story's acceptance criterion was "audit produces a quality report with architecture compliance score >85%".

The first implementation pass produced two integrity issues that surfaced in self-review:

1. **Rubric calibration to clear the threshold.** When the corpus initially scored 66.7%, the `output_contract` and `role_clarity` regexes were broadened to recognise additional heading variants — including `## Integration` as evidence of an output contract, which describes how to *invoke* an agent rather than what it *returns*.
2. **Aspirational contracts.** Three agents (`devops`, `code-quality-specialist`, `git-operator`) had JSON output sections written by the architect specifically to lift them above the 85% line. Those JSON shapes described emissions nothing in the system actually produces or validates — documentation drift authored to satisfy the rubric, not the system.

A staff-engineer review of STORY-055 flagged both as the same anti-pattern: a calibration tool you tune to clear its own threshold loses signal for catching future drift.

## Decision

**This project will treat the architecture audit as a measurement instrument, not a compliance ritual.** Specifically:

1. **Rubric corrections** (broadening regexes, adding synonyms) are accepted only when they recognise a documentation convention the corpus *already uses*. The standard is "would I have called this output documentation if the regex didn't exist?", not "does this push the score higher?".
2. **Agent edits** that affect compliance score must reflect contracts the agent actually emits or will emit (the agent.md *is* the prompt; adding instructions to emit a shape is a forward contract). Authoring fictional output sections for agents whose role doesn't naturally produce them is rejected.
3. **Threshold and corpus move together, not opposite each other.** When corpus < target, the gap is a backlog item, not a knob to turn. `DEFAULT_THRESHOLD` is the *measured baseline floor*, bumped only when corpus genuinely reaches a new level.
4. **Regression tests pre-bake the bump.** A test like `test_corpus_below_target_flags_remediation_work` exists specifically to fire when corpus reaches target — instructing the operator to retire the test and bump the threshold. This makes the bump deliberate and visible.

The current rubric scores six dimensions (frontmatter completeness, role clarity, tool minimality, skills mapping, body cohesion, output contract), each 0–2 points. Compliance % = `(total / 12) × 100`. Target is 85%; current corpus baseline is 86.7% (10 agents, measured 2026-04-26).

## Alternatives Considered

1. **Drop the audit entirely.** Rejected — the architect agent needs an enforceable contract or its acceptance criteria are unverifiable. Without a measurement tool, "architecture compliance" is opinion.
2. **Adopt an external rubric (e.g. addyosmani/agent-skills).** Rejected — that rubric scores skill files, not agent files; the dimensions and weights wouldn't match this repo's conventions. The in-repo rubric also doubles as enforcement of the conventions (`docs/skill-anatomy.md` for skills, `.github/agents/*.agent.md` frontmatter contract for agents).
3. **Lower the target to whatever the corpus naturally scores.** Rejected on principle — a target that always equals the current state never demands improvement. The 85% target was set after surveying healthy agent files and identifying what a well-formed file scores under the rubric.
4. **Make the audit advisory rather than gating.** Rejected — without test enforcement, the score drifts silently. The current setup gates `passes_threshold = overall_compliance_pct >= DEFAULT_THRESHOLD` so a regression below baseline fails CI.

## Consequences

- **Positive:** The rubric is an honest signal of corpus health; future contributors can trust that "the audit passes" means the agent corpus actually meets standards rather than that someone tuned the regex.
- **Positive:** The staff-engineer review pattern (self-critique → revert → document) is reusable for any future calibration tool the project adds.
- **Negative:** When corpus < target, the gap is visible and creates real backlog work that must be sequenced into sprints. The project must accept living below target rather than papering it over.
- **Follow-up:** The current corpus has six findings (5 agents with `skills_mapping` issues, 4 agents with partial `output_contract` documentation, 1 agent with no skills declared). Filed as GH issues — see "References" below.
- **Revisit if:** the rubric ever needs broadening to clear a threshold, or if the architect agent itself fails the rubric (its compliance is asserted in `tests/test_architecture_audit.py`).

## References

- `scripts/architecture_audit.py` — implementation
- `tests/test_architecture_audit.py` — rubric + threshold enforcement
- `tests/test_architect_agent.py` — architect agent compliance
- `skills/architecture-patterns/SKILL.md` — rubric documentation
- `.github/agents/architect.agent.md` — agent definition
- ADR-0002 — Agent Registry Pattern (where `.agent.md` files live)
- ADR-0008 — Agent Skill Governance (related: skills format)
- STORY-055 (closed in `data/skills_state/backlog.json`) — original story
- STORY-056 / STORY-057 (closed) — corpus lift work
- Commits `f53b66c`, `4a14e7c`, `1725b9d`, `8a74eab` — implementation history
