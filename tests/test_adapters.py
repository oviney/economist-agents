"""Coverage tests for ``src.economist_agents.adapters``.

The adapters module bridges ``scripts/`` legacy modules into the ``src/``
namespace via a ``sys.path`` mutation. Because the imports happen at module
load time, a rename or relocation of any wrapped script silently breaks the
production path used by ``flow.py``.

These tests pin the contract: importing the adapter module must succeed and
each of the five exported names must resolve to a callable or class. The
tests are intentionally lightweight — they touch no network, no LLMs and no
environment variables.

Related issue: https://github.com/oviney/economist-agents/issues/338
"""

from __future__ import annotations

import importlib
import inspect


def test_adapters_module_imports_without_error() -> None:
    """The adapter module must import cleanly.

    Failure here means the ``sys.path`` mutation or one of the five wrapped
    script imports broke (rename, relocation, or syntax error in a script).
    """
    module = importlib.import_module("src.economist_agents.adapters")
    assert module is not None


def test_create_llm_client_is_callable() -> None:
    """``create_llm_client`` must be exported as a callable factory."""
    from src.economist_agents.adapters import create_llm_client

    assert callable(create_llm_client)


def test_generate_featured_image_is_callable() -> None:
    """``generate_featured_image`` must be exported as a callable."""
    from src.economist_agents.adapters import generate_featured_image

    assert callable(generate_featured_image)


def test_run_editorial_board_is_callable() -> None:
    """``run_editorial_board`` must be exported as a callable."""
    from src.economist_agents.adapters import run_editorial_board

    assert callable(run_editorial_board)


def test_scout_topics_is_callable() -> None:
    """``scout_topics`` must be exported as a callable."""
    from src.economist_agents.adapters import scout_topics

    assert callable(scout_topics)


def test_publication_validator_is_class() -> None:
    """``PublicationValidator`` must be exported as a class."""
    from src.economist_agents.adapters import PublicationValidator

    assert inspect.isclass(PublicationValidator)


def test_adapters_all_exports_resolve() -> None:
    """Every name in ``__all__`` must resolve on the module.

    Guards against ``__all__`` drift — e.g. a name removed from the import
    block but left in ``__all__``, or vice versa.
    """
    module = importlib.import_module("src.economist_agents.adapters")
    expected = {
        "PublicationValidator",
        "create_llm_client",
        "generate_featured_image",
        "run_editorial_board",
        "scout_topics",
    }
    assert set(module.__all__) == expected
    for name in expected:
        assert hasattr(module, name), f"adapters.{name} is missing"
