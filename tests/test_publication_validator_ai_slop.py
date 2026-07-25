#!/usr/bin/env python3
"""B-017 · AI-slop detectors on the publication validator (BUG-054).

The generated flaky-tests article passed every existing economist-writing gate
yet still read like AI slop. These tests pin four **countable** tells that must
be *flagged* (never silently rewritten) and surfaced to the human reviewer:

1. em-dash density  2. the ``not X but Y`` antithesis scaffold
3. meta-commentary on the article's own argument  4. unfalsifiable superlatives

Design contract (see docs/specs/B-017-ai-slop-enforcement.md):
- checks REPORT, they never mutate the article;
- new checks emit HIGH / MEDIUM, **never CRITICAL** — they inform, they don't
  quarantine an otherwise-publishable draft;
- fenced code blocks and the References section are exempt.
"""

from __future__ import annotations

from scripts.publication_validator import PublicationValidator

# ── article builder ──────────────────────────────────────────────────────

_PAD = " ".join(["word"] * 720)  # keeps every fixture over the 700-word floor
_REFERENCES = (
    "## References\n\n"
    '1. Gartner, ["World Quality Report 2024"](https://example.com/a), 2024\n'
    '2. Google, ["Flaky Tests at Scale"](https://example.com/b), 2023\n'
    '3. METR, ["AI Developer Productivity"](https://example.com/c), 2025\n'
)
_CHART = "![Data Chart](/assets/charts/test-chart.png)\n"


def _article(body: str) -> str:
    """Wrap a body in otherwise-valid frontmatter + chart + references."""
    return (
        "---\n"
        "layout: post\n"
        'title: "Specific Descriptive Title for Testing"\n'
        "date: 2026-04-03\n"
        'author: "Ouray Viney"\n'
        'categories: ["Quality Engineering"]\n'
        'description: "A concise test description for SEO purposes"\n'
        "image: /assets/images/test-article.png\n"
        'image_alt: "A testing rig catching defects before release"\n'
        'image_caption: "Illustration: stronger gates catch weaker drafts"\n'
        "---\n\n"
        f"{body}\n\n{_CHART}\n{_REFERENCES}\n"
    )


def _validate(body: str) -> list[dict[str, str]]:
    validator = PublicationValidator(
        expected_date="2026-04-03", require_image_file=False
    )
    _, issues = validator.validate(_article(body))
    return issues


def _by_check(issues: list[dict[str, str]], name: str) -> list[dict[str, str]]:
    return [i for i in issues if i.get("check") == name]


# Real BUG-054 tells, condensed into four paragraphs: em-dash rhythm (~2/para),
# 4 antitheses, 2 meta-commentary phrases, 2 superlatives — then padded over the
# word floor.
_SLOP_BODY = (
    "Flaky tests are not a nuisance but a quantifiable payroll cost — one that "
    "compounds quietly — and the bill lands on payroll, not the test suite. She "
    "is not cutting corners but paying down a debt no ledger records.\n\n"
    "The argument here is blunter than most teams admit — the waste is not "
    "hidden but ignored — and the ignoring is the point. No other category of "
    "engineering waste operates so openly and so unchallenged.\n\n"
    "The numbers, once examined, make this case almost without assistance — a "
    "dripping tap that floods the basement before anyone calls the plumber — a "
    "small leak with a large bill. This is not a technical problem but an "
    "organisational one, and it is the most expensive form of denial a team can "
    "afford.\n\n"
    f"{_PAD}"
)

# Plain Economist-style prose: one em-dash across four paragraphs, no antithesis
# pile-up, no meta-commentary, no absolute superlative.
_CLEAN_BODY = (
    "Flaky tests impose a measurable cost on engineering teams. Gartner puts "
    "the annual figure in the millions for large organisations.\n\n"
    "The mechanism is mundane. A test passes, then fails, then passes again, "
    "and an engineer stops trusting the signal.\n\n"
    "Google reported a concrete number — its continuous-integration system "
    "spent a double-digit share of retries on known-flaky suites.\n\n"
    f"{_PAD}"
)


# ── 1. em-dash density ─────────────────────────────────────────────────────


class TestEmDashDensity:
    def test_dense_em_dashes_flag_high(self) -> None:
        hits = _by_check(_validate(_SLOP_BODY), "em_dash_density")
        assert hits, "dense em-dash rhythm should be flagged"
        assert hits[0]["severity"] == "HIGH"

    def test_clean_prose_not_flagged(self) -> None:
        assert not _by_check(_validate(_CLEAN_BODY), "em_dash_density")

    def test_em_dashes_inside_code_block_exempt(self) -> None:
        body = (
            "Ordinary sentence one. Ordinary sentence two.\n\n"
            "```python\nx = a — b — c — d — e — f\n```\n\n"
            f"{_PAD}"
        )
        assert not _by_check(_validate(body), "em_dash_density")


# ── 2. not-X-but-Y antithesis scaffold ─────────────────────────────────────


class TestAntithesisScaffold:
    def test_repeated_antithesis_flags_high(self) -> None:
        hits = _by_check(_validate(_SLOP_BODY), "antithesis_scaffold")
        assert hits and hits[0]["severity"] == "HIGH"

    def test_single_antithesis_not_flagged(self) -> None:
        # One antithesis is legitimate rhetoric — the tell is the *pile-up*.
        body = "The cost is not trivial but real. " + _PAD
        assert not _by_check(_validate(body), "antithesis_scaffold")

    def test_two_antitheses_are_medium(self) -> None:
        body = (
            "The cost is not trivial but real. The fix is not quick but worth it. "
            + _PAD
        )
        hits = _by_check(_validate(body), "antithesis_scaffold")
        assert hits and hits[0]["severity"] == "MEDIUM"

    def test_clean_prose_not_flagged(self) -> None:
        assert not _by_check(_validate(_CLEAN_BODY), "antithesis_scaffold")


# ── 3. meta-commentary on the argument ─────────────────────────────────────


class TestMetaCommentary:
    def test_meta_commentary_flags_high(self) -> None:
        hits = _by_check(_validate(_SLOP_BODY), "meta_commentary")
        assert hits and hits[0]["severity"] == "HIGH"

    def test_clean_prose_not_flagged(self) -> None:
        assert not _by_check(_validate(_CLEAN_BODY), "meta_commentary")


# ── 4. unfalsifiable superlatives ──────────────────────────────────────────


class TestSuperlatives:
    def test_multiple_superlatives_flag_high(self) -> None:
        hits = _by_check(_validate(_SLOP_BODY), "unfalsifiable_superlative")
        assert hits and hits[0]["severity"] == "HIGH"

    def test_clean_prose_not_flagged(self) -> None:
        assert not _by_check(_validate(_CLEAN_BODY), "unfalsifiable_superlative")


# ── cross-cutting invariants ───────────────────────────────────────────────


class TestInvariants:
    def test_slop_flags_never_block_publication(self) -> None:
        # An article whose ONLY faults are slop tells must stay publishable —
        # the new checks inform, they never emit CRITICAL.
        validator = PublicationValidator(
            expected_date="2026-04-03", require_image_file=False
        )
        is_valid, issues = validator.validate(_article(_SLOP_BODY))
        new_checks = {
            "em_dash_density",
            "antithesis_scaffold",
            "meta_commentary",
            "unfalsifiable_superlative",
        }
        assert any(i.get("check") in new_checks for i in issues), "expected slop flags"
        assert not [
            i
            for i in issues
            if i.get("check") in new_checks and i["severity"] == "CRITICAL"
        ], "slop checks must never be CRITICAL"
        assert is_valid, "slop-only article must remain publishable (no CRITICAL)"

    def test_validate_is_idempotent(self) -> None:
        validator = PublicationValidator(
            expected_date="2026-04-03", require_image_file=False
        )
        art = _article(_SLOP_BODY)
        first = validator.validate(art)[1]
        second = validator.validate(art)[1]
        assert len(first) == len(second), "issues must not accumulate across calls"

    def test_clean_article_has_no_new_flags(self) -> None:
        issues = _validate(_CLEAN_BODY)
        new_checks = {
            "em_dash_density",
            "antithesis_scaffold",
            "meta_commentary",
            "unfalsifiable_superlative",
        }
        assert not [i for i in issues if i.get("check") in new_checks]


# ---------------------------------------------------------------------------
# BUG-055 guard: `image:` present-but-empty must be CRITICAL, not silently OK
# ---------------------------------------------------------------------------


class TestEmptyImageIsCritical:
    """An empty ``image:`` is worse than an absent one and must never deploy.

    Stage 4 now omits the key, but an article generated before that fix (or a
    writer that emits the key itself) can still carry ``image: ""`` — and it
    silently breaks the blog's REQUIRED ``build`` check, because Liquid treats
    ``""`` as truthy, satisfies ``{% if page.image %}``, and renders an ``<img>``
    with no ``src`` for html-proofer to reject. This is the deterministic local
    gate that BUG-055 lacked: it escaped to the blog's CI instead.
    """

    def _issues(self, image_line: str) -> list[dict[str, str]]:
        article = _article(_CLEAN_BODY).replace(
            "image: /assets/images/test-article.png", image_line
        )
        validator = PublicationValidator(
            expected_date="2026-04-03", require_image_file=False
        )
        return validator.validate(article)[1]

    def test_empty_quoted_image_is_critical(self) -> None:
        hits = _by_check(self._issues('image: ""'), "empty_image_value")
        assert hits, 'image: "" must be flagged'
        assert hits[0]["severity"] == "CRITICAL"

    def test_bare_empty_image_is_critical(self) -> None:
        hits = _by_check(self._issues("image:"), "empty_image_value")
        assert hits and hits[0]["severity"] == "CRITICAL"

    def test_absent_image_key_is_fine(self) -> None:
        # Chart-only (#403 Path A): omitting the key entirely is the correct form.
        article = "\n".join(
            line
            for line in _article(_CLEAN_BODY).splitlines()
            if not line.startswith("image")
        )
        validator = PublicationValidator(
            expected_date="2026-04-03", require_image_file=False
        )
        is_valid, issues = validator.validate(article)
        assert not _by_check(issues, "empty_image_value")
        assert is_valid, [i for i in issues if i["severity"] == "CRITICAL"]

    def test_real_image_path_is_fine(self) -> None:
        hits = _by_check(
            self._issues("image: /assets/images/test-article.png"), "empty_image_value"
        )
        assert not hits
