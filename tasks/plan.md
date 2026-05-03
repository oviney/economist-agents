# Plan: Fix shell injection in regenerate-image.yml (issue #342)

**Spec**: SPEC.md
**Date**: 2026-05-03

## Injection inventory

16 `${{ inputs.* }}` references in `run:` blocks:
- `${{ inputs.slug }}` — 14 instances (lines 54, 60, 61, 70, 75, 89×2, 90×2,
  94, 95, 96, 102, 105, 107)
- `${{ inputs.topic }}` — 1 instance (line 51)
- `${{ inputs.summary }}` — 1 instance (line 52)
- `${{ inputs.mood }}` — 1 instance (line 53) — SAFE (`type: choice`), no change

## Dependency graph

```
T1 (add job-level env: block + validation step)
  └──► T2 (replace all 16 ${{ inputs.* }} in run: blocks with $SLUG/$TOPIC/$SUMMARY)
         └──► T3 (grep assertion + manual verification notes + close #342)
```

## Tasks

### T1 — Add job-level `env:` and validation step

**File**: `.github/workflows/regenerate-image.yml`

1. Add `env:` block at the job level (between `runs-on:` and `steps:`):
   ```yaml
   env:
     SLUG: ${{ inputs.slug }}
     TOPIC: ${{ inputs.topic }}
     SUMMARY: ${{ inputs.summary }}
   ```

2. Insert a `Validate inputs` step as the first step (before `actions/checkout`):
   ```yaml
   - name: Validate inputs
     run: |
       if [[ ! "$SLUG" =~ ^[a-z0-9][a-z0-9-]{0,79}$ ]]; then
         echo "::error::Invalid slug '$SLUG': must match ^[a-z0-9][a-z0-9-]{0,79}$"
         exit 1
       fi
       if [[ ${#TOPIC} -gt 200 ]]; then
         echo "::error::topic exceeds 200 characters"
         exit 1
       fi
       if [[ ${#SUMMARY} -gt 500 ]]; then
         echo "::error::summary exceeds 500 characters"
         exit 1
       fi
   ```

DoD: `grep "SLUG:\|TOPIC:\|SUMMARY:" .github/workflows/regenerate-image.yml`
shows the env block; `Validate inputs` step exists before `actions/checkout`.

---

### T2 — Replace all `${{ inputs.* }}` references in `run:` blocks

**File**: `.github/workflows/regenerate-image.yml`

Replace every occurrence of `${{ inputs.slug }}`, `${{ inputs.topic }}`, and
`${{ inputs.summary }}` in `run:` blocks with `$SLUG`, `$TOPIC`, and `$SUMMARY`
respectively. `${{ inputs.mood }}` stays as-is.

14 slug replacements, 1 topic, 1 summary = 16 total.

DoD:
```bash
grep -c '\${{ inputs\.slug\|inputs\.topic\|inputs\.summary' \
  .github/workflows/regenerate-image.yml
# Must return 0
```

---

### T3 — Verify and close #342

1. Run the DoD grep from T2 — confirm 0 injection points remain in `run:` blocks.
2. Confirm `${{ inputs.mood }}` is unchanged (1 occurrence in the shell step, safe).
3. Close #342 with a summary.

No pytest tests for workflow YAML. Manual test instructions are in SPEC.md §5.
