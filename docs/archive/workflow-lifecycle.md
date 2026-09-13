# Workflow lifecycle

Every non-trivial task in this repo runs through a lifecycle skill before any code is
written. The skills themselves are **not vendored here** — they load from the
[`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills) plugin, which is the
single source of truth for their semantics and content. This page names the phases and
points at the upstream definitions.

## Why this page exists instead of 20 copies

Until 2026-07-31 this repository carried its own copy of each upstream skill — 20
directories, 5,788 lines, 15 of them byte-identical to upstream and 5 differing by two to
four cosmetic lines. B-035 measured what those copies were doing and the answer was
*nothing*: every skill invoked during a session loads from the plugin's directory, and each
invocation prints the base directory it loaded from. The local copies were never read.

They were, however, free to drift — nothing compared them to upstream — and they
republished a third party's documentation under this site. Deleting them removed 5,788
lines and lost zero instructions, because everything deleted duplicated something that
loads from elsewhere. See `BACKLOG.md` B-035 Task 3(a).

**`using-agent-skills` is the one exception and is still local**, because 32 of its 174
lines are this repo's own Skill Routing Contract rather than upstream content.

## The phases

| Phase | Skill | Use it when |
|---|---|---|
| Define | [`interview-me`](https://github.com/addyosmani/agent-skills/blob/main/skills/interview-me/SKILL.md) | The ask is underspecified and you are filling in blanks silently |
| Define | [`idea-refine`](https://github.com/addyosmani/agent-skills/blob/main/skills/idea-refine/SKILL.md) | The idea is still vague and needs stress-testing |
| Define | [`spec-driven-development`](https://github.com/addyosmani/agent-skills/blob/main/skills/spec-driven-development/SKILL.md) | Any new feature or change — **no implementation starts without a spec** |
| Plan | [`planning-and-task-breakdown`](https://github.com/addyosmani/agent-skills/blob/main/skills/planning-and-task-breakdown/SKILL.md) | A spec exists and needs a dependency-ordered task list |
| Build | [`context-engineering`](https://github.com/addyosmani/agent-skills/blob/main/skills/context-engineering/SKILL.md) | Session start, or output quality is drifting |
| Build | [`incremental-implementation`](https://github.com/addyosmani/agent-skills/blob/main/skills/incremental-implementation/SKILL.md) | Implementing anything touching more than one file |
| Build | [`source-driven-development`](https://github.com/addyosmani/agent-skills/blob/main/skills/source-driven-development/SKILL.md) | Correctness depends on a framework's actual documented behaviour |
| Build | [`doubt-driven-development`](https://github.com/addyosmani/agent-skills/blob/main/skills/doubt-driven-development/SKILL.md) | Stakes are high or the code is unfamiliar |
| Build | [`api-and-interface-design`](https://github.com/addyosmani/agent-skills/blob/main/skills/api-and-interface-design/SKILL.md) | Designing a module boundary or public interface |
| Build | [`frontend-ui-engineering`](https://github.com/addyosmani/agent-skills/blob/main/skills/frontend-ui-engineering/SKILL.md) | Building user-facing interfaces |
| Verify | [`test-driven-development`](https://github.com/addyosmani/agent-skills/blob/main/skills/test-driven-development/SKILL.md) | Any logic, any bug fix — RED → GREEN → REFACTOR |
| Verify | [`debugging-and-error-recovery`](https://github.com/addyosmani/agent-skills/blob/main/skills/debugging-and-error-recovery/SKILL.md) | Something broke and the cause is not yet known |
| Verify | [`browser-testing-with-devtools`](https://github.com/addyosmani/agent-skills/blob/main/skills/browser-testing-with-devtools/SKILL.md) | Verifying behaviour that only exists in a browser |
| Review | [`code-review-and-quality`](https://github.com/addyosmani/agent-skills/blob/main/skills/code-review-and-quality/SKILL.md) | Before merging anything |
| Review | [`code-simplification`](https://github.com/addyosmani/agent-skills/blob/main/skills/code-simplification/SKILL.md) | Code works but reads worse than it should |
| Review | [`security-and-hardening`](https://github.com/addyosmani/agent-skills/blob/main/skills/security-and-hardening/SKILL.md) | Handling untrusted input, auth, or external integrations |
| Review | [`performance-optimization`](https://github.com/addyosmani/agent-skills/blob/main/skills/performance-optimization/SKILL.md) | A measured performance problem exists |
| Ship | [`git-workflow-and-versioning`](https://github.com/addyosmani/agent-skills/blob/main/skills/git-workflow-and-versioning/SKILL.md) | Committing, branching, resolving conflicts |
| Ship | [`ci-cd-and-automation`](https://github.com/addyosmani/agent-skills/blob/main/skills/ci-cd-and-automation/SKILL.md) | Changing build or deployment pipelines |
| Ship | [`documentation-and-adrs`](https://github.com/addyosmani/agent-skills/blob/main/skills/documentation-and-adrs/SKILL.md) | Recording an architectural decision |
| Ship | [`deprecation-and-migration`](https://github.com/addyosmani/agent-skills/blob/main/skills/deprecation-and-migration/SKILL.md) | Removing or migrating off an old system |
| Ship | [`shipping-and-launch`](https://github.com/addyosmani/agent-skills/blob/main/skills/shipping-and-launch/SKILL.md) | Deploying to production |

## Routing

[`using-agent-skills`](skills/using-agent-skills/SKILL.md) is the meta-skill: it triages a
task to the right phase and carries this repo's Skill Routing Contract, which governs how
the next skill is chosen. Two rules from it are worth stating here:

- **Only `SKILL.md` workflows are agent-skills.** Plugin commands, MCP tools and repo-local
  agent personas are never agent-skills and must never be offered as the next one.
- **If the next lifecycle skill is not installed, say so** rather than substituting
  something else.

The repo's own domain skills — Economist writing, Python quality, defect prevention and the
rest — are listed under **Skills → Domain** in the nav and *are* maintained here.
