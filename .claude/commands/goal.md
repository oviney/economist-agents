---
description: Drive a whole backlog goal to completion through the lifecycle skills — spec to shipped, slice by slice, gate-verified
argument-hint: <B-NNN or a goal statement>
---

Goal: **$ARGUMENTS**

You are running this to *completion*, not to a checkpoint. A phase command
(`/spec`, `/build`, `/ship`) does one step and stops. This one owns the goal
until its exit criteria are met or a boundary blocks it.

## 0 · Mandated opening (CLAUDE.md lifecycle discipline)

First two tool calls, in order, no exceptions:
1. `Skill agent-skills:using-agent-skills`
2. `Skill agent-skills:context-engineering`

## 1 · Resolve the goal before doing anything

- `B-NNN` → read that entry in `BACKLOG.md` **and** any matching
  `docs/specs/B-NNN-*.md`.
- Free-form goal → search `BACKLOG.md` for an existing item first. Do not open a
  second front on work already tracked.

**If a spec exists, that spec is the contract.** Do not re-spec it, do not
re-litigate its decisions, do not "improve" its scope. Its slices are your task
list; its Boundaries section is your permission model; its Errata is a record of
mistakes already made — read it so you don't repeat them.

**If no spec exists:** invoke `agent-skills:spec-driven-development`, write one,
and **stop for the owner's LGTM.** No implementation without a spec and a human
LGTM — that is non-negotiable, and "the goal seemed obvious" is not an exemption.

## 2 · Verify the goal is still true

Specs rot. Before slice 1, re-measure the claims the plan depends on — the file
still exists, the caller is still live, the test count is still what was
recorded. **Before claiming code is unreachable, run it.** A worktree and a test
run beat any amount of grepping; two rounds of grep-based reasoning have already
been overturned in this repo.

Record the current baseline (`make ci-local`: pass / skip / coverage) so every
later diff is against a measured number, not a remembered one.

## 3 · Execute slice by slice

Invoke `agent-skills:incremental-implementation` with
`agent-skills:test-driven-development`. Per slice:

1. Read the slice's stated cost. If it deletes a capability, that loss was named
   in the spec — confirm it is still acceptable, don't rediscover it after.
2. RED → GREEN → refactor for anything with behaviour.
3. `make ci-local`. It is the merge gate; there is no CI to catch you.
4. Compare counts to the baseline. Coverage drift from deleting well-covered
   code is expected and is not a regression — say which it is.
5. Commit the slice on its own, counts in the message.
6. Update the `BACKLOG.md` entry with what landed. A compacted session must be
   able to resume from the repo alone.

A failing gate routes to `agent-skills:debugging-and-error-recovery`. Never
delete a test to make a gate pass.

## 4 · Close the loop

- `agent-skills:code-review-and-quality` on the accumulated diff.
- `agent-skills:doubt-driven-development` if the goal changed shape while you
  worked — a plan that drifted deserves one adversarial pass before it ships.
- `agent-skills:shipping-and-launch` only if the goal actually ships something.
- Update `BACKLOG.md`: item done, defects it closes marked closed in
  `data/skills_state/defect_tracker.json` (gitignored — `BACKLOG.md` is the
  durable record).

## 5 · Boundaries

- **Never stop mid-goal to ask "should I continue?"** Continue. The slices are
  approved.
- **Do stop** at anything the spec's Boundaries mark ask-first, at any
  irreversible or outward-facing action, and at any point the evidence
  contradicts the spec — report the contradiction, don't route around it.
- **Report faithfully.** Failing tests get shown with output. A skipped step gets
  said. Partial completion gets named as partial, with what is left and why.
