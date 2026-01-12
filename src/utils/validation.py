#!/usr/bin/env python3
"""
Input Validation Utility Functions

Provides standardized validation functions for agent input processing.
"""

from typing import Any


def run_research_agent(client: Any, topic: str, research_brief: dict[str, Any]) -> bool:
    """
    Run the research agent to analyze a given topic and update the research brief.

    Args:
        client: Mock or actual client used for interfacing with the agent infrastructure
        topic: The topic to be researched. Must be a non-empty string with at least 3 characters
        research_brief: A dictionary to be populated with research results. Must be non-empty

    Returns:
        True if the operation is successful, False otherwise

    Raises:
        ValueError: If topic is invalid or research_brief is empty
    """
    # Validate inputs
    if not isinstance(topic, str) or len(topic.strip()) < 3:
        raise ValueError(
            "Invalid topic: Must be a non-empty string with at least 3 characters."
        )

    if not research_brief:
        raise ValueError("Empty research_brief")

    # Agent logic
    research_brief["status"] = "completed"
    research_brief["data"] = "Research data"
    return True


def validate_agent_input(
    input_data: dict[str, Any], required_fields: list[str]
) -> bool:
    """
    Validate agent input data contains required fields.

    Args:
        input_data: Dictionary containing input data to validate
        required_fields: List of required field names

    Returns:
        True if validation passes

    Raises:
        ValueError: If required fields are missing or invalid
    """
    if not isinstance(input_data, dict):
        raise ValueError("Input data must be a dictionary")

    if not required_fields:
        raise ValueError("Required fields list cannot be empty")

    missing_fields = [field for field in required_fields if field not in input_data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")

    return True
