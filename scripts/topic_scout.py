#!/usr/bin/env python3
"""
Topic Scout Agent

Monitors the quality engineering landscape to identify high-value article topics.
Runs weekly (or on-demand) to populate the content queue with timely, relevant topics.

Sources analyzed:
- Industry news and announcements
- Conference talk trends
- Tool/framework releases
- Research papers and reports
- Community discussions (Reddit, HN, dev.to)
- Competitor content gaps

Output: Ranked list of topics with data availability scores
"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent_loader import load_scout_prompts as _load_scout_prompts  # noqa: E402

from src.tools.topic_deduplicator import TopicDeduplicator  # noqa: E402

logger = logging.getLogger(__name__)

# Trend grounding: live web search replaces plain LLM trend research.
from topic_trend_grounding import build_grounded_trend_context

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Theme keyword map for diversity classification.
# Keys are canonical theme labels used by check_topic_diversity().
# ---------------------------------------------------------------------------
THEME_KEYWORDS: dict[str, list[str]] = {
    "ai_testing": [
        "ai",
        "ml",
        "machine learning",
        "test generation",
        "copilot",
        "llm",
        "generative",
        "ai-powered",
        "ai testing",
    ],
    "security": [
        "security",
        "vulnerability",
        "devsecops",
        "sast",
        "dast",
        "owasp",
        "penetration",
        "supply-chain",
        "exploit",
        "cve",
    ],
    "devops": [
        "devops",
        "ci/cd",
        "cicd",
        "deployment",
        "pipeline",
        "gitops",
        "docker",
        "kubernetes",
        "release engineering",
        "continuous delivery",
    ],
    "platform_engineering": [
        "platform engineering",
        "internal developer platform",
        "idp",
        "backstage",
        "paved path",
        "golden path",
        "developer portal",
    ],
    "observability": [
        "observability",
        "opentelemetry",
        "distributed tracing",
        "tracing",
        "logging",
        "metrics",
        "slo",
        "sla",
        "alerting",
        "monitoring",
    ],
    "developer_experience": [
        "developer experience",
        "dx",
        "developer productivity",
        "onboarding",
        "cognitive load",
        "inner loop",
        "developer satisfaction",
        "devex",
    ],
    "software_architecture": [
        "architecture",
        "microservices",
        "monolith",
        "design pattern",
        "technical debt",
        "refactoring",
        "modular",
        "domain-driven",
    ],
    "quality_economics": [
        "roi",
        "cost",
        "economics",
        "budget",
        "maintenance cost",
        "investment",
        "total cost",
        "productivity",
        "velocity",
    ],
    "test_automation": [
        "test automation",
        "flaky test",
        "test suite",
        "playwright",
        "cypress",
        "selenium",
        "shift-left",
        "shift-right",
        "e2e",
        "unit test",
    ],
}

# Content Intelligence: real blog performance data from GA4 ETL (ADR-0007)
from content_intelligence import get_performance_context  # noqa: E402

# Import unified LLM client
from llm_client import call_llm, create_llm_client  # noqa: E402

_scout_prompts = _load_scout_prompts()
SCOUT_AGENT_PROMPT = _scout_prompts["scout"]
TREND_RESEARCH_PROMPT = _scout_prompts["trend"]


def classify_topic_theme(topic: dict) -> str:
    """Classify a topic into its primary theme using keyword matching.

    If the topic already has a ``theme`` field (set by the LLM), that value is
    returned directly so the model's own categorisation is honoured.  Otherwise,
    keyword matching across the topic's text fields is used as a fallback.

    Args:
        topic: Topic dict as returned by ``scout_topics()``.

    Returns:
        Theme string (e.g. ``"security"``, ``"ai_testing"``).
        Falls back to ``"other"`` when no keywords match.
    """
    # Prefer the LLM-supplied theme field when present.
    if topic.get("theme"):
        return str(topic["theme"]).strip().lower()

    # Build a combined text blob from all descriptive fields.
    text = " ".join(
        [
            topic.get("topic", ""),
            topic.get("hook", ""),
            topic.get("thesis", ""),
            topic.get("contrarian_angle", ""),
            topic.get("talking_points", ""),
        ]
    ).lower()

    theme_scores: dict[str, int] = {}
    for theme, keywords in THEME_KEYWORDS.items():
        score = sum(
            1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text)
        )
        if score > 0:
            theme_scores[theme] = score

    if not theme_scores:
        return "other"

    return max(theme_scores, key=lambda k: theme_scores[k])


def check_topic_diversity(topics: list) -> tuple[bool, str]:
    """Check whether generated topics are sufficiently diverse.

    A set of topics is considered diverse when no single theme accounts for
    more than 40 % of the topics.

    Args:
        topics: List of topic dicts from ``scout_topics()``.

    Returns:
        A tuple ``(is_diverse, dominant_theme)`` where:
        - ``is_diverse`` is ``True`` when the threshold is not exceeded.
        - ``dominant_theme`` is the theme that appears most often (empty string
          when *topics* is empty).
    """
    if not topics:
        return True, ""

    theme_counts: dict[str, int] = {}
    for topic in topics:
        theme = classify_topic_theme(topic)
        theme_counts[theme] = theme_counts.get(theme, 0) + 1

    dominant_theme = max(theme_counts, key=lambda k: theme_counts[k])
    dominant_ratio = theme_counts[dominant_theme] / len(topics)

    return dominant_ratio <= 0.4, dominant_theme


def _parse_topics_json(response_text: str, label: str = "") -> list | None:
    """Extract and parse a JSON array from an LLM response string.

    Args:
        response_text: Raw text returned by the LLM.
        label: Optional label used in printed warning messages (e.g. ``"on retry"``).

    Returns:
        Parsed list of topic dicts, or ``None`` when parsing fails (the caller
        should treat ``None`` as an empty result and return ``[]``).
    """
    suffix = f" {label}" if label else ""
    try:
        start = response_text.find("[")
        end = response_text.rfind("]") + 1
        if start != -1 and end > start:
            return json.loads(response_text[start:end])
        print(f"   ⚠ Could not parse topic list{suffix}")
        return None
    except json.JSONDecodeError as exc:
        print(f"   ⚠ JSON parse error{suffix}: {exc}")
        return None


def create_client():
    """Create unified LLM client (supports Anthropic Claude and OpenAI)"""
    return create_llm_client()


def scout_topics(
    client,
    focus_area: str = None,
    *,
    allow_empty_archive: bool = False,
) -> list:
    """
    Scout for high-value topics.

    Args:
        focus_area: Optional filter (e.g., "test automation", "AI", "performance")
        allow_empty_archive: If False (default), raise RuntimeError when the
            `published_articles` ChromaDB collection is missing or empty. This
            fail-closed behavior prevents publishing dedup-blind (issue #237).
            Set to True only for bootstrap runs before any articles exist.

    Returns:
        List of scored topic recommendations, filtered against the
        published_articles archive (near-duplicates removed).

    Raises:
        RuntimeError: If the ChromaDB archive is unavailable or empty and
            `allow_empty_archive` is False.
    """
    print("🔭 Topic Scout Agent: Scanning the landscape...\n")

    # Load real blog performance data (ADR-0007 feedback loop).
    # Gracefully degrades if data/performance.db is missing.
    print("   Loading performance context from GA4 data...")
    performance_context = get_performance_context(top_limit=5, bottom_limit=5)

    # First, gather current trends from live web search (grounded evidence).
    print("   Researching current trends (live web search)...")
    try:
        trends = build_grounded_trend_context(
            focus_area=focus_area,
        )
    except Exception as exc:
        logger.warning(
            "Trend grounding failed (%s); falling back to unverified mode", exc
        )
        trends = (
            "## Live Trend Evidence\n\n"
            "_Trend grounding encountered an error. Rely on your training "
            "knowledge but flag any claims as [UNVERIFIED]._\n"
        )

    # Then, identify topics based on trends AND real blog performance
    print("   Identifying high-value topics (informed by real audience data)...")
    scout_prompt = f"""{performance_context}

---

## Current Trends in Quality Engineering

{trends}

---

{SCOUT_AGENT_PROMPT}"""

    response_text = call_llm(
        client,
        "",  # System prompt embedded in scout_prompt
        scout_prompt,
        max_tokens=3000,
    )

    topics = _parse_topics_json(response_text)
    if topics is None:
        return []

    # Diversity check: if >40% of topics share the same theme, regenerate once.
    # Requires at least 3 topics to be meaningful (with 2, any split is ≥50%).
    is_diverse, dominant_theme = check_topic_diversity(topics)
    if len(topics) >= 3 and not is_diverse:
        print(
            f"   ⚠ Diversity check failed: too many '{dominant_theme}' topics "
            f"(>{int(0.4 * 100)}% threshold). Regenerating with diversity hint..."
        )
        diversity_hint = (
            f"\n\nDIVERSITY ALERT: Your previous response contained too many topics "
            f"about '{dominant_theme}'. You MUST now produce topics that span at least "
            f"4 different categories. Do NOT include more than 1 topic from "
            f"'{dominant_theme}'."
        )
        retry_response = call_llm(
            client,
            "",
            scout_prompt + diversity_hint,
            max_tokens=3000,
        )
        retry_topics = _parse_topics_json(retry_response, label="on retry")
        if retry_topics is None:
            return []
        topics = retry_topics

    # Sort by score
    topics.sort(key=lambda x: x.get("total_score", 0), reverse=True)

    # Deduplicate against the published-articles archive (issue #237).
    # Fail-closed: if the archive is unavailable or empty, abort rather
    # than publish dedup-blind. Callers can opt out via allow_empty_archive.
    print("\n   Running dedup check against published_articles archive...")
    deduplicator = TopicDeduplicator()
    archive_ok = (
        deduplicator.collection is not None and deduplicator.collection.count() > 0
    )
    if not archive_ok:
        msg = (
            "TopicDeduplicator archive unavailable or empty — refusing to "
            "publish dedup-blind. Run scripts/index_published_articles.py "
            "to backfill the published_articles collection, or re-run with "
            "TOPIC_SCOUT_ALLOW_EMPTY_ARCHIVE=1 for a bootstrap run."
        )
        if not allow_empty_archive:
            raise RuntimeError(msg)
        logger.warning("%s (allow_empty_archive=True, proceeding)", msg)

    kept, rejected = deduplicator.filter_topics(topics)
    if rejected:
        print(
            f"   🚫 Dropped {len(rejected)} near-duplicate topic(s) "
            f"against the published archive."
        )
    topics = kept

    print(f"\n✅ Found {len(topics)} high-value topics:\n")
    for i, t in enumerate(topics, 1):
        score = t.get("total_score", 0)
        print(f"   {i}. [{score}/25] {t['topic']}")
        print(f"      └─ {t.get('hook', 'No hook')[:80]}...")

    return topics


def update_content_queue(topics: list, queue_file: str = "content_queue.json"):
    """Save scouted topics to a queue file."""
    queue_data = {"updated": datetime.now().isoformat(), "topics": topics}
    with open(queue_file, "w") as f:
        json.dump(queue_data, f, indent=2)
    print(f"\n📝 Saved {len(topics)} topics to {queue_file}")


def format_for_workflow(topics: list) -> str:
    """Format topics for GitHub Actions workflow dispatch."""
    output = []
    for t in topics:
        output.append(
            {
                "topic": t["topic"],
                "category": "quality-engineering",
                "talking_points": t.get("talking_points", ""),
                "score": t.get("total_score", 0),
            }
        )
    return json.dumps(output, indent=2)


def main():
    client = create_client()

    # Optional focus area from environment
    focus = os.environ.get("FOCUS_AREA", "").strip()

    # Bootstrap escape hatch for dedup fail-closed (issue #237). Only set
    # this for the very first run, before any articles exist in the archive.
    allow_empty = bool(os.environ.get("TOPIC_SCOUT_ALLOW_EMPTY_ARCHIVE", "").strip())

    topics = scout_topics(
        client,
        focus if focus else None,
        allow_empty_archive=allow_empty,
    )

    if topics:
        # Save to queue
        update_content_queue(topics)

        # Also output for GitHub Actions
        print("\n" + "=" * 60)
        print("WORKFLOW-READY FORMAT:")
        print("=" * 60)
        print(format_for_workflow(topics))

        # Set output for GitHub Actions
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                # Escape for GitHub Actions
                topics_json = (
                    json.dumps(topics)
                    .replace("%", "%25")
                    .replace("\n", "%0A")
                    .replace("\r", "%0D")
                )
                f.write(f"topics={topics_json}\n")
                f.write(f"top_topic={topics[0]['topic']}\n")


if __name__ == "__main__":
    main()
