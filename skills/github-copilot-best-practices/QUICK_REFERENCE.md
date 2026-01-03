# GitHub Copilot Agent Best Practices - Quick Reference

## The 5 Essential Elements

Every agent request should include:

1. **Clear Objective** - One-sentence goal
2. **Context** - Why this change is needed
3. **Pattern Reference** - Point to similar code
4. **Constraints** - What to preserve/avoid
5. **Validation** - How to verify success

## Request Template

```
Task: [One clear sentence]

Context:
- File: [path/to/file.py line X-Y]
- Why: [Business reason or bug being fixed]
- Pattern: Follow [reference to similar code]

Changes:
1. [Specific change with validation]
2. [Specific change with validation]

Validation:
- [ ] Run [command] and verify [outcome]
- [ ] Check [criteria]

Success: [Measurable outcome]
```

## DO ✅

- **Be Specific**: "Add type hints to lines 45-60 in scripts/economist_agent.py"
- **Provide Context**: "Fixing BUG-016: unverified statistics in research output"
- **Reference Patterns**: "Follow the error handling in scripts/llm_client.py"
- **Define Done**: "Run `mypy scripts/` and get 0 errors"
- **Give Examples**: Show input/output pairs

## DON'T ❌

- **Be Vague**: "Make it better", "Fix the agent"
- **Skip Context**: "Update the prompt" (which prompt? why?)
- **Combine Tasks**: "Add tests, fix bugs, update docs" (do separately)
- **Assume Knowledge**: "Follow our standards" (which standards? where?)
- **Skip Validation**: "Add error handling" (how do I verify it works?)

## Common Patterns

### Code Modification
```
Task: Add retry logic to LLM API calls in scripts/economist_agent.py

Context:
- Function: run_research_agent() at line 145
- Why: API calls fail with rate limits (BUG-024)
- Pattern: Use retry_with_exponential_backoff() from scripts/llm_client.py

Changes:
1. Wrap API call in retry decorator (max 3 attempts, 1s/2s/4s backoff)
2. Log each retry with logger.warning()
3. Raise APIError after final failure

Validation:
- [ ] pytest tests/test_economist_agent.py::test_research_agent_retry passes
- [ ] mypy shows no type errors
- [ ] Manually trigger rate limit and verify retries

Success: API calls succeed after transient failures
```

### New Feature
```
Task: Add chart embedding validation to Writer Agent

Context:
- Issue: Charts generated but not referenced in articles (BUG-016)
- Pattern: Follow validation_checks in scripts/blog_qa_agent.py

Implementation:
1. Add validate_chart_embedding() function
2. Check chart_data exists AND chart markdown in article
3. Raise ValidationError if missing

Validation:
- [ ] Test with missing chart markdown → fails correctly
- [ ] Test with valid embedding → passes
- [ ] pytest coverage >80%

Success: No orphaned charts in output/charts/
```

### Debugging
```
Task: Fix chart label overlap with X-axis (BUG-025)

Context:
- Symptom: Labels at y=15, violates zone boundary (should be >20)
- File: scripts/generate_chart.py lines 120-150
- Expected: Labels placed at y>20 per docs/CHART_DESIGN_SPEC.md

Investigation:
1. Check calculate_label_position() function
2. Verify margin_bottom=20 is applied
3. Add safety buffer: min_y_position = margin_bottom + 5

Validation:
- [ ] Generate chart with examples/chart_data.json
- [ ] Measure label y-coordinates (all should be >20)
- [ ] Update tests/test_generate_chart.py with bounds check

Success: All labels placed above y=20
```

## Agent-Specific Tips

### @quality-enforcer
- Reference: `skills/python-quality/SKILL.md`
- Focus: Type hints, docstrings, error handling
- Validation: `make quality` must pass

### @test-writer
- Reference: `skills/testing/SKILL.md`
- Focus: Coverage >80%, mock all APIs
- Validation: `pytest tests/ -v --cov`

### @refactor-specialist
- Reference: `skills/python-quality/SKILL.md`
- Focus: One file at a time, preserve functionality
- Validation: Tests still pass after refactoring

### @scrum-master
- Reference: `skills/github-copilot-best-practices/SKILL.md`
- Focus: Clear stories, incremental tasks, DoR validation
- Validation: All 8 DoR criteria met

### @po-agent
- Reference: `skills/github-copilot-best-practices/SKILL.md`
- Focus: Clear acceptance criteria, testable outcomes
- Validation: >90% AC approval rate

## Validation Commands

```bash
# Python Quality
ruff format --check .          # Check formatting
ruff check .                   # Check linting
mypy scripts/                  # Check types
make quality                   # All quality checks

# Testing
pytest tests/ -v               # Run all tests
pytest tests/ --cov=scripts    # With coverage
pytest tests/test_X.py::test_Y # Specific test

# Integration
python3 scripts/economist_agent.py  # Run main pipeline
python3 scripts/generate_chart.py   # Test chart generation
```

## Quick Checklist

Before submitting to an agent:
- [ ] Clear one-sentence objective
- [ ] Context (why needed)
- [ ] File/line location
- [ ] Pattern reference
- [ ] Constraints listed
- [ ] Validation steps
- [ ] Success criteria

## Examples Library

### Perfect Request
✅ **GOOD**: "Add type hints to all functions in scripts/economist_agent.py (lines 45-200), following the pattern in scripts/topic_scout.py. Run `mypy scripts/economist_agent.py` and fix all errors. Success: 0 mypy errors."

### Vague Request
❌ **BAD**: "Make the economist agent better"

### Missing Context
❌ **BAD**: "Fix the test"
✅ **GOOD**: "Fix test_research_agent in tests/test_economist_agent.py line 87 - it's failing because the mock API response format changed in commit abc1234. Update the mock to use new format: {'content': '...', 'model': '...'}"

### Compound Task
❌ **BAD**: "Add tests, fix the chart bug, and update docs"
✅ **GOOD**: 
- Task 1: "Add tests for scripts/economist_agent.py (aim for >80% coverage)"
- Task 2: "Fix chart label overlap bug (BUG-025)"
- Task 3: "Update docs/ARCHITECTURE.md with new chart validation"

## Resources

Full documentation:
- [skills/github-copilot-best-practices/SKILL.md](SKILL.md)
- [skills/github-copilot-best-practices/AGENT_CHECKLIST.md](AGENT_CHECKLIST.md)
- [.github/copilot-instructions.md](../../.github/copilot-instructions.md)

Agent definitions:
- [.github/agents/](../../.github/agents/)

---

**Keep this reference handy when requesting work from AI agents!**

Print it, bookmark it, or keep it open in a tab. Following these patterns will dramatically improve agent effectiveness and reduce back-and-forth iterations.
