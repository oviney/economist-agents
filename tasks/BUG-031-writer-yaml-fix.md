# BUG-031: Writer Agent YAML Front Matter Fix

**Assigned To:** @refactor-specialist  
**Priority:** HIGH  
**GitHub Issue:** #32  
**Estimated Effort:** 2-3 hours

## Problem Statement

Writer Agent generates blog articles without proper YAML front matter, causing publication validation to fail and articles to be quarantined instead of published.

**Evidence from Workflow Run 20707502129:**
- Article generated but quarantined: `output/quarantine/2026-01-05-understanding-opendns-cybersecurity-protection.md`
- Validation error: "Missing YAML front matter - Article must start with --- delimiter"
- Chart generated successfully but article rejected before reaching blog PR

## Root Cause Analysis

**Component:** `agents/writer_agent.py`  
**Root Cause:** Prompt engineering gap  
**Test Gap:** No integration test validates YAML format before publication validator

**Related Bugs:**
- BUG-028: Writer Agent YAML frontmatter missing opening '---'
- BUG-029: Writer Agent articles too short (478-543 words vs 800+ required)
- BUG-031: Writer Agent generates articles without YAML front matter (THIS BUG)

All three point to systematic prompt engineering issues in Writer Agent.

## Required Fix

### 1. Update Writer Agent Prompts

File: `agents/writer_agent.py` (and possibly `agents/writer_tasks.py`)

**Add explicit YAML front matter requirements:**
```markdown
CRITICAL: Article MUST start with YAML front matter using this EXACT format:

---
title: "Article Title Here"
date: YYYY-MM-DD
categories: [category1, category2]
description: "Brief description"
---

[Article content starts here]
```

**Enforce in self-validation:**
- Check article starts with `---` delimiter
- Verify all required fields present (title, date, categories, description)
- Validate article ends with closing `---` delimiter
- Ensure minimum 800 words after front matter

### 2. Add Integration Test

File: `tests/test_writer_agent_yaml.py` (NEW)

**Test should:**
- Run Writer Agent with test topic
- Validate output starts with `---`
- Check required YAML fields present
- Verify closing `---` delimiter
- Confirm word count >= 800 words
- Run BEFORE publication validator to shift-left detection

### 3. Testing Plan

**Local validation:**
```bash
# Test Writer Agent generates proper YAML
python3 -c "from agents.writer_agent import run_writer_agent; from llm_client import create_llm_client; client = create_llm_client(); article = run_writer_agent(client, 'Test Topic', {}, '2026-01-05', None, None); print('PASS' if article[0].startswith('---') else 'FAIL')"

# Run new integration test
pytest tests/test_writer_agent_yaml.py -v

# Re-run full workflow
gh workflow run content-pipeline.yml -f topic="Understanding OpenDNS: Cybersecurity Protection" -f run_scout=false -f run_board=false -f interactive=false
```

## Success Criteria

- [ ] Writer Agent prompt updated with explicit YAML format requirements
- [ ] Writer Agent self-validation checks for --- delimiters
- [ ] Integration test created and passing
- [ ] Workflow run generates article WITHOUT quarantine
- [ ] Blog PR contains both article markdown AND chart PNG
- [ ] BUG-031 marked fixed in defect_tracker.json
- [ ] GitHub issue #32 closed

## Delegation Notes

This fix should also address BUG-028 and BUG-029 since all three are Writer Agent prompt engineering issues. Consider comprehensive Writer Agent prompt overhaul rather than piecemeal fixes.

**User's Original Goal:** Generate blog post "Understanding OpenDNS: Cybersecurity Protection"  
**Blocker:** This bug prevents completion

**Priority:** Unblocks user's primary objective - HIGHEST PRIORITY FIX
