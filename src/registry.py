#!/usr/bin/env python3
"""
Agent Registry

Provides centralized registry for loading and managing CrewAI crew classes.
Enables dynamic crew discovery and instantiation for multi-stage article generation.
"""

import importlib
from pathlib import Path
from typing import Any


class AgentRegistry:
    """
    Central registry for managing CrewAI crew classes.

    Responsibilities:
    - Discover available crew classes from src/crews/
    - Load crew classes dynamically by name
    - Provide metadata about registered crews

    Usage:
        registry = AgentRegistry()
        stage3_class = registry.get_crew_class("Stage3Crew")
        crew = stage3_class(topic="AI Testing")
        result = crew.kickoff()
    """

    def __init__(self):
        """Initialize registry and discover available crews"""
        self._crews = {}
        self._discover_crews()

    def _discover_crews(self):
        """
        Discover all crew classes in src/crews/ directory.

        Convention: Each crew file should contain a class matching its filename.
        Example: src/crews/stage3_crew.py contains Stage3Crew class.
        """
        crews_dir = Path(__file__).parent.parent / "src" / "crews"

        if not crews_dir.exists():
            # Fallback: try loading from src/stage3_crew.py (legacy location)
            self._load_legacy_crews()
            return

        # Scan crews directory for Python files
        for crew_file in crews_dir.glob("*_crew.py"):
            if crew_file.name.startswith("__"):
                continue

            module_name = crew_file.stem  # e.g., "stage3_crew"
            class_name = self._module_to_class_name(module_name)  # e.g., "Stage3Crew"

            try:
                # Import module dynamically
                module = importlib.import_module(f"src.crews.{module_name}")

                # Get class from module
                if hasattr(module, class_name):
                    crew_class = getattr(module, class_name)
                    self._crews[class_name] = crew_class
            except ImportError as e:
                print(f"Warning: Could not import {module_name}: {e}")
                continue

    def _load_legacy_crews(self):
        """
        Load crews from legacy src/stage3_crew.py location.
        Supports backward compatibility during migration.
        """
        try:
            from src.stage3_crew import Stage3Crew

            self._crews["Stage3Crew"] = Stage3Crew
        except ImportError:
            pass

    def _module_to_class_name(self, module_name: str) -> str:
        """
        Convert module name to class name.

        Examples:
            stage3_crew -> Stage3Crew
            stage4_crew -> Stage4Crew
            research_crew -> ResearchCrew
        """
        parts = module_name.split("_")
        return "".join(part.capitalize() for part in parts)

    def get_crew_class(self, crew_name: str) -> type[Any]:
        """
        Get crew class by name.

        Args:
            crew_name: Name of crew class (e.g., "Stage3Crew")

        Returns:
            Crew class type

        Raises:
            KeyError: If crew name not found in registry
        """
        if crew_name not in self._crews:
            available = ", ".join(self._crews.keys())
            raise KeyError(
                f"Crew '{crew_name}' not found in registry. "
                f"Available crews: {available}"
            )

        return self._crews[crew_name]

    def get_available_crews(self) -> list[str]:
        """
        Get list of all registered crew names.

        Returns:
            List of crew names (e.g., ["Stage3Crew", "Stage4Crew"])
        """
        return list(self._crews.keys())

    def register_crew(self, crew_name: str, crew_class: type[Any]):
        """
        Manually register a crew class.

        Useful for testing or registering external crews.

        Args:
            crew_name: Name for the crew (e.g., "CustomCrew")
            crew_class: Crew class type
        """
        self._crews[crew_name] = crew_class

    def __repr__(self) -> str:
        """String representation showing registered crews"""
        crew_list = ", ".join(self._crews.keys())
        return f"AgentRegistry(crews=[{crew_list}])"
