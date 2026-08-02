"""The review packet — what a finished run hands to the owner (B-042).

The pipeline produces everything a *machine* can produce and stops. Every image
the blog publishes is the owner's, because fully automated visual generation has
not produced outcomes he will stand behind; the fabricated chart that gave B-042
its name is the measured instance.

So a run ends with a packet rather than with finished art: the gate results, the
permanent slug, the hero brief, the chart figures found in the research (or an
honest statement that there were none), and the exact commands that follow.

This is **not** the #403 handshake ADR-0016 deleted. That paused Stage 3, wrote
resume state, and exited 10 before Stage 4 ever ran, leaving an unvalidated
half-article. This runs the whole pipeline, passes every gate, exits 0, and then
tells the owner what is left. One path, no resume state, no reserved exit codes.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)

#: Where a finished packet is written, alongside the article it describes.
PACKETS_DIR = Path("output/posts")

#: How long the notifier may block. A banner is a courtesy; a run that has
#: already succeeded must never hang waiting for one.
_NOTIFY_TIMEOUT_S = 5.0


class _PacketSource(Protocol):
    """The subset of ``PipelineResult`` a packet reads.

    A Protocol rather than the concrete class so tests can pass a small stub,
    and so this module does not import the pipeline it is called from.
    """

    topic: str
    slug: str
    image_prompt: str
    chart_proposal: dict[str, Any] | None
    chart_spec_path: Path | None
    editorial_score: int
    gates_passed: int
    publication_validator_passed: bool
    publication_validator_issues: list[dict[str, str]]
    total_cost_usd: float
    article_chars: int


def _format_verdict(result: _PacketSource) -> str:
    lines = [
        "## 1. Verdict",
        "",
        f"- Publication validator: "
        f"{'PASSED' if result.publication_validator_passed else 'FAILED'}",
        f"- Editorial score: {result.editorial_score}",
        f"- Gates passed: {result.gates_passed}",
        f"- Cost: ${result.total_cost_usd:.4f}",
        f"- Length: {result.article_chars} chars",
    ]
    if result.publication_validator_issues:
        lines += ["", "Outstanding issues:"]
        lines += [
            f"  - [{i.get('severity')}] {i.get('check')}: {i.get('message')}"
            for i in result.publication_validator_issues
        ]
    lines += [
        "",
        "Art is **not** part of this verdict. The validator no longer rules on "
        "whether an article needs a chart (B-042), and hero presence is checked "
        "at the deploy boundary (ADR-0017) — so a PASS here means *the prose is "
        "ready*, not that the post is complete.",
    ]
    return "\n".join(lines)


def _format_hero(result: _PacketSource) -> str:
    target = f"output/posts/images/{result.slug}-hero.svg"
    lines = [
        "## 2. Hero image — yours to draw",
        "",
        f"Drop it at `{target}`.",
        "",
        "**SVG is preferred.** The blog's `responsive-image.html` rewrites "
        "`.png` → `.webp`, so a PNG hero needs a `.webp` sibling beside it; an "
        "SVG takes the plain `<img>` branch and needs none.",
        "",
        f"The brief is also at `output/posts/{result.slug}.image_prompt.md`, and "
        "inline in the article as a `<!-- HERO IMAGE` comment. **The deploy step "
        "refuses an article still carrying that comment** (BUG-065), so replacing "
        "it is part of the job, not a tidy-up.",
    ]
    if result.image_prompt:
        lines += ["", "```text", result.image_prompt.strip(), "```"]
    else:
        lines += [
            "",
            "> No brief was synthesised — the writer emitted no `image_alt`. "
            "Draw from the article's thesis.",
        ]
    return "\n".join(lines)


def _format_chart(result: _PacketSource) -> str:
    lines = ["## 3. Chart — only if the research supports one", ""]

    if result.chart_proposal is None:
        lines += [
            "**No chart proposed. The research brief contains no numeric claim.**",
            "",
            "This is a first-class outcome, not a gap: nothing here needs "
            "charting, and the article passes without one. The old gate would "
            "have required a chart anyway, which is how four percentages came to "
            "be invented.",
            "",
            "What was searched: every number in the brief carrying a unit "
            "(`%`, `per cent`, `billion`, `million`, `thousand`, `trillion`, "
            "`fold`, `times`, `x`). Bare counts and years are deliberately not "
            'proposed, so a figure written as "1,200 engineers" would not '
            "appear above — if you know of one, it is yours to add. Neither is "
            'either end of a range: "15–20%" is not a measurement, and a row '
            "reading `20 %` would read as one.",
        ]
        return "\n".join(lines)

    rows = result.chart_proposal["data"]
    spec_path = result.chart_spec_path or f"output/charts/{result.slug}.spec.json"
    lines += [
        f"**{len(rows)} figure(s) extracted from the brief.** Every value below "
        "appears in the research verbatim — none was generated.",
        "",
        f"Edit `{spec_path}`, then run `make art SLUG={result.slug}`.",
        "",
        "You need to supply: the `title`, and a `metric` label per row. They are "
        "empty by design — framing is the editorial judgment, and a plausible "
        "machine-written label is what made the fabricated chart read as real "
        "data. Delete the rows you do not want: these are candidates, not a "
        "chart. One axis, one measure — the renderer rejects a spec whose values "
        "span too many orders of magnitude (B-014).",
        "",
        "Two kinds of figure are deliberately left out, so you know to add them "
        'yourself if you want them: bare counts and years ("1,200 engineers"), '
        'and either end of a range ("15–20%" is not a measurement).',
        "",
        "| value | unit | found in the brief as |",
        "|---|---|---|",
    ]
    lines += [
        f"| {row['value']} | {row['unit']} | "
        f"{row['source'].removeprefix('brief: ').strip()} |"
        for row in rows
    ]
    return "\n".join(lines)


def _format_next(result: _PacketSource) -> str:
    return "\n".join(
        [
            "## 4. What happens next",
            "",
            "```bash",
            "# 1. Draw the hero (and the chart, if you want one) as above.",
            "# 2. Finalise the art — renders the chart spec if present, embeds",
            "#    it, and points `image:` at your hero:",
            f"make art SLUG={result.slug}",
            "",
            "# 3. Deploy to the unlisted review URL and read the live page:",
            "python -m scripts.deploy_to_blog \\",
            f"    --article output/posts/{result.slug}.md --mode review",
            "",
            "# 4. Only after you have read it:",
            f"make publish SLUG={result.slug}",
            "```",
        ]
    )


def build_packet(result: _PacketSource, article_path: Path) -> str:
    """Render the review packet for a finished run."""
    header = "\n".join(
        [
            f"# Review packet — {result.slug}",
            "",
            f"**Topic:** {result.topic}",
            f"**Article:** `{article_path}`",
            "",
            f"**The slug `{result.slug}` becomes a permanent URL.** The blog has "
            "no `jekyll-redirect-from`, so renaming a published post 404s the "
            "original. Change it now or not at all.",
        ]
    )
    return (
        "\n\n".join(
            [
                header,
                _format_verdict(result),
                _format_hero(result),
                _format_chart(result),
                _format_next(result),
            ]
        )
        + "\n"
    )


def write_packet(result: _PacketSource, article_path: Path) -> Path:
    """Write the packet beside the article and return its path."""
    PACKETS_DIR.mkdir(parents=True, exist_ok=True)
    path = PACKETS_DIR / f"{result.slug}.review.md"
    path.write_text(build_packet(result, article_path))
    logger.info("Wrote review packet: %s", path)
    return path


def notify(title: str, message: str) -> bool:
    """Post a desktop banner. Returns whether one was actually shown.

    Never raises and never blocks for long. A notification is a courtesy at the
    end of a run that has already succeeded; if it fails — not macOS, no
    ``osascript``, a headless session, a timeout — the packet on disk and the
    terminal summary still carry every fact, so the right behaviour is to
    degrade quietly rather than to fail a good run over a banner.
    """
    osascript = shutil.which("osascript")
    if osascript is None:
        logger.debug("No osascript on PATH — skipping desktop notification")
        return False

    # Quotes are the only AppleScript-string metacharacter that matters here;
    # both values are ours, but escape anyway so a topic containing a quote
    # cannot produce a syntax error that prints a scary traceback.
    safe_title = title.replace('"', "'")
    safe_message = message.replace('"', "'")
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    try:
        subprocess.run(  # noqa: S603 - fixed executable, no shell, escaped args
            [osascript, "-e", script],
            check=True,
            capture_output=True,
            timeout=_NOTIFY_TIMEOUT_S,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.debug("Desktop notification failed (non-fatal): %s", exc)
        return False
    return True
