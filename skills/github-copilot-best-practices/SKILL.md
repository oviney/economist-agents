# GitHub Copilot Agent Best Practices for Economist-Agents

## Overview
This skill document defines best practices for interacting with GitHub Copilot and other AI coding agents, ensuring optimal results when working on the economist-agents multi-agent system. These practices are derived from GitHub's official guidance on getting the best results from coding agents.

## Core Principles

### 1. Clear and Specific Instructions
AI agents work best with precise, actionable instructions that include context about what you're trying to achieve.

**✅ DO:**
- Provide explicit goals: "Add type hints to all functions in scripts/economist_agent.py"
- Include context: "Following the patterns in scripts/topic_scout.py, add error handling"
- Specify constraints: "Use orjson instead of json, maintain British spelling"
- Reference existing patterns: "Use the same prompt structure as RESEARCH_AGENT_PROMPT"

**❌ DON'T:**
- Give vague requests: "Make it better"
- Assume implicit knowledge: "Fix the agent" (which agent? what's broken?)
- Skip context: "Add tests" (what should they test? what coverage target?)

### 2. Incremental Task Breakdown
Break large tasks into smaller, focused steps that can be validated independently.

**✅ DO:**
- "First, add type hints to function signatures"
- "Then, add comprehensive docstrings"
- "Finally, run mypy and fix any type errors"

**❌ DON'T:**
- "Refactor the entire codebase to meet quality standards" (too broad)
- Combine unrelated tasks: "Add tests and fix the chart layout issue" (should be separate)

### 3. Provide Examples and Patterns
Show the agent what "good" looks like by referencing existing code or providing examples.

**✅ DO:**
- "Follow the error handling pattern in scripts/blog_qa_agent.py lines 45-60"
- "Use the same docstring format as the invoke_agent function"
- "Generate charts with the same style constraints as in docs/CHART_DESIGN_SPEC.md"

**❌ DON'T:**
- Expect the agent to infer coding standards without examples
- Assume the agent knows project-specific conventions

### 4. Specify Quality Gates and Validation
Define how you'll know the task is complete and what validation is required.

**✅ DO:**
- "Run `make quality` after changes and fix any violations"
- "Ensure all tests pass with `pytest tests/ -v`"
- "Validate that mypy returns 0 errors"
- "Check that the generated output matches the example in examples/"

**❌ DON'T:**
- Skip validation steps
- Assume the agent knows your quality criteria

### 5. Reference Documentation Explicitly
Point to specific documentation, skills, or reference files to ground the agent's work.

**✅ DO:**
- "Follow the standards in skills/python-quality/SKILL.md"
- "Use the agent prompt format defined in .github/copilot-instructions.md"
- "Adhere to the zone separation rules in docs/CHART_DESIGN_SPEC.md"

**❌ DON'T:**
- Assume the agent has read all documentation
- Reference non-existent files or outdated guides

## Agent-Specific Best Practices

### For Code Modification Requests

**Context to Provide:**
1. **File location**: Full path (e.g., `scripts/economist_agent.py`)
2. **What to change**: Specific function, class, or section
3. **Why**: Business reason or bug being fixed
4. **How**: Approach or pattern to follow
5. **Validation**: How to verify the change works

**Example Request:**
```
Task: Add retry logic to LLM API calls in scripts/economist_agent.py

Context:
- Function: run_research_agent() at line 145
- Pattern: Follow the retry_with_exponential_backoff() pattern from scripts/llm_client.py
- Why: API calls occasionally fail with rate limit errors (BUG-024)
- Validation: Run pytest tests/test_economist_agent.py::test_research_agent_retry

Success criteria:
- Max 3 retries with exponential backoff (1s, 2s, 4s)
- Log each retry attempt with logger.warning()
- Raise APIError after final failure
- Type hints and docstring updated
```

### For New Feature Requests

**Context to Provide:**
1. **User story**: As a [role], I need [capability], so that [benefit]
2. **Acceptance criteria**: Testable conditions for success
3. **Integration points**: What other code this interacts with
4. **Design constraints**: Patterns, styles, or limits to follow
5. **Testing requirements**: Coverage and test types needed

**Example Request:**
```
User Story: As a Content Generator, I need automated chart embedding validation, so that charts are never orphaned in output/charts/ directory

Acceptance Criteria:
1. Writer Agent checks if chart_data exists when generating article
2. If chart exists but no chart markdown in article, raise ValidationError
3. Visual QA validates chart is referenced in text (not just embedded)
4. Prevention pattern added to skills/defect_prevention_rules.py

Implementation Notes:
- Add validate_chart_embedding() to scripts/economist_agent.py
- Follow validation pattern from scripts/blog_qa_agent.py
- Update WRITER_AGENT_PROMPT to include chart embedding requirement
- Add test to tests/test_economist_agent.py

Quality Gates:
- Pytest coverage >80% for new code
- Mypy passes with no errors
- Ruff format and lint pass
```

### For Debugging and Investigation

**Context to Provide:**
1. **Symptom**: What's broken or not working as expected
2. **Expected behavior**: What should happen
3. **Reproduction steps**: How to trigger the issue
4. **Error messages**: Full stack traces or error logs
5. **Recent changes**: What was changed before the issue appeared

**Example Request:**
```
Issue: Chart labels overlapping with X-axis zone (BUG-025)

Symptom: Generated chart in output/charts/article-123.png has labels at y=15, which violates zone boundary (should be >20)

Expected behavior: All inline labels should be placed at y>20 to avoid X-axis intrusion (per docs/CHART_DESIGN_SPEC.md section 3.2)

Reproduction:
1. Run: python3 scripts/generate_chart.py --data examples/chart_data.json
2. Observe: Label "Q4 2025" at coordinates (3.5, 15)
3. Expected: Label should be at (3.5, 25) or higher

Files to investigate:
- scripts/generate_chart.py lines 120-150 (label placement logic)
- Check calculate_label_position() function

Root cause hypothesis: Label y-coordinate not accounting for margin_bottom=20

Fix approach:
- Add min_y_position = margin_bottom + 5 safety buffer
- Update tests/test_generate_chart.py to validate label bounds
```

## Integration with Economist-Agents

### Agent Configuration Best Practices

All agent definition files (.github/agents/*.agent.md) should include:

1. **Role**: Clear, single-sentence description
2. **Responsibilities**: Specific, actionable tasks
3. **Tools Available**: Scripts, commands, or APIs the agent can use
4. **Quality Gates**: What must pass before task is complete
5. **Workflow**: Step-by-step process for common tasks
6. **Examples**: Concrete usage patterns with expected outputs
7. **Anti-Patterns**: What NOT to do (learned from mistakes)

### Prompt Engineering Best Practices

When writing or updating agent prompts (e.g., RESEARCH_AGENT_PROMPT):

**Structure:**
```python
AGENT_NAME_PROMPT = """You are a [role with specific expertise].

YOUR MISSION:
[Clear statement of the agent's purpose]

CRITICAL RULES:
1. [Most important constraint, with rationale]
2. [Second most important constraint]
3. [Third most important constraint]

WORKFLOW:
1. [Step 1 with specific action]
2. [Step 2 with specific action]
3. [Step 3 with specific action]

OUTPUT FORMAT:
[Exact structure expected, with example]

FORBIDDEN PATTERNS:
- [Anti-pattern 1 with example]
- [Anti-pattern 2 with example]

QUALITY GATES:
- [Validation 1: how to check]
- [Validation 2: how to check]
"""
```

**Key Elements:**
- **Explicit constraints**: State what's forbidden, not just what's allowed
- **Concrete examples**: Show the exact output format, not just describe it
- **Error handling**: Specify what to do when things go wrong
- **Escalation paths**: When to ask for human input

### Skills Directory Best Practices

When creating or updating skills (skills/*/SKILL.md):

1. **Title**: Descriptive, matches directory name
2. **Overview**: 2-3 sentences explaining the skill's purpose
3. **Core Principles**: 3-5 fundamental rules or concepts
4. **Detailed Guidance**: Specific patterns, examples, anti-patterns
5. **Integration Points**: How this skill relates to other skills
6. **Validation**: How to verify the skill is being followed
7. **References**: Links to related docs, code, or external resources

**Format Template:**
```markdown
# [Skill Name]

## Overview
[2-3 sentence description of what this skill covers]

## Core Principles
1. [Fundamental rule 1]
2. [Fundamental rule 2]
3. [Fundamental rule 3]

## Detailed Guidance

### [Topic 1]
**✅ DO:**
- [Specific action with example]

**❌ DON'T:**
- [Anti-pattern with explanation]

**Example:**
```[language]
[Code or command example]
```

## Integration Points
- [How this relates to other skills or agents]

## Validation
- [How to verify compliance]

## References
- [Link to related documentation]
```

## Common Patterns for This Repository

### 1. Agent Prompt Updates
```
Task: Update RESEARCH_AGENT_PROMPT to enforce source attribution

Context:
- File: scripts/economist_agent.py lines 28-65
- Issue: Research findings lack explicit sources (BUG-016)
- Pattern: Follow the constraint format in WRITER_AGENT_PROMPT

Changes needed:
1. Add to CRITICAL RULES: "Every statistic MUST have a named source"
2. Add to OUTPUT FORMAT: Include 'sources' array with {claim, source, url}
3. Add to FORBIDDEN PATTERNS: "[UNVERIFIED]" claims in final output

Validation:
- Run economist_agent.py with test topic
- Verify research output includes sources array
- Check that writer agent receives structured sources
```

### 2. Quality Gate Additions
```
Task: Add chart embedding validation to Writer Agent quality gates

Context:
- Agent: Writer Agent in scripts/economist_agent.py
- Issue: Charts generated but not referenced in article text
- Pattern: Follow validation_checks structure in scripts/blog_qa_agent.py

Implementation:
1. Add validate_chart_embedding() after writer agent completes
2. Check if chart_data exists AND chart markdown present in article
3. If missing, raise ValidationError with helpful message
4. Update WRITER_AGENT_PROMPT to mention chart embedding requirement

Testing:
- Create test with chart_data but no markdown → should fail
- Create test with chart_data and markdown → should pass
- Run full pipeline and verify charts are embedded
```

### 3. Skills Learning
```
Task: Store learned pattern from BUG-024 fix in skills system

Context:
- Bug: API rate limits causing silent failures
- Fix: Added retry logic with exponential backoff
- Pattern: All LLM API calls need retry logic

Action:
Use skills_manager.learn_pattern():
- subject: "api_error_handling"
- fact: "All LLM API calls must use retry_with_exponential_backoff()"
- citations: "scripts/llm_client.py:45, BUG-024 fix commit abc1234"
- reason: "Prevents silent failures from transient API errors. Critical for production reliability."
- category: "error_handling"

Result: Future agents will reference this pattern automatically
```

## Validation Checklist

Before submitting work to an AI agent, verify you've provided:

- [ ] **Clear objective**: One-sentence goal statement
- [ ] **Context**: Why this change is needed
- [ ] **Location**: Specific files and line numbers
- [ ] **Pattern reference**: Point to similar existing code
- [ ] **Constraints**: What must be preserved or avoided
- [ ] **Validation steps**: How to verify success
- [ ] **Quality gates**: What automated checks must pass
- [ ] **Examples**: Show expected input/output if applicable

## Anti-Patterns to Avoid

### 1. Vague Instructions
**❌ Bad:** "Make the agents better"
**✅ Good:** "Add error handling with retry logic to all LLM API calls in scripts/, following the pattern in scripts/llm_client.py"

### 2. Missing Context
**❌ Bad:** "Fix the test"
**✅ Good:** "Fix test_research_agent in tests/test_economist_agent.py line 87 - it's failing because the mock API response format changed in commit abc1234"

### 3. Compound Tasks
**❌ Bad:** "Add tests, fix the chart bug, and update documentation"
**✅ Good:** Break into 3 separate tasks, each with clear validation

### 4. Assuming Implicit Knowledge
**❌ Bad:** "Update the prompt to follow our style"
**✅ Good:** "Update RESEARCH_AGENT_PROMPT following the structure in WRITER_AGENT_PROMPT (constraint lists, output format, forbidden patterns)"

### 5. No Validation Criteria
**❌ Bad:** "Add type hints to the functions"
**✅ Good:** "Add type hints to all functions in scripts/economist_agent.py. Run `mypy scripts/economist_agent.py` and fix all errors. Success criteria: mypy returns 0 errors."

## Continuous Improvement

### Learning from Interactions

After each agent interaction, consider:

1. **What worked well?** - Document successful patterns in skills/
2. **What was unclear?** - Update agent definitions or prompts
3. **What was missed?** - Add to quality gates or validation checklists
4. **What took too long?** - Simplify or break down further

### Updating This Skill

As you learn more effective patterns:

1. Add new examples to relevant sections
2. Update anti-patterns with real mistakes encountered
3. Refine validation checklists based on what catches issues
4. Share successful prompt patterns in agent definition files

## References

### Internal Documentation
- `.github/copilot-instructions.md` - AI coding instructions for this repository
- `.github/agents/` - Agent definition files with specific responsibilities
- `skills/python-quality/SKILL.md` - Python coding standards
- `skills/testing/SKILL.md` - Testing patterns and practices
- `docs/SCRUM_MASTER_PROTOCOL.md` - Process discipline and workflow

### External Resources
- [GitHub Copilot Documentation](https://docs.github.com/en/copilot) - Official GitHub Copilot guides
- [GitHub Copilot Best Practices](https://docs.github.com/en/copilot/using-github-copilot/best-practices-for-using-github-copilot) - Effective usage patterns
- [Prompt Engineering Guide](https://www.promptingguide.ai/) - General prompt engineering techniques

### Agent Patterns
- **Research Agent**: Prompts-as-code with explicit constraints (scripts/economist_agent.py)
- **Editorial Board**: Persona-driven voting with weighted consensus (scripts/editorial_board.py)
- **Quality Enforcer**: Skills-based validation with learned patterns (.github/agents/quality-enforcer.agent.md)

---

**Skill Version**: 1.0
**Created**: 2026-01-03
**Last Updated**: 2026-01-03
**Maintained By**: Economist-Agents Team
**Status**: Production

This skill document should be referenced when:
- Creating new agent definitions
- Updating existing agent prompts
- Requesting work from AI coding agents
- Writing instructions for automated workflows
- Training team members on effective AI collaboration
