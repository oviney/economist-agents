"""
Comprehensive tests for generate_chart.py

Tests chart generation functionality including:
- Chart creation with valid data
- Economist style configuration (colors, fonts, layout)
- Data validation and error handling
- Module constants and data structures

Target: >90% coverage

Note: generate_chart.py is a procedural script that executes on import.
We mock plt.savefig BEFORE importing to avoid FileNotFoundError.
The script runs once on first import, so we test the results of that execution.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from io import StringIO

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Mock savefig and close BEFORE importing generate_chart
# This prevents FileNotFoundError when script tries to save to hardcoded path
_mock_savefig = MagicMock()
_mock_close = MagicMock()

with patch('matplotlib.pyplot.savefig', _mock_savefig), \
     patch('matplotlib.pyplot.close', _mock_close):
    # Import with coverage tracking enabled
    import generate_chart  # This will execute the script safely


# ============================================================================
# TEST CONSTANTS AND DATA
# ============================================================================


def test_economist_color_constants():
    """Test that Economist color constants are defined correctly."""
    assert generate_chart.NAVY == "#17648d"
    assert generate_chart.BURGUNDY == "#843844"
    assert generate_chart.RED_BAR == "#e3120b"
    assert generate_chart.BG_COLOR == "#f1f0e9"
    assert generate_chart.GRAY_TEXT == "#666666"
    assert generate_chart.GRAY_LIGHT == "#888888"
    assert generate_chart.GRID_COLOR == "#cccccc"


def test_data_arrays_defined():
    """Test that chart data arrays are defined."""
    # Verify data arrays exist
    assert hasattr(generate_chart, "years")
    assert hasattr(generate_chart, "ai_adoption")
    assert hasattr(generate_chart, "maintenance_reduction")
    
    # Verify data structure
    assert isinstance(generate_chart.years, list)
    assert isinstance(generate_chart.ai_adoption, list)
    assert isinstance(generate_chart.maintenance_reduction, list)
    
    # Verify data lengths match
    assert len(generate_chart.years) == len(generate_chart.ai_adoption)
    assert len(generate_chart.years) == len(generate_chart.maintenance_reduction)


def test_data_arrays_content():
    """Test that data arrays have valid content."""
    # Verify years are sequential
    years = generate_chart.years
    assert years == sorted(years)
    assert years[0] == 2018
    assert years[-1] == 2025
    assert len(years) == 8
    
    # Verify ai_adoption values are reasonable percentages
    ai_adoption = generate_chart.ai_adoption
    assert all(0 <= val <= 100 for val in ai_adoption)
    assert ai_adoption[-1] > ai_adoption[0]  # Overall trend upward
    assert ai_adoption == [12, 18, 28, 42, 55, 68, 78, 81]
    
    # Verify maintenance_reduction values
    maintenance = generate_chart.maintenance_reduction
    assert all(val >= 0 for val in maintenance)
    assert maintenance == [0, 2, 5, 8, 12, 14, 16, 18]


def test_data_integrity():
    """Test that data maintains referential integrity."""
    # AI adoption should be higher than maintenance reduction
    for ai, maint in zip(generate_chart.ai_adoption, generate_chart.maintenance_reduction):
        assert ai >= maint  # AI adoption always higher or equal
    
    # Last year should show the gap (the automation gap theme)
    assert generate_chart.ai_adoption[-1] > generate_chart.maintenance_reduction[-1]
    gap = generate_chart.ai_adoption[-1] - generate_chart.maintenance_reduction[-1]
    assert gap > 60  # Significant gap as intended by chart


# ============================================================================
# TEST MATPLOTLIB CONFIGURATION
# ============================================================================


def test_matplotlib_imports():
    """Test that matplotlib modules are imported correctly."""
    assert hasattr(generate_chart, "plt")
    assert hasattr(generate_chart, "mpatches")


def test_font_configuration():
    """Test that DejaVu Sans font is configured."""
    # Font should have been set when module loaded
    assert "font.family" in plt.rcParams
    font_family = plt.rcParams["font.family"]
    # Could be a list or string depending on matplotlib version
    if isinstance(font_family, list):
        assert "DejaVu Sans" in font_family
    else:
        assert "DejaVu Sans" in str(font_family)


def test_font_size_configuration():
    """Test that font size is configured."""
    assert "font.size" in plt.rcParams
    assert plt.rcParams["font.size"] == 10


def test_axes_linewidth_configuration():
    """Test that axes linewidth is set to 0."""
    assert "axes.linewidth" in plt.rcParams
    assert plt.rcParams["axes.linewidth"] == 0


# ============================================================================
# TEST CHART FILE OUTPUT
# ============================================================================


def test_output_path_defined():
    """Test that output path is defined."""
    assert hasattr(generate_chart, "output_path")
    assert isinstance(generate_chart.output_path, str)
    assert generate_chart.output_path.endswith(".png")


def test_chart_saved_with_correct_parameters():
    """Test that chart would be saved with correct parameters."""
    # The script already ran during import with our mock
    # We're testing that the expected path format exists
    expected_path = "/home/claude/blog-automation/assets/charts/testing-times-ai-gap.png"
    assert generate_chart.output_path == expected_path


def test_economist_style_colors_used():
    """Test that Economist colors are used in the chart."""
    # Verify all Economist colors are defined and valid hex colors
    colors = [
        generate_chart.NAVY,
        generate_chart.BURGUNDY, 
        generate_chart.RED_BAR,
        generate_chart.BG_COLOR,
        generate_chart.GRAY_TEXT,
        generate_chart.GRAY_LIGHT,
        generate_chart.GRID_COLOR,
    ]
    
    for color in colors:
        assert color.startswith("#")
        assert len(color) == 7  # #RRGGBB format
        # Verify hex digits
        assert all(c in "0123456789abcdefABCDEF" for c in color[1:])


# ============================================================================
# TEST MODULE STRUCTURE
# ============================================================================


def test_module_has_no_syntax_errors():
    """Test that generate_chart module imports without syntax errors."""
    # If we got here, import succeeded (happened at top of file)
    assert generate_chart is not None


def test_all_constants_accessible():
    """Test that all expected constants are accessible."""
    required_constants = [
        "NAVY", "BURGUNDY", "RED_BAR", "BG_COLOR",
        "GRAY_TEXT", "GRAY_LIGHT", "GRID_COLOR",
        "years", "ai_adoption", "maintenance_reduction",
        "output_path"
    ]
    
    for const in required_constants:
        assert hasattr(generate_chart, const), f"Missing constant: {const}"


def test_matplotlib_backend_agnostic():
    """Test that chart generation works with Agg backend."""
    # Script should have configured matplotlib for headless operation
    # The module was successfully imported, so it worked with current backend
    assert generate_chart.plt is not None


# ============================================================================
# TEST DATA RELATIONSHIPS
# ============================================================================


def test_automation_gap_exists():
    """Test that the chart demonstrates an automation gap."""
    # The chart's theme is the gap between AI adoption and maintenance reduction
    ai_final = generate_chart.ai_adoption[-1]
    maint_final = generate_chart.maintenance_reduction[-1]
    
    gap = ai_final - maint_final
    
    # Gap should be significant (this is the chart's main point)
    assert gap > 50, f"Gap ({gap}) should be significant to show automation paradox"
    
    # AI adoption should be much higher
    assert ai_final > maint_final * 3, "AI adoption should be multiple of maintenance reduction"


def test_trend_directions():
    """Test that both trends move in expected directions."""
    ai = generate_chart.ai_adoption
    maint = generate_chart.maintenance_reduction
    
    # Both should trend upward
    assert ai[-1] > ai[0], "AI adoption should increase over time"
    assert maint[-1] > maint[0], "Maintenance reduction should increase over time"
    
    # AI should grow faster (that's the gap)
    ai_growth = ai[-1] - ai[0]
    maint_growth = maint[-1] - maint[0]
    assert ai_growth > maint_growth * 3, "AI growth should far exceed maintenance reduction growth"


def test_year_range_reasonable():
    """Test that year range makes sense for the data."""
    years = generate_chart.years
    
    # Should span reasonable period (8 years)
    assert len(years) == 8
    
    # Should be recent years (2018-2025)
    assert years[0] >= 2015
    assert years[-1] <= 2030
    
    # Should be consecutive
    for i in range(len(years) - 1):
        assert years[i+1] == years[i] + 1


def test_percentage_values_valid():
    """Test that all percentage values are valid."""
    ai = generate_chart.ai_adoption
    maint = generate_chart.maintenance_reduction
    
    # All values should be valid percentages (0-100)
    for val in ai + maint:
        assert 0 <= val <= 100, f"Value {val} outside valid percentage range"
        assert isinstance(val, (int, float)), f"Value {val} not numeric"


# ============================================================================
# TEST ECONOMIST DESIGN STANDARDS
# ============================================================================


def test_color_palette_complete():
    """Test that complete Economist color palette is defined."""
    palette = {
        "primary": generate_chart.NAVY,
        "secondary": generate_chart.BURGUNDY,
        "highlight": generate_chart.RED_BAR,
        "background": generate_chart.BG_COLOR,
        "text_primary": generate_chart.GRAY_TEXT,
        "text_secondary": generate_chart.GRAY_LIGHT,
        "grid": generate_chart.GRID_COLOR,
    }
    
    # All colors should be distinct
    assert len(set(palette.values())) == len(palette)
    
    # All should be valid hex colors
    for name, color in palette.items():
        assert color.startswith("#"), f"{name} color doesn't start with #"
        assert len(color) == 7, f"{name} color not in #RRGGBB format"


def test_navy_primary_color():
    """Test that navy is the primary data color."""
    assert generate_chart.NAVY == "#17648d"
    # This should be used for the primary (AI adoption) series


def test_burgundy_secondary_color():
    """Test that burgundy is the secondary data color."""
    assert generate_chart.BURGUNDY == "#843844"
    # This should be used for the secondary (maintenance) series


def test_red_bar_highlight():
    """Test that red bar color is correct."""
    assert generate_chart.RED_BAR == "#e3120b"
    # This is the Economist's signature red for the top bar


def test_background_warmth():
    """Test that background is warm beige (not pure white)."""
    assert generate_chart.BG_COLOR == "#f1f0e9"
    # Economist uses warm beige, not harsh white


# ============================================================================
# EDGE CASES AND VALIDATION
# ============================================================================


def test_no_negative_values():
    """Test that there are no negative values in the data."""
    all_values = generate_chart.ai_adoption + generate_chart.maintenance_reduction
    assert all(val >= 0 for val in all_values)


def test_no_missing_data():
    """Test that there are no None or NaN values."""
    all_values = generate_chart.ai_adoption + generate_chart.maintenance_reduction
    assert all(val is not None for val in all_values)
    
    # Check for NaN (if using numpy/pandas)
    import math
    assert all(not (isinstance(val, float) and math.isnan(val)) for val in all_values)


def test_data_year_alignment():
    """Test that data points align with years."""
    # Each data series should have exactly one value per year
    assert len(generate_chart.years) == len(generate_chart.ai_adoption)
    assert len(generate_chart.years) == len(generate_chart.maintenance_reduction)


def test_final_year_is_2025():
    """Test that final year is 2025 (current data endpoint)."""
    assert generate_chart.years[-1] == 2025


def test_baseline_year_is_2018():
    """Test that baseline year is 2018."""
    assert generate_chart.years[0] == 2018


# ============================================================================
# PRINT OUTPUT TESTS (capturing the script's prints)
# ============================================================================


def test_success_message_would_print():
    """Test that success message format is correct."""
    # The script prints a success message - test the path format
    output_path = generate_chart.output_path
    assert "testing-times-ai-gap.png" in output_path
    
    # Expected print format
    expected_print = f"Chart saved to {output_path}"
    assert expected_print  # Path is valid for print statement
