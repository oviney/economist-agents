# GitHub Copilot Best Practices Skill

This skill provides comprehensive guidance on interacting effectively with GitHub Copilot and AI coding agents in the economist-agents repository.

## Purpose

Ensure all agent interactions follow proven patterns that maximize effectiveness, minimize iterations, and produce high-quality results. These practices are derived from GitHub's official guidance on working with coding agents and adapted for the economist-agents multi-agent system.

## Documents in This Skill

### 1. [SKILL.md](SKILL.md) - Complete Best Practices Guide
**Use when**: Setting up new agents, designing workflows, training team members

**Contents**:
- Core principles (clarity, incremental tasks, examples, quality gates)
- Agent-specific best practices (code modification, features, debugging)
- Integration with economist-agents (agent configs, prompts, skills)
- Common patterns for this repository
- Validation checklists
- Anti-patterns to avoid
- Continuous improvement strategies

**Length**: ~15,000 words | **Read time**: 30-45 minutes

### 2. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - One-Page Cheat Sheet
**Use when**: Making agent requests, need quick reminder

**Contents**:
- 5 essential elements of every request
- Request template
- DO/DON'T examples
- Common patterns (code, features, debugging)
- Agent-specific tips
- Validation commands
- Examples library

**Length**: ~6,000 words | **Read time**: 5-10 minutes

### 3. [AGENT_CHECKLIST.md](AGENT_CHECKLIST.md) - Comprehensive Checklists
**Use when**: Creating agent definitions, writing prompts, validating work

**Contents**:
- Pre-request checklist (context, scope, patterns, validation)
- Agent definition checklist (frontmatter, role, responsibilities, quality gates)
- Prompt engineering checklist (structure, clarity, constraints, examples)
- Skill document checklist (title, principles, guidance, references)
- Incremental task checklist (foundation, implementation, validation)
- Validation command checklist (quality, testing, build, CI)
- Anti-patterns reference
- Perfect request template

**Length**: ~10,000 words | **Read time**: 20-30 minutes

## Quick Start

### For Agent Requests
1. Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md) (5 minutes)
2. Use the request template
3. Check the DO/DON'T examples
4. Verify your request against the 5 essential elements

### For Agent Configuration
1. Read [AGENT_CHECKLIST.md](AGENT_CHECKLIST.md) (20 minutes)
2. Use the agent definition checklist
3. Reference existing agents for patterns
4. Follow the frontmatter structure

### For Deep Understanding
1. Read [SKILL.md](SKILL.md) in full (45 minutes)
2. Review examples for your use case
3. Study integration patterns
4. Learn anti-patterns to avoid

## Integration with Economist-Agents

### Agent Definitions
All agent files in `.github/agents/*.agent.md` now reference this skill:

```yaml
skills:
  - skills/python-quality
  - skills/github-copilot-best-practices  # ← Added
```

### Copilot Instructions
The `.github/copilot-instructions.md` file includes a dedicated section on these best practices, ensuring all AI coding assistants are aware of them.

### Usage in Practice

**When creating a new agent**:
1. Copy an existing agent definition as template
2. Follow [AGENT_CHECKLIST.md](AGENT_CHECKLIST.md) agent definition section
3. Reference this skill in the frontmatter
4. Add best practices reminder in the role section

**When requesting work from an agent**:
1. Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md) template
2. Provide all 5 essential elements
3. Reference patterns from existing code
4. Define clear validation steps

**When writing prompts**:
1. Use [AGENT_CHECKLIST.md](AGENT_CHECKLIST.md) prompt engineering section
2. Include: role, mission, rules, workflow, format, forbidden patterns, quality gates
3. Provide concrete examples
4. Specify error handling

## Key Principles

### 1. Clear and Specific Instructions
AI agents work best with precise, actionable instructions that include context about what you're trying to achieve.

### 2. Incremental Task Breakdown
Break large tasks into smaller, focused steps that can be validated independently.

### 3. Provide Examples and Patterns
Show the agent what "good" looks like by referencing existing code or providing examples.

### 4. Specify Quality Gates and Validation
Define how you'll know the task is complete and what validation is required.

### 5. Reference Documentation Explicitly
Point to specific documentation, skills, or reference files to ground the agent's work.

## Examples

### Good Agent Request
```
Task: Add type hints to all functions in scripts/economist_agent.py

Context:
- File: scripts/economist_agent.py lines 45-200
- Why: Improving code quality, fixing mypy errors (12 errors currently)
- Pattern: Follow type hint style in scripts/topic_scout.py

Changes:
1. Add type hints to function signatures (use dict[str, Any] for JSON)
2. Add return type hints (use Optional[T] for nullable types)
3. Import types from typing module

Validation:
- [ ] Run `mypy scripts/economist_agent.py` → 0 errors
- [ ] Run `make quality` → all checks pass
- [ ] Verify no tests broken: `pytest tests/`

Success: All functions have type hints, mypy passes
```

### Poor Agent Request
```
Fix the agent code
```
(No context, no scope, no validation, no success criteria)

## Continuous Improvement

This skill document is living documentation. As we learn more effective patterns:

1. **Add successful patterns** to the examples sections
2. **Document anti-patterns** from real mistakes
3. **Update checklists** based on what catches issues
4. **Refine templates** to be more effective
5. **Share learnings** across the team

## References

### Internal Documentation
- [.github/copilot-instructions.md](../../.github/copilot-instructions.md) - AI coding instructions
- [.github/agents/](../../.github/agents/) - Agent definitions
- [skills/python-quality/SKILL.md](../python-quality/SKILL.md) - Python standards
- [skills/testing/SKILL.md](../testing/SKILL.md) - Testing standards
- [docs/SCRUM_MASTER_PROTOCOL.md](../../docs/SCRUM_MASTER_PROTOCOL.md) - Process discipline

### External Resources
- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
- [GitHub Copilot Best Practices](https://docs.github.com/en/copilot/using-github-copilot/best-practices-for-using-github-copilot)
- [GitHub Copilot Coding Agent Guide](https://docs.github.com/en/enterprise-cloud@latest/copilot/tutorials/coding-agent/get-the-best-results)

## Feedback & Updates

If you discover patterns that work well or anti-patterns that cause problems:

1. Document them in the appropriate section
2. Add examples to illustrate the pattern
3. Update checklists to include the check
4. Share with the team

---

**Skill Version**: 1.0
**Created**: 2026-01-03
**Status**: Production
**Maintained By**: Economist-Agents Team

**Usage Statistics** (to be tracked):
- Agents referencing this skill: 6/6 (100%)
- Agent request improvement rate: TBD
- Iteration reduction: TBD
- Quality improvement: TBD
