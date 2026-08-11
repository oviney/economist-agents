#!/usr/bin/env python3
"""Convert a Claude HTML artifact into a markdown research brief (B-038).

The owner researches by holding a back-and-forth conversation with Claude and
finalising it as an HTML artifact.  The pipeline cannot read HTML: ``--brief``
expects markdown, and the only route today is manual transcription.

Usage::

    python scripts/html_to_brief.py ~/Downloads/conversation.html --slug ai-code-review
    # writes docs/research/ai-code-review.md

    IS_SANDBOX=1 python -m src.agent_sdk.pipeline "<topic>" \
        --brief docs/research/ai-code-review.md

**This is transport, not judgment.**  ``load_brief_file``
(``src/agent_sdk/pipeline.py``) does exactly two things — read the file and strip
``## Refuted…`` — and ``stage3_runner.py`` hands the result to the writer
verbatim.  There is no schema.  So the job is faithful conversion: structure to
structure, with quotes, tables and URLs preserved byte-for-byte.

There is deliberately **no LLM in the middle**.  ADR-0018 measured what a
paraphrase step costs — fidelity defects (a statistic quoted with its offsetting
clause deleted, a conclusion imported into a paper that does not report it)
survived four gates and produced a 51/100 BLOCK on an article the deterministic
evaluator passed at 88%.  A paraphrase sits exactly where that damage starts.
The judging already happened in the conversation.

Deterministic, via bs4 (already installed): no new dependency, no key, no network.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.element import (
    CData,
    Comment,
    Declaration,
    Doctype,
    NavigableString,
    PageElement,
    ProcessingInstruction,
    Tag,
)

logger = logging.getLogger(__name__)

#: The section ``load_brief_file`` strips.  Emitted on every brief, always empty and
#: always last, so moving a paragraph into it is a one-line edit whose effect is
#: guaranteed by the loader rather than by the writer's discretion.
REFUTED_HEADING = "## Refuted / unverified"

_REFUTED_NOTE = (
    "Move any claim the writer must NOT use into this section. `load_brief_file` "
    "drops everything from this heading to the end of the file, so anything below "
    "is excluded by construction. This note goes with it."
)

#: Styling and navigation are not content.  Claude artifacts carry all of these.
CHROME_TAGS = ("script", "style", "nav", "footer", "head", "noscript", "template")

#: Anything whose presence means "start a new block".  Used both to dispatch and to
#: decide whether a container should be recursed into or flattened into a paragraph.
_BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "caption",
        "dd",
        "details",
        "dialog",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hgroup",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "svg",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
)

_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})

#: Comments, doctypes and processing instructions are markup, not text.
_NON_CONTENT_STRINGS = (Comment, Doctype, Declaration, ProcessingInstruction, CData)

DEFAULT_OUT_DIR = Path("docs/research")

_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class BriefConversionError(RuntimeError):
    """The input yielded no content — better a clear error than a hollow brief."""


# ═══════════════════════════════════════════════════════════════════════════
# Inline conversion — runs of text inside a block
# ═══════════════════════════════════════════════════════════════════════════


#: Inline elements that survive as markdown emphasis.  A dispatch table rather than a
#: branch ladder, so adding a mapping is data, not control flow.
_INLINE_WRAPPERS = {
    "strong": "**{}**",
    "b": "**{}**",
    "em": "*{}*",
    "i": "*{}*",
    "code": "`{}`",
    "q": '"{}"',
}


def _inline(node: PageElement) -> str:
    """Render one inline node (or the inline projection of a block) as markdown."""
    if isinstance(node, _NON_CONTENT_STRINGS):
        return ""
    if isinstance(node, NavigableString):
        return re.sub(r"\s+", " ", str(node))
    if isinstance(node, Tag):
        return _inline_tag(node)
    return ""


def _inline_image(tag: Tag) -> str:
    """``<img>`` — keep the src, or the alt text if there is no src."""
    src = str(tag.get("src") or "")
    alt = str(tag.get("alt") or "")
    return f"![{alt}]({src})" if src else alt


def _inline_link(tag: Tag, inner: str) -> str:
    """``<a href>`` — the URL is copied verbatim; ADR-0018 G5 depends on real URLs."""
    href = tag.get("href")
    return f"[{inner.strip()}]({href})" if href and inner.strip() else inner


def _inline_tag(tag: Tag) -> str:
    """Render an inline tag.  Unmapped tags fall through to their own text."""
    name = tag.name
    if name == "br":
        return "\n"
    if name == "img":
        return _inline_image(tag)

    inner = _inline_children(tag)

    if name == "a":
        return _inline_link(tag, inner)
    wrapper = _INLINE_WRAPPERS.get(name)
    if wrapper and inner.strip():
        return wrapper.format(inner.strip())
    if name in _BLOCK_TAGS:
        # A block flattened into inline context: keep a separator so words from two
        # paragraphs never glue together.
        return f"{inner} "
    return inner


def _inline_children(node: Tag) -> str:
    """Concatenate the inline rendering of a tag's children."""
    return "".join(_inline(child) for child in node.children)


def _tidy(text: str) -> str:
    """Collapse horizontal whitespace, keeping ``<br>``-derived line breaks."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def _one_line(text: str) -> str:
    """As ``_tidy``, but flattened — for headings and table cells."""
    return _tidy(text).replace("\n", " ").strip()


# ═══════════════════════════════════════════════════════════════════════════
# Block conversion
# ═══════════════════════════════════════════════════════════════════════════


def _is_block(node: PageElement) -> bool:
    """True when the node must start its own markdown block."""
    if not isinstance(node, Tag):
        return False
    return node.name in _BLOCK_TAGS or node.find(list(_BLOCK_TAGS)) is not None


def _blocks(root: Tag) -> Iterator[str]:
    """Walk a container in document order, yielding markdown blocks.

    Consecutive inline siblings are gathered into a single paragraph so a sentence
    split across ``<span>``s does not become three paragraphs.  Unrecognised
    containers are recursed into and unrecognised inline elements are rendered as
    their text: nothing is discarded.
    """
    pending: list[PageElement] = []

    def flush() -> Iterator[str]:
        if pending:
            text = _tidy("".join(_inline(node) for node in pending))
            pending.clear()
            if text:
                yield text

    for child in root.children:
        if not _is_block(child):
            pending.append(child)
            continue
        yield from flush()
        assert isinstance(child, Tag)  # _is_block guarantees it
        yield from _convert_block(child)

    yield from flush()


def _render_heading(tag: Tag) -> str:
    """Demote by one level so the brief's own ``#`` title stays top-level."""
    text = _one_line(_inline_children(tag))
    return f"{'#' * min(int(tag.name[1]) + 1, 6)} {text}" if text else ""


def _convert_block(tag: Tag) -> Iterator[str]:
    """Render one block-level element, recursing into containers we do not map."""
    renderer = _BLOCK_RENDERERS.get(tag.name)
    if renderer is None:
        yield from _blocks(tag)
        return
    rendered = renderer(tag)
    if rendered.strip():
        yield rendered


def _find_tags(
    tag: Tag, names: str | list[str], *, recursive: bool = True
) -> list[Tag]:
    """``find_all`` narrowed to real tags — bs4's return type is wider than we use."""
    return [
        child
        for child in tag.find_all(names, recursive=recursive)
        if isinstance(child, Tag)
    ]


def _render_list(tag: Tag, *, ordered: bool, depth: int = 0) -> str:
    """Render ``<ul>``/``<ol>``, preserving nesting as two-space indentation."""
    lines: list[str] = []
    for index, item in enumerate(_find_tags(tag, "li", recursive=False), start=1):
        nested = _find_tags(item, ["ul", "ol"], recursive=False)
        for sublist in nested:
            sublist.extract()

        marker = f"{index}." if ordered else "-"
        text = _one_line(_inline_children(item))
        indent = "  " * depth
        if text:
            lines.append(f"{indent}{marker} {text}")
        for sublist in nested:
            rendered = _render_list(
                sublist, ordered=sublist.name == "ol", depth=depth + 1
            )
            if rendered:
                lines.append(rendered)
    return "\n".join(lines)


def _render_blockquote(tag: Tag) -> str:
    """Render ``<blockquote>``.  These are usually the load-bearing quotes."""
    inner = "\n\n".join(block for block in _blocks(tag) if block)
    if not inner.strip():
        return ""
    return "\n".join(f"> {line}" if line.strip() else ">" for line in inner.split("\n"))


def _render_pre(tag: Tag) -> str:
    """Render ``<pre>`` as a fenced block, whitespace untouched."""
    code = tag.find("code")
    text = (code if isinstance(code, Tag) else tag).get_text().strip("\n")
    if not text.strip():
        return ""
    return f"```\n{text}\n```"


def _render_table(tag: Tag) -> str:
    """Render a table as GFM.  Dropping one would lose the comparison it carries."""
    rows: list[list[str]] = []
    header: list[str] | None = None

    for tr in _find_tags(tag, "tr"):
        cell_tags = _find_tags(tr, ["th", "td"], recursive=False)
        cells = [
            _one_line(_inline_children(cell)).replace("|", r"\|") for cell in cell_tags
        ]
        if not cells:
            continue
        is_header_row = all(cell.name == "th" for cell in cell_tags)
        if header is None and is_header_row and not rows:
            header = cells
        else:
            rows.append(cells)

    if header is None and not rows:
        return ""

    width = max(len(row) for row in ([header] if header else []) + rows)
    # GFM requires a header row; an empty one invents no content.
    header = (header or [""] * width) + [""] * (width - len(header or []))

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    lines += ["| " + " | ".join(row + [""] * (width - len(row))) + " |" for row in rows]
    return "\n".join(lines)


def _render_svg(tag: Tag) -> str:
    """Keep an inline SVG's labels, and say plainly that they are diagram labels.

    Claude artifacts draw diagrams as inline SVG.  Flattened into prose the labels read
    as a sentence ("Schedule Pressure Feature Velocity + - DELAY B1"), which is the
    fidelity hazard ADR-0018 is about: the writer would treat a diagram key as a claim.
    Labelling costs nothing and invents nothing.
    """
    labels = [_one_line(node.get_text(" ")) for node in _find_tags(tag, "text")]
    loose = [
        _one_line(str(string))
        for string in tag.strings
        if isinstance(string, PageElement)
        and not isinstance(string, _NON_CONTENT_STRINGS)
        and string.find_parent("text") is None
    ]
    parts = [part for part in labels + loose if part]
    if not parts:
        return ""
    return "*Diagram (inline SVG in the source) — labels only:* " + " · ".join(parts)


#: Block dispatch.  Anything not here is a container we recurse into, so an unmapped
#: element loses its structure but never its content.
_BLOCK_RENDERERS: dict[str, Callable[[Tag], str]] = {
    **dict.fromkeys(_HEADING_TAGS, _render_heading),
    "p": lambda tag: _tidy(_inline_children(tag)),
    "ul": lambda tag: _render_list(tag, ordered=False),
    "ol": lambda tag: _render_list(tag, ordered=True),
    "blockquote": _render_blockquote,
    "table": _render_table,
    "pre": _render_pre,
    "svg": _render_svg,
    "hr": lambda _tag: "---",
}


# ═══════════════════════════════════════════════════════════════════════════
# Document assembly
# ═══════════════════════════════════════════════════════════════════════════


def _strip_chrome(soup: BeautifulSoup) -> Counter[str]:
    """Remove styling and navigation.  Returns what was removed, so it can be reported."""
    dropped: Counter[str] = Counter()
    for tag in _find_tags(soup, list(CHROME_TAGS)):
        dropped[str(tag.name)] += 1
        tag.decompose()
    return dropped


def _render(root: BeautifulSoup) -> str:
    """Join the document's blocks into markdown."""
    return "\n\n".join(block for block in _blocks(root) if block.strip())


def html_to_markdown(html: str) -> str:
    """Convert HTML to markdown, chrome removed.  No title promotion, no scaffolding."""
    soup = BeautifulSoup(html, "html.parser")
    _strip_chrome(soup)
    return _render(soup)


def _extract_title(soup: BeautifulSoup, fallback: str) -> str:
    """Take the document title, promoting the first ``<h1>`` out of the body.

    Promotion, not duplication: the ``<h1>`` becomes the brief's ``#`` heading and is
    removed from the body so it is not rendered twice.
    """
    h1 = soup.find("h1")
    if isinstance(h1, Tag):
        text = _one_line(_inline_children(h1))
        h1.decompose()
        if text:
            return text
    title = soup.find("title")
    if isinstance(title, Tag) and title.get_text().strip():
        return _one_line(title.get_text())
    return fallback


def build_brief(html: str, *, source_name: str) -> str:
    """Convert a Claude HTML artifact into a complete markdown research brief.

    Raises ``BriefConversionError`` when the input yields no content — a hollow
    brief that silently produces a hollow article is the worse outcome.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup, fallback=Path(source_name).stem)
    _strip_chrome(soup)
    body = _render(soup)

    if not body.strip():
        raise BriefConversionError(
            f"{source_name}: no content found after removing "
            f"{'/'.join(CHROME_TAGS)} — refusing to write a hollow brief"
        )

    return "\n".join(
        [
            f"# {title}",
            "",
            f"*Converted from `{source_name}` by `scripts/html_to_brief.py`. "
            "Reorder or delete freely before use — but nothing here needs re-typing.*",
            "",
            body,
            "",
            REFUTED_HEADING,
            "",
            _REFUTED_NOTE,
            "",
        ]
    )


def find_dropped_words(html: str, markdown: str) -> Counter[str]:
    """Words present in the source's content tree but missing from the markdown.

    The converter's one hard promise is that it never silently drops content, so it
    checks itself at runtime rather than only in the test suite.
    """
    soup = BeautifulSoup(html, "html.parser")
    _strip_chrome(soup)
    source = Counter(re.findall(r"[0-9A-Za-z]+", soup.get_text(" ")))
    return source - Counter(re.findall(r"[0-9A-Za-z]+", markdown))


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="html_to_brief",
        description="Convert a Claude HTML artifact into a markdown research brief.",
    )
    parser.add_argument("html", help="path to the HTML artifact")
    parser.add_argument(
        "--slug", required=True, help="output filename stem: <out-dir>/<slug>.md"
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help=f"directory for the brief (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing brief"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point.  Returns 0 on success, non-zero on any refusal to write."""
    args = _build_parser().parse_args(argv)

    if not _SLUG_RE.match(args.slug) or ".." in args.slug:
        logger.error(
            "invalid --slug %r: use letters, digits, '.', '_' and '-'", args.slug
        )
        return 2

    source = Path(args.html)
    if not source.is_file():
        logger.error("no such file: %s", source)
        return 2

    destination = Path(args.out_dir) / f"{args.slug}.md"
    if destination.exists() and not args.force:
        logger.error("%s already exists — pass --force to overwrite", destination)
        return 1

    html = source.read_text(errors="replace")
    try:
        brief = build_brief(html, source_name=source.name)
    except BriefConversionError as exc:
        logger.error("%s", exc)
        return 1

    dropped = find_dropped_words(html, brief)
    if dropped:  # pragma: no cover - the converter is built so this stays empty
        logger.warning(
            "%d word(s) did not survive conversion: %s",
            sum(dropped.values()),
            ", ".join(sorted(dropped)[:20]),
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(brief)
    logger.info("wrote %s (%d chars)", destination, len(brief))
    logger.info(
        "review it, move anything unproven under '%s', then: "
        'python -m src.agent_sdk.pipeline "<topic>" --brief %s',
        REFUTED_HEADING,
        destination,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
