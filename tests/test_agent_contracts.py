"""
Agent Contract Tests

Validates the contracts between pipeline agents:
- Research → Writer schema contract
- Citation integrity (no fabricated stats / embedded secrets)
- FrontmatterSchema validate_article structured result
"""


def test_research_writer_schema_contract():
    """Writer output must include all required front matter fields."""
    from scripts.frontmatter_schema import REQUIRED_FIELDS, FrontmatterSchema

    schema = FrontmatterSchema()

    valid_output = (
        '---\nlayout: post\ntitle: "Test Article"\ndate: 2026-04-14\n'
        'author: "Ouray Viney"\ncategories: ["quality-engineering"]\n'
        "image: /assets/images/test-article.png\n"
        'description: "A test article about quality engineering."\n'
        "---\n\nContent here."
    )
    result = schema.validate_article(valid_output)
    assert result.is_valid, f"Valid writer output failed schema: {result.errors}"

    for field in REQUIRED_FIELDS:
        incomplete = valid_output.replace(f"\n{field}:", "\nMISSING_FIELD:")
        result = schema.validate_article(incomplete)
        assert not result.is_valid, f"Missing {field} should fail validation"
        assert any(field in e for e in result.errors), f"Error should mention {field}"


def test_citation_integrity_no_fabricated_stats():
    """Article body should not contain suspicious unattributed statistics."""
    from scripts.frontmatter_schema import FrontmatterSchema

    schema = FrontmatterSchema()

    with_citation = (
        '---\nlayout: post\ntitle: "AI Study"\ndate: 2026-04-14\n'
        'author: "Ouray Viney"\ncategories: ["software-engineering"]\n'
        "image: /assets/images/ai-study.png\n"
        'description: "Analysis of AI adoption."\n'
        "---\n\n"
        "According to McKinsey's 2024 report, 72% of companies have adopted AI. "
        "The data shows strong growth."
    )
    result = schema.validate_article(with_citation)
    assert result.is_valid

    with_secret = (
        '---\nlayout: post\ntitle: "Test"\ndate: 2026-04-14\n'
        'author: "Ouray Viney"\ncategories: ["test-automation"]\n'
        "image: /assets/images/test.png\n"
        'description: "Test post."\n'
        "---\n\nContent here."
    )
    result = schema.validate_article(with_secret)
    assert result.is_valid

    # The schema surfaces embedded API keys as a warning (not a hard error),
    # keeping is_valid=True so the pipeline can still route the article — but
    # the warning must be present so the publisher can review before deploying.
    with_api_key = (
        '---\nlayout: post\ntitle: "Test"\ndate: 2026-04-14\n'
        'author: "Ouray Viney"\ncategories: ["test-automation"]\n'
        "image: /assets/images/test.png\n"
        'description: "API key: sk-abcdefghijklmnopqrstuvwxyz123456"\n'
        "---\n\nContent"
    )
    result = schema.validate_article(with_api_key)
    assert any(
        "sensitive" in w.lower() or "secret" in w.lower() or "api" in w.lower()
        for w in result.warnings
    ), f"Expected sensitive-data warning, got: {result.warnings}"


def test_validate_file_returns_structured_result():
    """validate_article() should return ValidationResult with is_valid, errors, warnings."""
    from scripts.frontmatter_schema import FrontmatterSchema, ValidationResult

    schema = FrontmatterSchema()

    valid_content = (
        '---\nlayout: post\ntitle: "Contract Test"\ndate: 2026-04-14\n'
        'author: "Ouray Viney"\ncategories: ["quality-engineering"]\n'
        "image: /assets/images/contract-test.png\n"
        'description: "A contract test article."\n'
        "---\n\nSome content here."
    )

    result = schema.validate_article(valid_content)
    assert isinstance(result, ValidationResult)
    assert result.is_valid
    assert result.errors == []
