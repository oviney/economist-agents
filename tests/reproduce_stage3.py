from src.crews.stage3_crew import Stage3Crew


def test_stage3_crew_migration():
    # Arrange
    crew = Stage3Crew(topic="Self-Healing Tests")

    # Act
    result = crew.kickoff()

    # Assert - Structure
    assert "article" in result
    assert "chart_data" in result

    # Assert - Not Empty
    assert result["article"] is not None
    assert len(result["article"]) > 500
    assert result["chart_data"] is not None

    # Assert - Format Mimics Legacy
    # Article should contain typical Economist elements
    article = result["article"]
    assert "---" in article  # YAML frontmatter
    assert "title:" in article
    assert "date:" in article

    # Chart data should have structure
    chart = result["chart_data"]
    assert isinstance(chart, dict)

    # Add specific chart structure checks based on legacy format
    # Example checks (customize based on legacy data structure):
    assert "data" in chart
    assert isinstance(chart["data"], list)
    assert len(chart["data"]) > 0

    # Validate required fields in article YAML frontmatter
    # Simple presence checks for typical fields
    assert "author:" in article or "Author:" in article
    assert "summary:" in article or "Summary:" in article
