from src.crews.stage3_crew import Stage3Crew


def test_stage3_crew_migration():
    # Arrange
    crew = Stage3Crew(topic="Self-Healing Tests")

    # Act
    result = crew.kickoff()

    # Assert
    assert "article" in result
    assert "chart_data" in result
    assert len(result["article"]) > 500
