# Economist-Agents

A keyless pipeline that turns the owner's take on a quality-engineering topic into a
published post on www.viney.ca. One writer, one prompt, one owner. The redesign that made
it so is `docs/specs/redesign-owner-voice-first.md` (B-048, approved 2026-09-13).

## Operating Constraints (NON-NEGOTIABLE — never propose against these, never re-litigate)

1. **NO new API keys. Ever.** Including "free-tier" keys. No `ANTHROPIC_API_KEY`,
   `OPENAI_API_KEY`, `SERPER_API_KEY`, `GEMINI_API_KEY` or any other key as a requirement.
2. **No paid third-party services.** No subscriptions, no metered APIs.
3. **The only LLM auth is the Claude subscription** via the Agent SDK (`claude_agent_sdk`
   / the authenticated `claude` CLI). Research is `claude_web` — Claude's own WebSearch.
4. **The owner makes every image.** The pipeline draws nothing — no hero, no chart, no
   raster model, no PIL pixel-pushing. It may *extract* candidate chart figures from the
   research brief (`propose_chart_spec`, labels left empty for the owner) and it may
   *render* a spec the owner has approved (`make art SLUG=<slug>`). A hand-made PNG at the
   same path always wins. Amended 2026-08-01 (B-042) after a mandatory-chart gate produced
   four invented percentages.
5. **No github.com-only workflows for running the pipeline.** It runs locally on the
   subscription.

*Scoped exception (2026-09-02):* the owner's existing OpenRouter key may be used for the
cross-model second opinion in `agent-skills:doubt-driven-development`, on finished work,
asked before each run. Nothing under `src/` or `scripts/` may read it or fall back to it.

If a task seems to need a key or a paid service, do it keyless or say it cannot be done
keyless. Encode any new constraint the owner states into this section immediately.

## Working with the owner

Ouray is the solo owner. These corrections are here so they survive a cleared session.

- **Persist it, don't narrate it.** A lesson worth keeping goes into this file, `BACKLOG.md`,
  an ADR, or a `skills/*/SKILL.md` — never into a closing sentence.
- **No menus.** Decide, state the decision, act. Surface a choice only at a true fork or
  before an irreversible or outward-facing action.
- **Research, then recommend.** Don't ask what the repo can answer.
- **Ruthless simplicity.** A "Not Doing" list is a good outcome.
- **Report faithfully.** Failing tests get shown with output; a skipped step gets said.

## Lifecycle discipline (non-negotiable for anything beyond Q&A or a one-line edit)

1. First two tool calls: `Skill agent-skills:using-agent-skills`, then
   `Skill agent-skills:context-engineering`. Then the phase skill the meta-skill names.
2. No implementation without a spec and a human LGTM; no sprint without a
   dependency-ordered task list. `/goal B-NNN` drives an item spec → LGTM → slices → done.
3. Surface assumptions before implementing anything non-trivial.
4. Only `SKILL.md` workflows are agent-skills; the lifecycle skills load from the
   `agent-skills` plugin (`agent-skills:<name>`). `skills/using-agent-skills/SKILL.md` holds
   this repo's routing contract.

**Backlog is local-first.** `BACKLOG.md` is the source of record (`B-NNN` items, `BUG-NNN`
defects). PRs and code review go through the `gh` CLI. No GitHub issues for backlog items.

## Architecture — one path (ADR-0016)

```
briefs / topic ──► research (claude_web) ──► write (Stage 3) ──► gates (Stage 4) ──► packet
                    src/agent_sdk/research     stage3_runner.py     stage4_runner.py    review_packet.py
                                                                    publication_validator.py
```

- `python -m src.agent_sdk.pipeline --brief briefs/<slug>.md` is the whole run. The brief
  is the owner's take (`briefs/TEMPLATE.md`: thesis, experiences, disagreement, what would
  change his mind); research runs in service of it and the writer argues it in the first
  person. A bare topic still works but produces a research synthesis with none of the owner
  in it, and the packet says so. The run exits 0 when publish-ready and leaves
  `output/posts/<slug>.md`, the review packet, the hero brief (`<slug>.image_prompt.md`)
  and, if the research carried figures, `output/charts/<slug>.spec.json` to frame.
- Stage 1/2 (topic scout, editorial board) were deleted by B-048: the owner is the
  editorial board. `--research-brief docs/research/<slug>.md` feeds a pre-built research
  brief verbatim; `scripts/html_to_brief.py` converts a Claude HTML artifact into one (B-038).
- Deterministic gates in `_shared.py` and `stage4_runner.py`: stat audit (no number that is
  not in the brief), category normalisation, description cap, heading merge, hedging
  removal, British spelling; then `scripts/publication_validator.py`.

## Publishing workflow (NON-NEGOTIABLE — nothing reaches `_posts/` without live review)

```bash
python -m src.agent_sdk.pipeline --brief briefs/<slug>.md                 # 1. generate
#   read output/posts/<slug>.review.md; draw output/posts/images/<slug>-hero.svg;
#   edit output/charts/<slug>.spec.json (title + labels) or delete the rows
make art SLUG=<slug>                                                     # 2. fold art in
python -m scripts.deploy_to_blog --article output/posts/<slug>.md --mode review  # 3. unlisted URL
make publish SLUG=<slug>                                                 # 4. only after reading it live
```

`--mode` is required and has no default, because the old default published article two
unreviewed (B-028). The deploy step refuses an article still carrying the `<!-- HERO IMAGE`
reviewer comment (BUG-065) and, until D7 lands, one with no hero on disk. The `PreToolUse`
hook denies `deploy_to_blog` without `--mode review` — two gates, deliberately. The blog
clone is `temp_blog_repo/` (gitignored); the test suite must never touch it (BUG-082 guard).

## Code standards and the merge gate

Type hints mandatory, docstrings required; `orjson` not `json`; `logger` not `print()`; mock every
network boundary in tests (the suite blocks sockets). Python is pinned by `.python-version`.

**Verification is local-first (ADR-0015).** No CI, `main` unprotected: run `make ci-local`
before merging — ruff, docs-truth, mypy (hard, over live code), pytest + coverage 70%,
bandit. You are the merge gate. The sensors programme (register, proofs, complexity and
post-edit sensors, mypy baseline, destructive-change guard) was retired by B-048 slice 4.

| Variable | Purpose |
|---|---|
| `BLOG_REPO_TOKEN` | Free GitHub token so the deploy step can push to `oviney/blog`. No AI key. |

## Key files

- `docs/specs/redesign-owner-voice-first.md` — the current redesign; its §5 slices are the plan.
- `docs/HANDOFF.md` — cross-session memory; `docs/adr/` — decisions; `docs/archive/` — history.
- `skills/economist-writing/SKILL.md` — the writing rules; `skills/python-quality/SKILL.md` —
  code standards; `skills/using-agent-skills/SKILL.md` — routing contract.
