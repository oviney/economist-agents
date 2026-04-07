#!/usr/bin/env python3
"""
Publication Validator MCP Server

Exposes the PublicationValidator quality gate as an MCP tool so that any
agent in the content pipeline can validate articles before publication.

Transport: stdio (default FastMCP behaviour)
"""

import logging
import re
import sys
from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP

# Ensure the repo root is on sys.path so the scripts package is importable
# when the server is launched directly (mirrors run.sh behaviour).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.publication_validator import PublicationValidator  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Categories accepted by the publication pipeline.
#: Keep in sync with the ``categories`` enum in ``scripts/schema_validator.py``
#: (``FRONT_MATTER_SCHEMA["properties"]["categories"]["items"]["enum"]``).
VALID_CATEGORIES: list[str] = [
    "quality-engineering",
    "test-automation",
    "performance",
    "ai-testing",
    "software-engineering",
    "devops",
]

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

logger = logging.getLogger(__name__)

mcp = FastMCP("publication-validator")


@mcp.tool()
def validate_for_publication(
    content: str,
    expected_date: str | None = None,
) -> dict:
    """Validate an article against publication quality gates.

    Wraps ``PublicationValidator.validate()`` and returns a structured
    result suitable for consumption by downstream agents.

    Args:
        content: Full article text including YAML front matter.
        expected_date: Expected publication date in ``YYYY-MM-DD`` format.
            Defaults to today's date when omitted.

    Returns:
        A dictionary with the following keys:

        * ``is_valid`` (bool): ``True`` when no CRITICAL issues were found.
        * ``issues`` (list[dict]): Zero or more issue dictionaries, each
          containing at minimum ``check``, ``severity``, and ``message``
          keys as produced by :class:`~scripts.publication_validator.PublicationValidator`.
    """
    logger.info(
        "validate_for_publication called: expected_date=%s, content_length=%d",
        expected_date,
        len(content),
    )

    validator = PublicationValidator(expected_date=expected_date)
    try:
        is_valid, issues = validator.validate(content)
    except Exception as exc:
        logger.exception("validate_for_publication failed: %s", exc)
        return {
            "is_valid": False,
            "issues": [
                {
                    "check": "validator_error",
                    "severity": "CRITICAL",
                    "message": str(exc),
                }
            ],
        }

    logger.info(
        "Validation complete: is_valid=%s, issue_count=%d", is_valid, len(issues)
    )

    return {"is_valid": is_valid, "issues": issues}


@mcp.tool()
def validate_post(post_path: str) -> dict:
    """Validate a blog-post file against publication front-matter requirements.

    Reads the markdown file at *post_path* and checks:

    * YAML front-matter delimiters are present (``---`` … ``---``).
    * Required fields are present: ``layout``, ``title``, ``date``,
      ``author``, ``categories``, ``image``.
    * ``layout`` equals ``"post"``.
    * ``title`` is a non-empty string.
    * ``date`` matches ``YYYY-MM-DD`` format.
    * ``author`` is a non-empty string.
    * Every item in ``categories`` is one of :data:`VALID_CATEGORIES`.
    * ``image`` refers to a path that exists on the filesystem (local paths
      only; ``http://`` / ``https://`` URLs are accepted without checking).

    Args:
        post_path: Absolute or relative path to the markdown post file.

    Returns:
        A dictionary with three keys:

        * ``valid`` (bool): ``True`` when *errors* is empty.
        * ``errors`` (list[str]): Fatal validation failures; the post must
          be fixed before publication.
        * ``warnings`` (list[str]): Non-fatal advisories.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ------------------------------------------------------------------
    # Read the file
    # ------------------------------------------------------------------
    post_file = Path(post_path)
    try:
        content = post_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "valid": False,
            "errors": [f"File not found: {post_path}"],
            "warnings": [],
        }
    except OSError as exc:
        return {
            "valid": False,
            "errors": [f"Error reading file: {exc}"],
            "warnings": [],
        }

    logger.info("validate_post: reading %s (%d bytes)", post_path, len(content))

    # ------------------------------------------------------------------
    # Front-matter delimiters
    # ------------------------------------------------------------------
    if not content.lstrip("\n").startswith("---"):
        errors.append("Missing YAML front-matter opening delimiter (---)")
        return {"valid": False, "errors": errors, "warnings": warnings}

    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append("Missing YAML front-matter closing delimiter (---)")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # ------------------------------------------------------------------
    # Parse YAML
    # ------------------------------------------------------------------
    try:
        frontmatter: dict = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        errors.append(f"Invalid YAML in front matter: {exc}")
        return {"valid": False, "errors": errors, "warnings": warnings}

    if not isinstance(frontmatter, dict):
        errors.append("Front matter must be a YAML dictionary")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # ------------------------------------------------------------------
    # Required fields
    # ------------------------------------------------------------------
    required_fields = ["layout", "title", "date", "author", "categories", "image"]
    for field in required_fields:
        if field not in frontmatter:
            errors.append(f"Missing required field: {field}")

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    # ------------------------------------------------------------------
    # layout
    # ------------------------------------------------------------------
    layout = frontmatter.get("layout")
    if layout != "post":
        errors.append(f"layout must be 'post', got '{layout}'")

    # ------------------------------------------------------------------
    # title
    # ------------------------------------------------------------------
    title = frontmatter.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("title must be a non-empty string")

    # ------------------------------------------------------------------
    # date (YYYY-MM-DD)
    # ------------------------------------------------------------------
    date_val = frontmatter.get("date")
    date_str = (
        date_val.strftime("%Y-%m-%d")
        if hasattr(date_val, "strftime")
        else str(date_val)
    )
    if not _DATE_RE.match(date_str):
        errors.append(f"date must be in YYYY-MM-DD format, got '{date_str}'")

    # ------------------------------------------------------------------
    # author
    # ------------------------------------------------------------------
    author = frontmatter.get("author")
    if not isinstance(author, str) or not author.strip():
        errors.append("author must be a non-empty string")

    # ------------------------------------------------------------------
    # categories — each must be in VALID_CATEGORIES
    # ------------------------------------------------------------------
    categories = frontmatter.get("categories")
    if not isinstance(categories, list):
        errors.append("categories must be a list")
    elif not categories:
        errors.append("categories must contain at least one entry")
    else:
        for cat in categories:
            if cat not in VALID_CATEGORIES:
                errors.append(
                    f"Invalid category '{cat}'. "
                    f"Must be one of: {', '.join(VALID_CATEGORIES)}"
                )

    # ------------------------------------------------------------------
    # image — local paths must exist on the filesystem
    # ------------------------------------------------------------------
    image = frontmatter.get("image")
    if image is None or (isinstance(image, str) and not image.strip()):
        errors.append("image field must be a non-empty value")
    else:
        image_str = str(image).strip()
        if not image_str.startswith(("http://", "https://")):
            image_path = Path(image_str)
            # Check candidates in priority order:
            # 1. As-is:            /abs/path/chart.png → /abs/path/chart.png
            # 2. Repo-root-rel:    /assets/chart.png   → <repo_root>/assets/chart.png
            # 3. Post-dir-rel:     chart.png           → <post_dir>/chart.png
            candidates = [
                image_path,
                _REPO_ROOT / image_str.lstrip("/"),
                post_file.parent / image_str.lstrip("/"),
            ]
            if not any(c.exists() for c in candidates):
                errors.append(f"image path does not exist: {image_str}")

    logger.info(
        "validate_post: %s — %d error(s), %d warning(s)",
        post_path,
        len(errors),
        len(warnings),
    )

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


if __name__ == "__main__":
    mcp.run(transport="stdio")
