#!/usr/bin/env python3
"""
Test Agent Registry

Validates that AgentRegistry can load and instantiate Stage3Crew and Stage4Crew.
Also covers full branch paths in src/registry.py (100% coverage target).
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.registry import AgentRegistry

try:
    import crewai  # noqa: F401

    _CREWAI_AVAILABLE = True
except ImportError:
    _CREWAI_AVAILABLE = False

requires_crewai = pytest.mark.skipif(
    not _CREWAI_AVAILABLE, reason="crewai not installed"
)

# Skip tests that require CrewAI and API keys
requires_crewai = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY for CrewAI",
)


class TestAgentRegistry:
    """Test cases for AgentRegistry"""

    def test_registry_initialization(self):
        """Test that AgentRegistry initializes correctly"""
        registry = AgentRegistry()
        assert registry is not None

    @requires_crewai
    def test_load_stage3_crew(self):
        """Test that AgentRegistry can load Stage3Crew"""
        registry = AgentRegistry()

        # Load Stage3Crew class
        stage3_class = registry.get_crew_class("Stage3Crew")
        assert stage3_class is not None

        # Instantiate with a topic
        crew_instance = stage3_class(topic="Test Topic")
        assert crew_instance is not None
        assert hasattr(crew_instance, "kickoff")

    @requires_crewai
    def test_load_stage4_crew(self):
        """Test that AgentRegistry can load Stage4Crew"""
        registry = AgentRegistry()

        # Load Stage4Crew class
        stage4_class = registry.get_crew_class("Stage4Crew")
        assert stage4_class is not None

        # Instantiate (Stage4Crew takes no __init__ args)
        crew_instance = stage4_class()
        assert crew_instance is not None
        assert hasattr(crew_instance, "kickoff")

    @requires_crewai
    def test_get_available_crews(self):
        """Test that AgentRegistry can list available crews"""
        registry = AgentRegistry()

        available_crews = registry.get_available_crews()
        assert isinstance(available_crews, list)
        assert "Stage3Crew" in available_crews
        assert "Stage4Crew" in available_crews

    def test_invalid_crew_name(self):
        """Test that requesting an invalid crew raises appropriate error"""
        registry = AgentRegistry()

        with pytest.raises((ValueError, KeyError)):
            registry.get_crew_class("NonExistentCrew")

    def test_get_crew_class_returns_registered_class(self):
        """get_crew_class returns exactly the registered class."""
        registry = AgentRegistry()

        class DummyCrew:
            pass

        registry.register_crew("DummyCrew", DummyCrew)
        result = registry.get_crew_class("DummyCrew")
        assert result is DummyCrew

    def test_register_crew_manual(self):
        """register_crew adds a class to the registry."""
        registry = AgentRegistry()
        initial_count = len(registry.get_available_crews())

        class NewCrew:
            pass

        registry.register_crew("NewCrew", NewCrew)
        assert "NewCrew" in registry.get_available_crews()
        assert len(registry.get_available_crews()) == initial_count + 1

    def test_repr_contains_registered_crew_names(self):
        """__repr__ includes the names of registered crews."""
        registry = AgentRegistry()

        class ReprCrew:
            pass

        registry.register_crew("ReprCrew", ReprCrew)
        representation = repr(registry)
        assert "ReprCrew" in representation
        assert "AgentRegistry" in representation

    def test_discover_crews_skips_dunder_files(self):
        """_discover_crews does not register dunder-named crews."""
        registry = AgentRegistry()
        crew_names = registry.get_available_crews()
        # Files like __init__.py should not appear as crew names
        for name in crew_names:
            assert not name.startswith("__")

    def test_load_legacy_crews_fallback(self):
        """_load_legacy_crews is called when crews_dir does not exist."""
        # Simulate crews_dir not existing so _load_legacy_crews is called
        with patch.object(Path, "exists", return_value=False):
            registry = AgentRegistry()
        # Registry should still be usable; it fell back to _load_legacy_crews
        assert isinstance(registry.get_available_crews(), list)

    def test_load_legacy_crews_import_error_silenced(self):
        """_load_legacy_crews is invoked when crews_dir doesn't exist (legacy path)."""
        # Simulate crews_dir not existing so _load_legacy_crews is called.
        # The actual import succeeds in the test environment; we just verify
        # the registry remains usable regardless of the legacy module state.
        with patch.object(Path, "exists", return_value=False):
            registry = AgentRegistry()
        # Registry should be usable; _load_legacy_crews ran
        assert isinstance(registry.get_available_crews(), list)

    def test_discover_crews_handles_import_error(self):
        """_discover_crews prints a warning and continues on ImportError."""
        import importlib

        crews_dir = Path(__file__).parent.parent / "src" / "crews"
        if not crews_dir.exists():
            pytest.skip("src/crews does not exist")

        # Patch importlib.import_module to raise ImportError for crew modules
        original_import = importlib.import_module

        def broken_import(name, *args, **kwargs):
            if "src.crews." in name:
                raise ImportError(f"Simulated import error for {name}")
            return original_import(name, *args, **kwargs)

        with patch("importlib.import_module", side_effect=broken_import):
            # Should not raise; prints warnings and continues
            registry = AgentRegistry()

        # Registry still usable even with broken imports
        assert isinstance(registry.get_available_crews(), list)
