#!/usr/bin/env python3
"""Finalise the art the owner made, and fold it into the article (B-042).

Run after drawing the hero and (optionally) editing the chart spec::

    make art SLUG=<slug>

Three steps, each a no-op when its input is absent:

1. **Render the chart** from ``output/charts/<slug>.spec.json``. A PNG already
   at ``output/charts/<slug>.png`` **wins and is never overwritten** — that is
   the fully-manual route, and silently replacing hand-made art with a rendered
   spec would be exactly the automation this item exists to remove.
2. **Embed the chart** in the article, before ``## References``. An embed is a
   claim that a figure exists, so it is written here — after the PNG does —
   rather than by Stage 4, which used to insert it unconditionally.
3. **Link the hero** into ``image:``, using the SVG's own ``<desc>`` as alt text.

Deliberately *not* done here: nothing is generated, drawn, or invented. This
script only arranges files the owner has already made.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from src.agent_sdk._shared import _auto_embed_chart
from src.agent_sdk.chart_renderer import ChartRenderError, render_chart
from src.agent_sdk.hero_svg import HERO_IMAGES_DIR
from src.agent_sdk.pipeline import _link_hero_asset

logger = logging.getLogger(__name__)

POSTS_DIR = Path("output/posts")
CHARTS_DIR = Path("output/charts")

#: Values the proposal leaves empty for the owner to supply. Rendering with them
#: still empty would produce a chart with no title and unlabelled bars, which is
#: worse than no chart — so the renderer's own validation is allowed to refuse,
#: and this message explains why rather than surfacing a bare stack trace.
_UNFRAMED_HINT = (
    "The chart spec still has the placeholders the proposal left for you: a "
    "`title`, and a `metric` label on every row you keep. Fill those in (and "
    "delete the rows you do not want) — the figures are already sourced from "
    "the brief; the framing is the part only you can supply."
)


def _render_chart_if_needed(slug: str) -> Path | None:
    """Render the spec unless a PNG is already there. Returns the PNG, if any."""
    png = CHARTS_DIR / f"{slug}.png"
    if png.is_file():
        print(f"  Chart: using the existing PNG at {png} (not overwritten)")
        return png

    spec_path = CHARTS_DIR / f"{slug}.spec.json"
    if not spec_path.is_file():
        print("  Chart: none — no spec and no PNG, so the article ships without one")
        return None

    try:
        spec = json.loads(spec_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  Chart: spec at {spec_path} is unreadable — {exc}", file=sys.stderr)
        return None

    try:
        render_chart(spec, png)
    except ChartRenderError as exc:
        print(f"  Chart: spec rejected — {exc}", file=sys.stderr)
        print(f"  {_UNFRAMED_HINT}", file=sys.stderr)
        return None
    print(f"  Chart: rendered {png}")
    return png


def finalise(slug: str) -> int:
    """Fold the owner's art into the article. Returns a process exit code."""
    article_path = POSTS_DIR / f"{slug}.md"
    if not article_path.is_file():
        print(f"No article at {article_path}", file=sys.stderr)
        return 1

    article = article_path.read_text()
    png = _render_chart_if_needed(slug)
    if png is not None:
        article = _auto_embed_chart(article)

    before = article
    article = _link_hero_asset(article, slug, images_dir=HERO_IMAGES_DIR)
    if article == before:
        print(
            f"  Hero: none found at {HERO_IMAGES_DIR}/{slug}-hero.svg — "
            "`image:` left absent, and deploy will refuse until it exists",
            file=sys.stderr,
        )
    else:
        print(f"  Hero: linked {HERO_IMAGES_DIR}/{slug}-hero.*")

    article_path.write_text(article)
    print(f"\nUpdated {article_path}")
    print(
        f"Next: python -m scripts.deploy_to_blog --article {article_path} --mode review"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--slug", required=True, help="Article slug (no extension)")
    args = parser.parse_args(argv)
    return finalise(args.slug)


if __name__ == "__main__":
    raise SystemExit(main())
