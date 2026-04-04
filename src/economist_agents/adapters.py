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

from editorial_board import run_editorial_board  # noqa: E402
from llm_client import create_llm_client  # noqa: E402
from publication_validator import PublicationValidator  # noqa: E402
from topic_scout import scout_topics  # noqa: E402

__all__ = [
    "create_llm_client",
    "run_editorial_board",
    "scout_topics",
    "PublicationValidator",
]
