# B-042 hand-off — first live acceptance, 2026-08-02

The flow had 2,747 passing tests and had never run. This is what happened when it did.

**Two defects, both invisible to the suite, both in the hand-off itself.** Neither is a
tuning question; both are gates that could not do their job on real input.

## What was verified, and how

### The art gate refuses. Confirmed, not assumed.

Run against the real article with a deliberately invalid token, so a gate failure would
have failed closed at git auth rather than published something.

| Probe | Article state | Outcome |
|---|---|---|
| 1 | as generated — hero comment present | exit 1, `_reject_unrendered_hero_prompt` |
| 2 | comment stripped, no `image:` | exit 1, `_require_hero` — "no `image:` in its frontmatter" |
| 3 | `image:` set, file absent | exit 1, `_require_hero` — "would push a broken `<img>`" |
| 4 | the exact state `make art` leaves | exit 1 — **and it should not have been** |

No clone occurred in any probe (`temp_blog_repo` on disk is from 2026-08-01 17:44, untouched).
The gates sit at `deploy_review` lines 621/623, ahead of the owner/repo/token checks, so the
refusal is not confounded by a missing credential.

**One ordering note.** `main()` requires `--blog-owner`, `--blog-repo` and a token *before*
`deploy_review` is called, so reaching the art gate from the CLI needs full arguments even
though the gate itself never touches them.

### BUG-070 — `make art` produces an article deploy refuses

`finalise_art` delegates to `pipeline._link_hero_asset`, which edits **only the frontmatter**.
The `<!-- HERO IMAGE` comment stays in the body, so the documented sequence — draw hero,
`make art`, `deploy --mode review` — cannot complete. The refusal message tells the owner to
"replace the whole comment with the image reference", which is the job `make art` was
supposed to have done.

**Why 12 passing tests missed it:** every fixture in `test_finalise_art.py` used an article
with no comment in it — input the pipeline never produces. Two gates written in separate
items (BUG-065's comment refusal, B-042's hand-off) had never been run against each other.
The regression test now imports the real gate rather than asserting on a substring.

### BUG-071 — `## References` did not render as a heading

The blog renders with **kramdown**, which unlike CommonMark will not start a block element on
the line after a paragraph. Verified by running kramdown directly:

```
input:   "para text.\n## References\n\n1. A\n"
output:  <p>para text.
         ## References</p>
```

**The stat audit manufactures this, and always has.** `audit_article_stats` splits on
`(?<=[.!?])\s+` — swallowing the newline before `## References` — and rejoins with a single
space. Stage 4's unconditional chart embed used to sit in that gap and supply the blank line
by accident. B-042 deleted that embed, so **the first article generated without a chart is
the first one where the heading breaks.** Both pre-B-042 articles still carry the
`. \n![Chart]…\n\n## References` shape on disk.

**And the CRITICAL check written for exactly this could not see it.** `inline_heading_marker`
used `[^\s]\s##\s`, which allows *one* whitespace character between the sentence and the
marker. The same edit that broke the heading left a trailing space, making the separator two
characters:

| input | caught |
|---|---|
| `deadline.\n## References` | yes |
| `deadline. \n## References` | **no** |
| `deadline. ## References` | yes |

One space silenced a CRITICAL gate. Fixed at both layers — the normaliser so the pipeline
stops emitting it, the check made line-based so it cannot be defeated by whitespace.

## The run

`--research-mode claude_web`, same topic string as the 2026-08-01 run so the ledger rows stay
comparable. Slug **changed**: `migration-deadline-testing-trap`, not
`testing-shortcuts-migration-deadline`. The slug derives from the writer's title.

| | 2026-08-01 (`--brief`) | 2026-08-02 (`claude_web`) |
|---|---|---|
| wall | 31.8 min | see `logs/agent_sdk_costs.jsonl` |
| cost | $1.01 | $0.8597 |
| references | 3, **no URLs** | 6, **all with URLs** |
| chart | 4 invented percentages | none generated; 19 figures *proposed* from the brief |

## Judging the packet as the owner

**Section 3 (chart) — works as designed.** 19 candidate figures, every one traceable to brief
text quoted alongside it, source URLs visible inside several of the context strings. `title`
empty, every `metric` empty, so an untouched proposal will not render. This is the opposite
of the fabricated chart.

Two usability notes, neither a blocker:

1. **Range endpoints are extracted as point values.** The brief says "earmark 15–20% of IT
   budgets" and "spending 30–40%"; the proposal offers rows reading `20 %` and `40 %`. The
   value does appear in the brief, so this is not fabrication — but a chart built from those
   rows would state a range endpoint as a measurement. The quoted context shows the range, so
   a careful reader catches it.
2. **Context strings are cut mid-word** (`'cts: Skipping Rigour Guarantees…'`) because the
   window is a fixed ±60 characters. Snapping to word boundaries would read better.

**Section 2 (hero brief) — usable.** Concrete subject, editorial framing, palette, aspect
ratio, and constraints. Nothing missing.

**Section 1 (verdict) — the one part that misled.** It reported `Publication validator:
PASSED`. With BUG-071 fixed, the same article is **REJECTED — 1 CRITICAL**. The packet was
truthfully reporting what the validator said; the validator was wrong.

## Still the owner's, and why

1. **Re-sourcing the artifact via Claude.ai.** Not done. `claude.ai/recents` shows only
   *"SRE Quality Governance Guide file location"* (Aug 1), a conversation *about* the file.
   The artifact is `SRE_Quality_Governance_Guide (2).html`, downloaded **Jul 21 13:04**, and
   nothing in the list obviously produced it. Pasting a long prompt into a guessed thread was
   not a gamble worth taking, so research was re-sourced the other sanctioned way —
   `claude_web`. **The B-038 HTML→brief path is therefore still unexercised on a re-sourced
   artifact.**
2. **The hero.** Constraint #4 as amended: the owner draws it. `make art` and the deploy are
   blocked behind it, so steps 4 and 5 have not run live.

**`BLOG_REPO_TOKEN` is not the blocker it first appeared to be.** `.env` carries no blog
entries, but `gh` is authenticated as `oviney` with `repo` scope and ADMIN on `oviney/blog`,
so `--token $(gh auth token)` supplies what the deploy needs.

## Read the article before publishing it

The prose passes and the citations resolve, but three things want an editor's eye:

1. **The IBM Systems Sciences Institute 60-to-1 ratio is load-bearing and contested.** It
   carries the section title and the subtitle. The sentence "Those numbers were challenged
   when first published; they have since been corroborated by every serious study that
   followed" has **no citation** and is a strong claim. That figure is widely criticised as
   untraceable to a primary source.
2. **Most references are secondary.** "Via ContextQA", "Via Rockstar Developer University",
   "Curiosity Software … citing McKinsey" — the sourcing prompt asks for primary sources, and
   these are write-ups about them.
3. **The validator still reports 8 quantified claims without inline attribution**, and an
   em-dash density of 1.45/paragraph. Both HIGH, both advisory.

## What did not need doing

`_check_placeholders` still cannot catch the hero comment, and still should not — the deploy
gate owns that, and a second pattern there would be dead code.
