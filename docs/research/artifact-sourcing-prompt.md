# Prompt: make a research artifact citable before it becomes a brief

Paste this back into the **same Claude.ai conversation that produced the HTML artifact**, so
it still has the argument in context. It asks for the same analysis re-emitted with resolvable
sources attached, rather than a fresh piece of research.

## Why this exists

Measured on 2026-08-01, the first real B-038 run. The artifact
(`sre-quality-governance-guide.html`) contained **zero `<a href>` and one unsourced
statistic**. `--brief` skips the research step, so the writer received an argument with no
evidence and supplied its own: a chart with four invented percentages, prose describing that
chart as showing something it does not plot, a named real executive given a motive his
company's annual report cannot support, and three references with no URLs. The deterministic
evaluator scored it 76 and the publication validator passed it.

The generator was not at fault. **An artifact with no evidence is an argument, not a research
brief**, and the pipeline cannot tell the difference. Fixing it downstream means catching
fabrication after it happens; fixing it here means it never happens.

The five constraints below are the `blog-post-review` gates (G1–G5, `skills/blog-post-review/`)
stated as authoring instructions. An artifact that satisfies them arrives at the review stage
already able to pass it.

---

## The prompt

> This artifact is going to become the research brief for a published article, and every
> claim in it will be checked against its source by an adversarial reviewer. Right now it
> cannot survive that, because it carries no citations — so anything downstream that needs
> evidence will invent it.
>
> Re-emit this artifact with sources attached. **Keep the analysis as it is** — the structure,
> the argument, the loops, the conclusions. I am not asking you to re-research the topic or
> change your mind about it. I am asking you to show your evidence, and to be explicit about
> where there isn't any.
>
> For every claim that carries weight, attach a **resolvable URL** — a primary source where
> one exists (the study, the report, the filing, the docs), not a secondary write-up about it.
> Then hold each one to these five rules:
>
> 1. **It resolves.** Every statistic, percentage, dollar figure, dated event and named study
>    links to a document I can open. A citation I have to go and find is not a citation.
> 2. **It says what I say it says.** The source must support *that specific claim*, at that
>    scope and sample. If a figure comes with an offsetting clause — "X rose 25%, but Y fell"
>    — quote both halves. Dropping the second half is the single most common way a true
>    sentence becomes a false one.
> 3. **The arithmetic is shown.** Any calculation, ratio, extrapolation or cost model: show
>    the working and state the denominator. Don't assert that it checks out.
> 4. **Nothing is invented.** No quotes, people, companies, studies or metrics that cannot be
>    distinguished from real ones. **If you cannot source something, do not drop it and do not
>    soften it into a vaguer version of itself** — keep the claim and mark it unsourced. That
>    is far more useful to me than a confident sentence I have to catch later.
> 5. **It is still current.** For anything from a publication that re-runs — annual reports,
>    industry surveys, vendor benchmarks, DORA, Stack Overflow — check whether a later edition
>    revises, reverses or narrows the finding, and cite the latest. Say so if it changed.
>
> Two things I need in addition to the prose:
>
> **A short table of real, sourced figures suitable for one chart** — three to six rows,
> each with its number, what it measures, and its source URL. If no such data exists for this
> topic, **say that plainly instead of assembling something plausible.** An honest "there is no
> quantitative dataset behind this argument" is a useful finding; a fabricated chart is the
> worst thing you can hand me.
>
> **A final section titled "Unsourced — do not publish as fact"**, listing every claim you
> could not attach a source to, including any that are load-bearing. Do not quietly delete
> them; I would rather know the argument rests on them.
>
> Output the whole thing as a single HTML artifact, as before.

---

## What to do with the result

```bash
# 1. Save the new artifact (samples are gitignored — local only)
mv ~/Downloads/<file>.html docs/research/samples/<topic>.html

# 2. Convert
python scripts/html_to_brief.py docs/research/samples/<topic>.html --slug <slug> --force

# 3. Check it actually has sources now — this is the whole point
grep -c '](http' docs/research/<slug>.md      # expect > 0

# 4. Move the "Unsourced" section under the brief's own `## Refuted / unverified`
#    heading. load_brief_file strips everything from that heading to EOF, so those
#    claims are excluded by construction rather than by the writer's discretion.
#    The converter demotes source headings by one level, so the artifact's own
#    heading will NOT be stripped automatically — this move is manual and deliberate.

# 5. Generate
python -m src.agent_sdk.pipeline "<topic>" --brief docs/research/<slug>.md
```

Then deploy to review — never straight to `_posts/` — per the publishing workflow in
`CLAUDE.md`.
