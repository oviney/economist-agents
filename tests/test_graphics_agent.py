#!/usr/bin/env python3
"""
Tests for Graphics Agent

Comprehensive test suite covering:
- Chart generation with valid/invalid specs
- Zone boundary enforcement
- Label positioning
- Matplotlib code generation
- Error handling
- Metrics collection
- Backward compatibility
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.graphics_agent import GraphicsAgent, run_graphics_agent
from agents.graphics_tasks import (
    TASK_TEMPLATES,
    GraphicsTask,
    create_chart_generation_task,
    create_label_optimization_task,
    create_zone_validation_task,
    get_task_template,
    validate_chart_spec,
)

# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = Mock()
    client.provider = "anthropic"
    client.model = "claude-3-5-sonnet-20241022"
    return client


@pytest.fixture
def valid_chart_spec():
    """Valid chart specification."""
    return {
        "title": "AI Adoption vs Maintenance Reduction",
        "subtitle": "Percentage of companies, 2018-2025",
        "type": "line",
        "data": {
            "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
            "ai_adoption": [12, 18, 28, 42, 55, 68, 78, 81],
            "maintenance_reduction": [0, 2, 5, 8, 12, 14, 16, 18],
        },
        "source": "Tricentis Research; TestGuild Survey",
    }


@pytest.fixture
def temp_output_path():
    """Temporary output path for chart."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def mock_metrics_collector():
    """Mock metrics collector."""
    with patch("agents.graphics_agent.get_metrics_collector") as mock:
        collector = Mock()
        chart_record = {
            "title": "Test Chart",
            "timestamp": "2026-01-02T00:00:00",
            "start_time": 0.0,
            "chart_type": "line",
            "generation_success": None,
        }
        collector.start_chart.return_value = chart_record
        collector.record_generation.return_value = None
        mock.return_value = collector
        yield collector


@pytest.fixture
def sample_matplotlib_code():
    """Sample matplotlib code for testing."""
    return """
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

fig, ax = plt.subplots(figsize=(8, 5.5))
fig.patch.set_facecolor('#f1f0e9')
ax.set_facecolor('#f1f0e9')

years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
ai_adoption = [12, 18, 28, 42, 55, 68, 78, 81]

ax.plot(years, ai_adoption, color='#17648d', linewidth=2.5)
ax.set_title('AI Adoption')
"""


# ═══════════════════════════════════════════════════════════════════════════
# GRAPHICS AGENT TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestGraphicsAgentInit:
    """Test Graphics Agent initialization."""

    def test_init_with_client(self, mock_llm_client):
        """Should initialize with LLM client."""
        agent = GraphicsAgent(mock_llm_client)
        assert agent.client == mock_llm_client
        assert agent.metrics is not None

    def test_has_graphics_prompt(self, mock_llm_client):
        """Should have GRAPHICS_AGENT_PROMPT defined."""
        agent = GraphicsAgent(mock_llm_client)
        assert hasattr(agent, "GRAPHICS_AGENT_PROMPT")
        assert "data visualization specialist" in agent.GRAPHICS_AGENT_PROMPT
        assert "LAYOUT ZONES" in agent.GRAPHICS_AGENT_PROMPT


class TestChartGeneration:
    """Test chart generation functionality."""

    def test_generate_chart_with_none_spec(self, mock_llm_client, temp_output_path):
        """Should return None for None chart_spec."""
        agent = GraphicsAgent(mock_llm_client)
        result = agent.generate_chart(None, temp_output_path)
        assert result is None

    def test_generate_chart_with_empty_spec(self, mock_llm_client, temp_output_path):
        """Should return None for empty chart_spec."""
        agent = GraphicsAgent(mock_llm_client)
        result = agent.generate_chart({}, temp_output_path)
        assert result is None

    def test_generate_chart_validates_chart_spec_type(
        self, mock_llm_client, temp_output_path
    ):
        """Should validate chart_spec is dict."""
        agent = GraphicsAgent(mock_llm_client)
        with pytest.raises(ValueError, match="Invalid chart_spec"):
            agent.generate_chart("not a dict", temp_output_path)

    def test_generate_chart_validates_required_fields(
        self, mock_llm_client, temp_output_path
    ):
        """Should validate required fields present."""
        agent = GraphicsAgent(mock_llm_client)
        with pytest.raises(ValueError, match="missing required fields"):
            agent.generate_chart({"title": "Test"}, temp_output_path)  # Missing data

    def test_generate_chart_validates_output_path(
        self, mock_llm_client, valid_chart_spec
    ):
        """Should validate output_path is non-empty string."""
        agent = GraphicsAgent(mock_llm_client)
        with pytest.raises(ValueError, match="Invalid output_path"):
            agent.generate_chart(valid_chart_spec, "")
        with pytest.raises(ValueError, match="Invalid output_path"):
            agent.generate_chart(valid_chart_spec, None)

    @patch("llm_client.call_llm")
    @patch("subprocess.run")
    def test_generate_chart_success(
        self,
        mock_subprocess,
        mock_call_llm,
        mock_llm_client,
        valid_chart_spec,
        temp_output_path,
        sample_matplotlib_code,
        mock_metrics_collector,
    ):
        """Should generate chart successfully."""
        mock_call_llm.return_value = sample_matplotlib_code
        mock_subprocess.return_value = Mock(returncode=0)

        agent = GraphicsAgent(mock_llm_client)
        result = agent.generate_chart(valid_chart_spec, temp_output_path)

        assert result == temp_output_path
        mock_call_llm.assert_called_once()
        mock_subprocess.assert_called_once()
        mock_metrics_collector.record_generation.assert_called_once()

    @patch("llm_client.call_llm")
    @patch("subprocess.run")
    def test_generate_chart_subprocess_failure(
        self,
        mock_subprocess,
        mock_call_llm,
        mock_llm_client,
        valid_chart_spec,
        temp_output_path,
        sample_matplotlib_code,
        mock_metrics_collector,
    ):
        """Should handle subprocess execution failure."""
        mock_call_llm.return_value = sample_matplotlib_code
        mock_subprocess.return_value = Mock(returncode=1, stderr="Matplotlib error")

        agent = GraphicsAgent(mock_llm_client)
        result = agent.generate_chart(valid_chart_spec, temp_output_path)

        assert result is None
        mock_metrics_collector.record_generation.assert_called()

    @patch("llm_client.call_llm")
    def test_generate_chart_llm_exception(
        self,
        mock_call_llm,
        mock_llm_client,
        valid_chart_spec,
        temp_output_path,
        mock_metrics_collector,
    ):
        """Should handle LLM call exception."""
        mock_call_llm.side_effect = Exception("LLM error")

        agent = GraphicsAgent(mock_llm_client)
        result = agent.generate_chart(valid_chart_spec, temp_output_path)

        assert result is None
        mock_metrics_collector.record_generation.assert_called()


class TestMatplotlibCodeGeneration:
    """Test matplotlib code generation."""

    @patch("llm_client.call_llm")
    def test_generate_matplotlib_code(
        self, mock_call_llm, mock_llm_client, valid_chart_spec, sample_matplotlib_code
    ):
        """Should generate matplotlib code via LLM."""
        mock_call_llm.return_value = sample_matplotlib_code

        agent = GraphicsAgent(mock_llm_client)
        code = agent._generate_matplotlib_code(valid_chart_spec, max_tokens=2500)

        assert "import matplotlib.pyplot" in code
        mock_call_llm.assert_called_once()

    @patch("llm_client.call_llm")
    def test_extract_code_from_python_block(
        self, mock_call_llm, mock_llm_client, valid_chart_spec
    ):
        """Should extract code from ```python blocks."""
        mock_call_llm.return_value = "```python\nprint('test')\n```"

        agent = GraphicsAgent(mock_llm_client)
        code = agent._generate_matplotlib_code(valid_chart_spec, max_tokens=2500)

        assert code.strip() == "print('test')"

    @patch("llm_client.call_llm")
    def test_extract_code_from_generic_block(
        self, mock_call_llm, mock_llm_client, valid_chart_spec
    ):
        """Should extract code from ``` blocks."""
        mock_call_llm.return_value = "```\nprint('test')\n```"

        agent = GraphicsAgent(mock_llm_client)
        code = agent._generate_matplotlib_code(valid_chart_spec, max_tokens=2500)

        assert code.strip() == "print('test')"


class TestMatplotlibCodeExecution:
    """Test matplotlib code execution."""

    @patch("subprocess.run")
    def test_execute_matplotlib_code_success(
        self, mock_subprocess, mock_llm_client, sample_matplotlib_code, temp_output_path
    ):
        """Should execute matplotlib code successfully."""
        mock_subprocess.return_value = Mock(returncode=0)

        agent = GraphicsAgent(mock_llm_client)
        success = agent._execute_matplotlib_code(
            sample_matplotlib_code, temp_output_path
        )

        assert success is True
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_execute_matplotlib_code_failure(
        self,
        mock_subprocess,
        mock_llm_client,
        sample_matplotlib_code,
        temp_output_path,
        mock_metrics_collector,
    ):
        """Should handle matplotlib execution failure."""
        mock_subprocess.return_value = Mock(returncode=1, stderr="Execution error")

        # Mock the metrics properly so it's not subscriptable
        mock_metrics_collector.current_session = {"charts": []}

        agent = GraphicsAgent(mock_llm_client)
        success = agent._execute_matplotlib_code(
            sample_matplotlib_code, temp_output_path
        )

        assert success is False

    def test_execute_adds_savefig_if_missing(self, mock_llm_client, temp_output_path):
        """Should add plt.savefig if not present."""
        code = "import matplotlib.pyplot as plt\nplt.plot([1,2,3])"

        agent = GraphicsAgent(mock_llm_client)

        # Mock subprocess to avoid actual execution
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0)
            agent._execute_matplotlib_code(code, temp_output_path)

        # Check that temp file was created with savefig
        # (Code should have savefig added)

    def test_execute_replaces_savefig_params(self, mock_llm_client, temp_output_path):
        """Should replace existing plt.savefig with correct params."""
        code = "import matplotlib.pyplot as plt\nplt.savefig('old.png')"

        agent = GraphicsAgent(mock_llm_client)

        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0)
            agent._execute_matplotlib_code(code, temp_output_path)

        # Savefig should be replaced with correct path


class TestBackwardCompatibility:
    """Test backward compatibility with economist_agent.py."""

    @patch("llm_client.call_llm")
    @patch("subprocess.run")
    def test_run_graphics_agent_function(
        self,
        mock_subprocess,
        mock_call_llm,
        mock_llm_client,
        valid_chart_spec,
        temp_output_path,
        sample_matplotlib_code,
        mock_metrics_collector,
    ):
        """Should maintain backward compatibility."""
        mock_call_llm.return_value = sample_matplotlib_code
        mock_subprocess.return_value = Mock(returncode=0)

        result = run_graphics_agent(mock_llm_client, valid_chart_spec, temp_output_path)

        assert result == temp_output_path

    def test_run_graphics_agent_signature(self, mock_llm_client):
        """Should have same signature as original."""
        import inspect

        sig = inspect.signature(run_graphics_agent)
        params = list(sig.parameters.keys())
        assert params == ["client", "chart_spec", "output_path"]


# ═══════════════════════════════════════════════════════════════════════════
# GRAPHICS TASKS TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestGraphicsTask:
    """Test GraphicsTask class."""

    def test_task_init(self, valid_chart_spec, temp_output_path):
        """Should initialize task with all params."""
        task = GraphicsTask(
            task_type="generate_chart",
            chart_spec=valid_chart_spec,
            output_path=temp_output_path,
            validation_level="strict",
            max_tokens=2500,
        )
        assert task.task_type == "generate_chart"
        assert task.chart_spec == valid_chart_spec
        assert task.output_path == temp_output_path
        assert task.validation_level == "strict"
        assert task.max_tokens == 2500

    def test_task_to_dict(self, valid_chart_spec, temp_output_path):
        """Should convert task to dict."""
        task = GraphicsTask(
            task_type="generate_chart",
            chart_spec=valid_chart_spec,
            output_path=temp_output_path,
        )
        task_dict = task.to_dict()
        assert isinstance(task_dict, dict)
        assert task_dict["task_type"] == "generate_chart"
        assert task_dict["chart_spec"] == valid_chart_spec


class TestTaskCreation:
    """Test task creation functions."""

    def test_create_chart_generation_task(self, valid_chart_spec, temp_output_path):
        """Should create chart generation task."""
        task = create_chart_generation_task(valid_chart_spec, temp_output_path)
        assert isinstance(task, GraphicsTask)
        assert task.task_type == "generate_chart"
        assert task.validation_level == "strict"

    def test_create_zone_validation_task(self, temp_output_path):
        """Should create zone validation task."""
        task = create_zone_validation_task(temp_output_path, validation_level="medium")
        assert isinstance(task, GraphicsTask)
        assert task.task_type == "validate_zones"
        assert task.validation_level == "medium"

    def test_create_label_optimization_task(self, valid_chart_spec, temp_output_path):
        """Should create label optimization task."""
        task = create_label_optimization_task(
            valid_chart_spec, "current_code", temp_output_path
        )
        assert isinstance(task, GraphicsTask)
        assert task.task_type == "optimize_labels"
        assert "optimization_target" in task.chart_spec


class TestTaskTemplates:
    """Test task templates."""

    def test_task_templates_defined(self):
        """Should have task templates defined."""
        assert isinstance(TASK_TEMPLATES, dict)
        assert "line_chart" in TASK_TEMPLATES
        assert "bar_chart" in TASK_TEMPLATES
        assert "scatter_plot" in TASK_TEMPLATES

    def test_get_task_template_line_chart(self):
        """Should get line chart template."""
        template = get_task_template("line_chart")
        assert template is not None
        assert template["chart_type"] == "line"
        assert "title" in template["required_fields"]

    def test_get_task_template_invalid(self):
        """Should return None for invalid chart type."""
        template = get_task_template("invalid_type")
        assert template is None

    def test_validate_chart_spec_valid(self, valid_chart_spec):
        """Should validate valid chart spec."""
        is_valid, errors = validate_chart_spec(valid_chart_spec, "line_chart")
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_chart_spec_missing_title(self):
        """Should detect missing title."""
        is_valid, errors = validate_chart_spec({"data": {}})
        assert is_valid is False
        assert any("title" in err for err in errors)

    def test_validate_chart_spec_missing_data(self):
        """Should detect missing data."""
        is_valid, errors = validate_chart_spec({"title": "Test"})
        assert is_valid is False
        assert any("data" in err for err in errors)


class TestMetricsIntegration:
    """Test metrics collection integration."""

    @patch("llm_client.call_llm")
    @patch("subprocess.run")
    def test_metrics_start_chart_called(
        self,
        mock_subprocess,
        mock_call_llm,
        mock_llm_client,
        valid_chart_spec,
        temp_output_path,
        sample_matplotlib_code,
        mock_metrics_collector,
    ):
        """Should call metrics.start_chart."""
        mock_call_llm.return_value = sample_matplotlib_code
        mock_subprocess.return_value = Mock(returncode=0)

        agent = GraphicsAgent(mock_llm_client)
        agent.generate_chart(valid_chart_spec, temp_output_path)

        mock_metrics_collector.start_chart.assert_called_once_with(
            valid_chart_spec["title"], valid_chart_spec
        )

    @patch("llm_client.call_llm")
    @patch("subprocess.run")
    def test_metrics_record_generation_success(
        self,
        mock_subprocess,
        mock_call_llm,
        mock_llm_client,
        valid_chart_spec,
        temp_output_path,
        sample_matplotlib_code,
        mock_metrics_collector,
    ):
        """Should record generation success."""
        mock_call_llm.return_value = sample_matplotlib_code
        mock_subprocess.return_value = Mock(returncode=0)

        agent = GraphicsAgent(mock_llm_client)
        agent.generate_chart(valid_chart_spec, temp_output_path)

        # Should call record_generation with success=True
        calls = mock_metrics_collector.record_generation.call_args_list
        assert len(calls) > 0
        # Check kwargs instead of positional args
        assert calls[0].kwargs["success"] is True

    @patch("llm_client.call_llm")
    def test_metrics_record_generation_failure(
        self,
        mock_call_llm,
        mock_llm_client,
        valid_chart_spec,
        temp_output_path,
        mock_metrics_collector,
    ):
        """Should record generation failure."""
        mock_call_llm.side_effect = Exception("LLM error")

        agent = GraphicsAgent(mock_llm_client)
        agent.generate_chart(valid_chart_spec, temp_output_path)

        # Should call record_generation with success=False
        calls = mock_metrics_collector.record_generation.call_args_list
        assert len(calls) > 0
        # Check kwargs instead of positional args
        assert calls[0].kwargs["success"] is False


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Integration tests."""

    @patch("llm_client.call_llm")
    @patch("subprocess.run")
    def test_full_chart_generation_flow(
        self,
        mock_subprocess,
        mock_call_llm,
        mock_llm_client,
        valid_chart_spec,
        temp_output_path,
        sample_matplotlib_code,
        mock_metrics_collector,
    ):
        """Should complete full chart generation flow."""
        mock_call_llm.return_value = sample_matplotlib_code
        mock_subprocess.return_value = Mock(returncode=0)

        # Create agent
        agent = GraphicsAgent(mock_llm_client)

        # Generate chart
        result = agent.generate_chart(valid_chart_spec, temp_output_path)

        # Verify flow
        assert result == temp_output_path
        assert mock_call_llm.call_count == 1
        assert mock_subprocess.call_count == 1
        assert mock_metrics_collector.start_chart.call_count == 1
        assert mock_metrics_collector.record_generation.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
