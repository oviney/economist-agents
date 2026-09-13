# Review prompt — is there more code here than the product justifies?

Written 2026-09-10 for a fresh-context reviewer. Pair it with
`docs/repo-state-2026-09-10.md`, which holds the measured baseline.

Keep this file. Re-running the same prompt after changes is how the answer becomes a trend
rather than an opinion.

---

## The prompt

> You are reviewing a Python repository with fresh eyes. Be adversarial and concrete. The
> owner's hypothesis is that **there is far more code here than the product justifies**, and
> your job is to confirm or refute it with evidence, not to agree with it.
>
> **The product.** A pipeline that writes Economist-style articles and publishes them to a
> blog. It has produced **6 articles since 2026-07**, when the current architecture landed;
> 30 posts exist in total, most predating it. One author, no other contributors, no external
> users, run locally on a Claude subscription.
>
> **The repository.** 35,505 lines of production Python (`src/` 11,155 + `scripts/` 24,350)
> and 48,554 lines of tests, plus 11,805 archived. 20 ADRs, 33 specs, 18 skill definitions,
> 281 markdown files, a 2,317-line backlog.
>
> **The measurement already taken.** A static import walk from the 12 real entry points — the
> pipeline, the flow, deploy/art/publish, and every check in the merge gate — finds that
> **55% of production code (18,891 lines, 48 modules) is reachable from no entry point**. But
> classifying those 48 shows **zero orphans**: 16,929 lines are named in a config, Makefile or
> doc, and the remaining 1,962 have tests. Nothing is dead. It is a second system —
> quality metrics, defect tracking, architecture auditing, skills-gap analysis, A/B scout
> comparison, GA4/GSC ETL, dashboards, closed-loop validation, sensor proofs — that measures
> and governs the pipeline rather than being it.
>
> Verify these numbers before relying on them. If any is wrong, say so first.
>
> **Answer these, in order:**
>
> 1. **What is the smallest set of modules that could still produce and publish an article?**
>    Name them. Give a line count. State what would be lost.
>
> 2. **For each of the ten largest modules not reachable from an entry point, what does it buy
>    at a rate of six articles?** Judge each: *keep* (earns its place at this scale), *reduce*
>    (idea is right, implementation is oversized), or *delete* (built for a scale that does not
>    exist). Give a reason tied to something you read, not a general principle.
>
> 3. **Which parts of the second system measure things nobody acts on?** A dashboard nobody
>    opens, a metric no decision consumes, a tracker whose output never changes behaviour. Cite
>    the consumer, or its absence.
>
> 4. **Is the test suite proportionate?** 48,554 lines of tests to 35,505 of code. Which tests
>    protect behaviour a user would notice, and which pin implementation details of tooling
>    that itself might not be needed?
>
> 5. **Is the governance layer** — 20 ADRs, 33 specs, 18 skills, 281 markdown files, a
>    2,317-line backlog — **load-bearing or self-sustaining?** Distinguish documents that
>    change what happens from documents that record that something happened.
>
> 6. **What would you cut first, and what is the argument against cutting it?** Steelman the
>    keep case before you recommend removal.
>
> **Rules.**
>
> - Read the code. Cite file and line. An assertion without a citation will be discarded.
> - Do not propose rewrites, new frameworks, or new abstractions. The question is what to
>   remove, not what to add.
> - "It's tested and documented" is not an argument for keeping something. Everything here is
>   tested and documented; that is what makes this hard.
> - Beware the reverse failure too: some of this may be genuinely load-bearing for a solo
>   operator with no CI and no reviewer. Say so where it is true.
> - Distinguish *lines* from *value*. A 1,200-line module used once a quarter may be fine; a
>   200-line one on the critical path may not be.
> - Deliver a ranked list with estimated lines removed and the risk of removing each.

---

## How to run it

Dispatch to a fresh-context reviewer with repo read access. It must have tools to read files
and run commands — a reviewer that reasons without reading will produce plausible prose, which
is the failure mode this repo has recorded repeatedly (`skills/defect-prevention/SKILL.md`).

Do **not** paste the conclusions of `docs/repo-state-2026-09-10.md` as settled fact beyond the
figures quoted above; the reviewer should re-derive what it relies on.
