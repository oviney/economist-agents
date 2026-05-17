"""Adapter module bridging scripts/ legacy modules into src/ namespace.

Centralises the sys.path manipulation so that flow.py can import
topic_scout, editorial_board, publication_validator, and llm_client
without scattering path hacks across the codebase.
"""

import sys
from pathlib import Path

_scripts_dir = str(Path(__file__).parent.parent.parent / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from scripts.editorial_board import run_editorial_board  # noqa: E402
from scripts.featured_image_agent import generate_featured_image  # noqa: E402
from scripts.llm_client import create_llm_client  # noqa: E402
from scripts.publication_validator import PublicationValidator  # noqa: E402
from scripts.topic_scout import scout_topics  # noqa: E402

__all__ = [
    "PublicationValidator",
    "create_llm_client",
    "generate_featured_image",
    "run_editorial_board",
    "scout_topics",
]
