# ADR-0020: The owner's voice is the input, not the gate

**Status:** Accepted
**Date:** 2026-09-13
**Decision Maker:** Ouray Viney (owner)
**Supersedes:** *(none — amends ADR-0016 "one pipeline path" by moving where the path starts, and retires the editorial-score half of ADR-0018)*
**Superseded by:**

## Context

By 2026-09-10 the repository was roughly 40,000 lines of production Python, 48,000 of
tests and 376 markdown files, of which about 7,000 lines produced and published an
article. Since July it had received 173 commits and published five posts. Two reviews
(`docs/archive/repo-state-2026-09-10.md`, `docs/archive/reviews/2026-09-10-fable-complexity-review.md`)
measured that; the spec this ADR records (`docs/specs/redesign-owner-voice-first.md`)
asked the question one level up.

The mission statement was "Economist-style articles with verified sources". The blog's
About page promised "two decades of quality-engineering practice distilled". The
pipeline resolved the conflict in favour of the first: the Economist voice is
institutional and never says "I", the writer prompt enforced it, and 20 of 29 published
posts contained no first-person word at all. The only owner input per article was a topic
string; his judgment entered as an approve/reject of a thousand finished words. Quality
was operationalised as regex compliance (25 validator checks, a 5-dimension scorer), no
reader signal was captured, and a blocking form gate had already manufactured a
fabrication once (B-042). The system optimised what its author knew how to optimise —
gates — and the harder asset, his voice, went unbuilt.

## Decision

This project will start every article from the owner's brief — his thesis, his
experiences, his disagreement, what would change his mind (`briefs/TEMPLATE.md`) — with
research run in service of that take and a writer whose identity is the editor of a
practitioner's column, first person expected. The pipeline is one straight line
(brief → research → write → gates → packet); Stage 1/2 and the "second system" of
metrics, trackers and sensors are deleted, not disabled. Gates split into blocking
(reader-protecting invariants: no unsourced number, links that resolve, no placeholder or
reviewer comment, a buildable frontmatter) and advisory (style, listed in the packet for
the owner). The quality loop closes with the owner's own post-publish verdict in the
brief, the last five of which steer the next draft; there is no editorial score. The
merge gate is ruff, docs-truth, mypy, pytest with coverage, and bandit; the constraint
guard and session hooks stay.

## Alternatives Considered

- **Keep the Economist identity and add an "experience" section.** Rejected: an
  anonymous institutional voice under a personal byline reads as exactly what it is, and
  the identity was the thing forbidding the moat.
- **Keep Stage 1/2 for autonomous topic discovery.** Rejected: seven synthetic personas
  voting is a simulation of an editorial meeting for a one-person publication, and had
  published nothing since July. The owner is the editorial board.
- **Calibrate the editorial scorer instead of deleting it (B-040).** Rejected: every
  dimension scored form; ADR-0018 had measured what an LLM judge costs; the owner reads
  every draft anyway, so an advisory list beside it is worth more than a quarantine.
- **Keep the sensors programme.** Rejected: it guarded the second system from itself.
  What remains is the constraint guard, which protects the owner's stated constraints
  from any future session, and plain checks in `ci-local`.
- **Add a reader-analytics loop.** Rejected: constraint #1. GA4 is read by eye, monthly.

## Consequences

Measured after slice 6 (2026-09-13): production Python from ~39,800 lines in 98 files to
10,448 in 37; tests from 48,554 lines to 13,239; markdown outside `docs/archive/` from 376
files to 50; the merge gate from 154 s to about a minute. Three things are open and recorded in `BACKLOG.md` under B-048: the
live acceptance of a real owner brief (needs the owner to write one); D7, hero optional,
which the evidence blocked — `oviney/blog`'s own `validate-post-quality.sh` errors on a
post with no hero, so the change is on the blog side; and D10, the stage-per-file
rewrite, whose gate is three real runs to a review URL.

The owner must now write about 200 words before a run. That is the point: a post he
could not write 200 words of take for is a post he has nothing to say about.
