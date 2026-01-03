#!/usr/bin/env python3
"""
Graphics Agent Tasks - Chart Generation Task Specifications

Defines task configurations for the Graphics Agent.
Compatible with CrewAI task structure for future migration.

Task Types:
- generate_chart: Create Economist-style visualization
- validate_zones: Check zone boundary compliance
- optimize_labels: Position labels in clear space
"""

from typing import Any


class GraphicsTask:
    """
    Task specification for Graphics Agent.

    Attributes:
        task_type: Type of graphics task (generate_chart, validate_zones, etc.)
        chart_spec: Chart specification with title, data, type
        output_path: Path to save generated chart
        validation_level: Visual QA validation strictness (strict, medium, lenient)
        max_tokens: Maximum LLM tokens for code generation
    """

    def __init__(
        self,
        task_type: str,
        chart_spec: dict[str, Any],
        output_path: str,
        validation_level: str = "strict",
        max_tokens: int = 2500,
    ):
        self.task_type = task_type
        self.chart_spec = chart_spec
        self.output_path = output_path
        self.validation_level = validation_level
        self.max_tokens = max_tokens

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary format."""
        return {
            "task_type": self.task_type,
            "chart_spec": self.chart_spec,
            "output_path": self.output_path,
            "validation_level": self.validation_level,
            "max_tokens": self.max_tokens,
        }


def create_chart_generation_task(
    chart_spec: dict[str, Any], output_path: str, max_tokens: int = 2500
) -> GraphicsTask:
    """
    Create a chart generation task.

    Args:
        chart_spec: Chart specification with required fields:
            - title: Chart title
            - data: Chart data (series, x-axis values, etc.)
            - type: Chart type (line, bar, scatter, etc.)
            - subtitle: Optional subtitle
            - source: Data source attribution
        output_path: Path to save generated PNG file
        max_tokens: Maximum tokens for LLM code generation

    Returns:
        GraphicsTask configured for chart generation

    Example:
        >>> task = create_chart_generation_task(
        ...     chart_spec={
        ...         "title": "AI Adoption vs Maintenance Reduction",
        ...         "subtitle": "Percentage of companies, 2018-2025",
        ...         "type": "line",
        ...         "data": {
        ...             "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
        ...             "ai_adoption": [12, 18, 28, 42, 55, 68, 78, 81],
        ...             "maintenance_reduction": [0, 2, 5, 8, 12, 14, 16, 18]
        ...         },
        ...         "source": "Tricentis Research; TestGuild Survey"
        ...     },
        ...     output_path="/path/to/chart.png"
        ... )
    """
    return GraphicsTask(
        task_type="generate_chart",
        chart_spec=chart_spec,
        output_path=output_path,
        validation_level="strict",
        max_tokens=max_tokens,
    )


def create_zone_validation_task(
    chart_path: str, validation_level: str = "strict"
) -> GraphicsTask:
    """
    Create a zone validation task.

    Validates that chart elements respect zone boundaries:
    - Red bar zone (y: 0.96-1.00)
    - Title zone (y: 0.85-0.94)
    - Chart zone (y: 0.15-0.78)
    - X-axis zone (y: 0.08-0.14)
    - Source zone (y: 0.01-0.06)

    Args:
        chart_path: Path to existing chart PNG file
        validation_level: Strictness level (strict, medium, lenient)

    Returns:
        GraphicsTask configured for zone validation
    """
    return GraphicsTask(
        task_type="validate_zones",
        chart_spec={"validation_target": chart_path},
        output_path=chart_path,  # In-place validation
        validation_level=validation_level,
        max_tokens=1000,  # Lower tokens for validation
    )


def create_label_optimization_task(
    chart_spec: dict[str, Any], current_code: str, output_path: str
) -> GraphicsTask:
    """
    Create a label optimization task.

    Optimizes label positioning to avoid overlaps:
    - Labels in clear space (not on data lines)
    - No overlap with x-axis labels
    - End-of-line labels where possible
    - xytext offsets for proper spacing

    Args:
        chart_spec: Original chart specification
        current_code: Current matplotlib code with label issues
        output_path: Path to save optimized chart

    Returns:
        GraphicsTask configured for label optimization
    """
    optimization_spec = chart_spec.copy()
    optimization_spec["optimization_target"] = "labels"
    optimization_spec["current_code"] = current_code

    return GraphicsTask(
        task_type="optimize_labels",
        chart_spec=optimization_spec,
        output_path=output_path,
        validation_level="strict",
        max_tokens=2000,
    )


# Task Templates for common chart types

TASK_TEMPLATES = {
    "line_chart": {
        "description": "Generate Economist-style line chart",
        "chart_type": "line",
        "required_fields": ["title", "data", "source"],
        "optional_fields": ["subtitle", "y_label", "x_label"],
        "validation_rules": [
            "zone_boundaries",
            "inline_labels",
            "color_palette",
            "gridlines_horizontal_only",
        ],
    },
    "bar_chart": {
        "description": "Generate Economist-style bar chart",
        "chart_type": "bar",
        "required_fields": ["title", "data", "source"],
        "optional_fields": ["subtitle", "y_label", "x_label"],
        "validation_rules": [
            "zone_boundaries",
            "data_labels",
            "color_palette",
            "gridlines_horizontal_only",
        ],
    },
    "scatter_plot": {
        "description": "Generate Economist-style scatter plot",
        "chart_type": "scatter",
        "required_fields": ["title", "data", "source"],
        "optional_fields": ["subtitle", "y_label", "x_label", "regression_line"],
        "validation_rules": [
            "zone_boundaries",
            "point_labels",
            "color_palette",
            "gridlines_horizontal_only",
        ],
    },
}


def get_task_template(chart_type: str) -> dict[str, Any] | None:
    """
    Get task template for chart type.

    Args:
        chart_type: Type of chart (line_chart, bar_chart, scatter_plot)

    Returns:
        Template dict or None if not found
    """
    return TASK_TEMPLATES.get(chart_type)


def validate_chart_spec(
    chart_spec: dict[str, Any], chart_type: str = None
) -> tuple[bool, list[str]]:
    """
    Validate chart specification against template requirements.

    Args:
        chart_spec: Chart specification to validate
        chart_type: Expected chart type (optional)

    Returns:
        (is_valid, error_messages)
    """
    errors = []

    # Check required fields
    if "title" not in chart_spec:
        errors.append("Missing required field: title")
    if "data" not in chart_spec:
        errors.append("Missing required field: data")

    # Check chart type specific requirements
    if chart_type and chart_type in TASK_TEMPLATES:
        template = TASK_TEMPLATES[chart_type]
        for field in template["required_fields"]:
            if field not in chart_spec:
                errors.append(f"Missing required field for {chart_type}: {field}")

    return (len(errors) == 0, errors)


if __name__ == "__main__":
    print("Graphics Tasks - Chart Generation Task Specifications")
    print("=" * 70)
    print("\nAvailable Task Types:")
    print("  - generate_chart: Create Economist-style visualization")
    print("  - validate_zones: Check zone boundary compliance")
    print("  - optimize_labels: Position labels in clear space")
    print("\nTask Templates:")
    for chart_type, template in TASK_TEMPLATES.items():
        print(f"  - {chart_type}: {template['description']}")
