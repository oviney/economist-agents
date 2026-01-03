# Agent Interaction Checklist

Use this checklist when requesting work from AI agents or creating new agent definitions to ensure GitHub Copilot best practices are followed.

## Pre-Request Checklist

Before requesting work from an AI agent, verify you have:

### Context & Objective
- [ ] Clear one-sentence objective stated
- [ ] Context provided (why this change is needed)
- [ ] Business value or problem statement explained
- [ ] Target outcome specified

### Location & Scope
- [ ] Specific files and line numbers identified
- [ ] Scope clearly bounded (which functions/classes/modules)
- [ ] Related files or dependencies noted
- [ ] Output locations specified

### Patterns & Constraints
- [ ] Referenced similar existing code as pattern
- [ ] Pointed to relevant skills documentation
- [ ] Listed constraints (what must be preserved)
- [ ] Identified anti-patterns to avoid
- [ ] Specified coding standards to follow

### Validation & Quality
- [ ] Defined "done" criteria (what success looks like)
- [ ] Listed validation steps (how to verify)
- [ ] Specified quality gates (automated checks)
- [ ] Identified testing requirements
- [ ] Set coverage or quality metrics targets

### Examples & Documentation
- [ ] Provided input/output examples if applicable
- [ ] Referenced relevant documentation
- [ ] Linked to related issues or PRs
- [ ] Included error messages or logs if debugging

## Agent Definition Checklist

When creating or updating agent definition files (.github/agents/*.agent.md):

### Frontmatter (YAML)
- [ ] `name`: Matches filename (kebab-case)
- [ ] `description`: Clear, one-line summary
- [ ] `model`: Specified (e.g., claude-sonnet-4-20250514)
- [ ] `tools`: Listed (bash, file_search, etc.)
- [ ] `skills`: Referenced (including github-copilot-best-practices)

### Role & Mission
- [ ] **Role**: Single-sentence description of the agent's expertise
- [ ] **Mission**: Clear statement of purpose
- [ ] **Best Practices Reference**: Links to github-copilot-best-practices skill
- [ ] **Key Principles**: 3-5 fundamental rules specific to this agent

### Responsibilities
- [ ] Specific, actionable tasks listed
- [ ] Organized by category or workflow
- [ ] Prioritized (most important first)
- [ ] Cross-references to related agents or tools

### Tools & Commands
- [ ] Available scripts and their usage
- [ ] CLI commands with examples
- [ ] API integrations documented
- [ ] File paths and locations specified

### Workflow & Process
- [ ] Step-by-step workflows for common tasks
- [ ] Decision trees for complex scenarios
- [ ] Handoff protocols to other agents
- [ ] Escalation paths when stuck

### Quality Gates
- [ ] Pre-execution gates (what must be ready)
- [ ] Post-execution gates (what must pass)
- [ ] Validation commands listed
- [ ] Success criteria defined

### Examples
- [ ] Concrete usage examples provided
- [ ] Input/output pairs shown
- [ ] Common scenarios covered
- [ ] Edge cases illustrated

### Anti-Patterns
- [ ] Common mistakes documented
- [ ] What NOT to do listed
- [ ] Learned from past issues
- [ ] Includes rationale for why to avoid

### Integration Points
- [ ] Related agents identified
- [ ] Shared context or data files noted
- [ ] Handoff protocols defined
- [ ] Dependencies documented

### References
- [ ] Links to internal docs
- [ ] Links to skills
- [ ] Links to example code
- [ ] Links to external resources if needed

## Prompt Engineering Checklist

When creating or updating agent prompts (e.g., RESEARCH_AGENT_PROMPT):

### Structure
- [ ] Clear role statement at the top
- [ ] Mission or purpose explicitly stated
- [ ] Critical rules section with rationale
- [ ] Workflow steps enumerated
- [ ] Output format specified with example
- [ ] Forbidden patterns listed
- [ ] Quality gates defined

### Clarity
- [ ] Uses imperative language ("Do X", "Never Y")
- [ ] Avoids ambiguous terms
- [ ] Provides concrete examples
- [ ] Specifies exact output format
- [ ] Includes edge case handling

### Constraints
- [ ] Explicit "MUST" requirements
- [ ] Explicit "NEVER" prohibitions
- [ ] Boundary conditions defined
- [ ] Error handling specified
- [ ] Escalation paths included

### Examples
- [ ] Good examples provided
- [ ] Bad examples (anti-patterns) shown
- [ ] Input/output pairs included
- [ ] Edge cases illustrated

### Validation
- [ ] Success criteria defined
- [ ] Validation steps listed
- [ ] Quality metrics specified
- [ ] Testing approach included

## Skill Document Checklist

When creating or updating skill documents (skills/*/SKILL.md):

### Title & Overview
- [ ] Title matches directory name
- [ ] Overview (2-3 sentences) explains purpose
- [ ] Scope clearly defined
- [ ] Target audience identified

### Core Principles
- [ ] 3-5 fundamental rules
- [ ] Clearly numbered or bulleted
- [ ] Rationale provided for each
- [ ] Prioritized by importance

### Detailed Guidance
- [ ] Organized by topic
- [ ] Uses "DO" and "DON'T" sections
- [ ] Provides concrete examples
- [ ] Includes code snippets
- [ ] Shows before/after comparisons

### Integration Points
- [ ] Related skills referenced
- [ ] Agent interactions explained
- [ ] Workflow integration described
- [ ] Data flow documented

### Validation
- [ ] How to verify compliance
- [ ] Automated checks listed
- [ ] Manual review steps if needed
- [ ] Quality metrics defined

### Examples
- [ ] Multiple examples provided
- [ ] Cover common scenarios
- [ ] Include edge cases
- [ ] Show expected results

### References
- [ ] Internal docs linked
- [ ] External resources cited
- [ ] Related agents listed
- [ ] Version and date included

## Incremental Task Checklist

When breaking down large tasks into incremental steps:

### Task 1: Foundation
- [ ] Clear objective defined
- [ ] Prerequisites identified
- [ ] Expected output specified
- [ ] Validation steps listed
- [ ] Estimated effort noted

### Task 2: Core Implementation
- [ ] Builds on Task 1 results
- [ ] Dependencies clearly stated
- [ ] Incremental progress defined
- [ ] Testing approach specified

### Task 3: Validation & Refinement
- [ ] Quality checks defined
- [ ] Edge cases covered
- [ ] Performance validated
- [ ] Documentation updated

### Final Integration
- [ ] All pieces integrated
- [ ] Full system tested
- [ ] Documentation complete
- [ ] Ready for review

## Validation Command Checklist

Common validation commands to include in agent instructions:

### Python Quality
- [ ] `ruff format --check .` - Check formatting
- [ ] `ruff check .` - Check linting
- [ ] `mypy scripts/` - Check type hints
- [ ] `make quality` - Run all quality checks

### Testing
- [ ] `pytest tests/ -v` - Run all tests
- [ ] `pytest tests/ --cov=scripts` - Run with coverage
- [ ] `pytest tests/test_specific.py::test_case` - Run specific test

### Build & Integration
- [ ] Script-specific commands (e.g., `python3 scripts/economist_agent.py`)
- [ ] Integration tests
- [ ] End-to-end workflows

### Git & CI
- [ ] `git status` - Check changed files
- [ ] `git diff` - Review changes
- [ ] CI/CD pipeline status check

## Common Anti-Patterns to Avoid

### Vague Instructions
- ❌ "Make it better"
- ❌ "Fix the agent"
- ❌ "Add some tests"
- ✅ "Add type hints to all functions in scripts/economist_agent.py and run mypy to validate"

### Missing Context
- ❌ "Update the prompt"
- ❌ "Fix the bug"
- ✅ "Update RESEARCH_AGENT_PROMPT to require source attribution for all statistics (BUG-016 fix)"

### Compound Tasks
- ❌ "Add tests, fix bugs, and update docs"
- ✅ Task 1: "Add tests for scripts/economist_agent.py"
- ✅ Task 2: "Fix BUG-016 in research agent"
- ✅ Task 3: "Update docs/ARCHITECTURE.md"

### No Validation
- ❌ "Add error handling to the API calls"
- ✅ "Add retry logic with exponential backoff to all LLM API calls. Validate with pytest tests/test_api_retry.py"

### Assuming Knowledge
- ❌ "Follow our coding standards"
- ✅ "Follow standards in skills/python-quality/SKILL.md: type hints, docstrings, orjson, logger"

## Quick Reference: Perfect Agent Request Template

```markdown
## Objective
[One clear sentence describing the goal]

## Context
- **Why**: [Business reason or problem being solved]
- **Related**: [Links to issues, PRs, or docs]
- **Impact**: [Who benefits and how]

## Scope
- **Files**: [Specific files and line numbers]
- **Functions**: [Which functions or classes]
- **Out of Scope**: [What NOT to change]

## Pattern Reference
- **Similar Code**: [Point to existing example]
- **Skills**: [List relevant skills documents]
- **Standards**: [Coding standards to follow]

## Constraints
- [Constraint 1: What must be preserved]
- [Constraint 2: What must be avoided]
- [Constraint 3: Required patterns]

## Implementation Steps
1. [Step 1 with validation]
2. [Step 2 with validation]
3. [Step 3 with validation]

## Validation
- [ ] [Automated check 1]
- [ ] [Automated check 2]
- [ ] [Manual verification step]

## Success Criteria
- [Measurable outcome 1]
- [Measurable outcome 2]
- [Quality metric target]

## Examples
**Input**: [Example input]
**Expected Output**: [Example output]
**Edge Case**: [How to handle]
```

## Resources

- [skills/github-copilot-best-practices/SKILL.md](SKILL.md) - Full best practices guide
- [.github/copilot-instructions.md](../../.github/copilot-instructions.md) - Repository-wide AI instructions
- [.github/agents/](../../.github/agents/) - Agent definition files
- [skills/python-quality/SKILL.md](../python-quality/SKILL.md) - Python coding standards
- [skills/testing/SKILL.md](../testing/SKILL.md) - Testing standards

---

**Version**: 1.0
**Created**: 2026-01-03
**Status**: Production

Use this checklist for:
- Requesting work from AI agents
- Creating new agent definitions
- Updating existing agents
- Writing prompts
- Designing workflows
- Quality assurance
