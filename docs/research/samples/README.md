# Sample HTML artifacts — drop them here

**This directory is the input side of B-038.** `scripts/html_to_brief.py` converts a Claude
HTML artifact into a markdown research brief at `docs/research/<slug>.md`; the files here are
the *real examples* its tests are built against.

## What to drop

Any HTML artifact produced at the end of a back-and-forth research conversation with Claude —
the thing you would otherwise transcribe by hand. Save it as `*.html` with a name that says
what the conversation was about:

```
docs/research/samples/ai-code-review-throughput.html
docs/research/samples/platform-eng-adoption.html
```

Nothing else needs to change. The converter and its tests discover whatever is here.

## Why real samples, not invented ones

The tests can run on synthetic fixtures, and v1 ships with three (headings-and-prose,
blockquote-heavy, table-bearing) precisely so the tool is not blocked on a sample. But a
synthetic fixture only proves the converter handles **HTML I imagined**.

This repo has been caught three times asserting from a plausible reading instead of measuring
— see the "defect that was never there" section in `skills/defect-prevention/SKILL.md`. The
one Claude HTML artifact in the repo,
`docs/reviews/review-queue-throughput-tax-42d2fbb4.html`, contains **zero `<a href>`**. Any
design that had assumed "sources will be links" would have been wrong on the only real
evidence available. One genuine sample is worth more than three invented ones.

## What happens to them

They are fixtures, not content. They are read by `tests/test_html_to_brief.py`, never
published, and never fed to the pipeline directly — the pipeline consumes the *converted*
brief at `docs/research/<slug>.md`.

If a sample contains anything you would not want in a public repo, do not commit it: put it
outside the repo and pass the path directly. The converter takes a path argument and does not
care where the file lives.
