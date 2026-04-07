#!/usr/bin/env python3
"""Index Published Articles — Backfill ChromaDB ``published_articles`` collection.

Fetches the blog's Jekyll search.json feed and upserts each article into the
``published_articles`` ChromaDB collection so that the Topic Scout can detect
duplicate topics before publishing.

The collection uses cosine distance so that similarity scores computed by
:class:`scripts.article_archive.ArticleArchive` remain consistent.

Usage::

    python scripts/index_published_articles.py \\
        --source https://viney.ca/search.json

    python scripts/index_published_articles.py \\
        --source /path/to/search.json \\
        --db .chromadb
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Any

import orjson
import requests

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:  # pragma: no cover
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not installed. Cannot index articles.")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLLECTION_NAME = "published_articles"
DEFAULT_SOURCE = "https://viney.ca/search.json"

# Sentinel: use ChromaDB's built-in embedding function (all-MiniLM-L6-v2)
_USE_DEFAULT_EF = object()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc_id(url: str) -> str:
    """Derive a stable, URL-safe ChromaDB document ID from an article URL.

    Strips the protocol and host so that the same article is always assigned
    the same ID regardless of whether it is referenced by a full URL or a
    root-relative path.

    Args:
        url: Article URL, e.g. ``"/2026-04-01-my-post/"`` or
             ``"https://viney.ca/2026-04-01-my-post/"``.

    Returns:
        A non-empty string that is safe to use as a ChromaDB document ID.
        Falls back to ``"unknown"`` when *url* is blank.
    """
    if not url:
        return "unknown"
    # Remove scheme + host
    path = re.sub(r"^https?://[^/]+", "", url)
    # Replace every non-alphanumeric character (except - and _) with _
    doc_id = re.sub(r"[^a-zA-Z0-9_-]", "_", path).strip("_")
    return doc_id or "unknown"


def _categories_to_str(categories: Any) -> str:
    """Normalise a categories value to a comma-separated string.

    Args:
        categories: A string, list, or other value from the JSON feed.

    Returns:
        Comma-separated string, e.g. ``"testing,ai"``.
    """
    if isinstance(categories, list):
        return ",".join(str(c) for c in categories)
    return str(categories) if categories is not None else ""


# ---------------------------------------------------------------------------
# Feed fetching
# ---------------------------------------------------------------------------


def fetch_search_json(source: str) -> list[dict[str, Any]]:
    """Fetch and parse the Jekyll search.json from a URL or local file path.

    Args:
        source: URL (``https://…``) or local file-system path to
                ``search.json``.

    Returns:
        List of article dicts parsed from the JSON array.

    Raises:
        ValueError: If the parsed JSON is not an array.
        requests.HTTPError: If an HTTP request returns a non-2xx status.
        json.JSONDecodeError: If the response body is not valid JSON.
        OSError: If a local file cannot be read.
    """
    if source.startswith("http://") or source.startswith("https://"):
        logger.info("Fetching search.json from %s", source)
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        data = response.json()
    else:
        path = Path(source)
        logger.info("Loading search.json from %s", path)
        with path.open("rb") as fh:
            data = orjson.loads(fh.read())

    if not isinstance(data, list):
        raise ValueError(
            f"Expected a JSON array at {source!r}, got {type(data).__name__}"
        )

    return data


# ---------------------------------------------------------------------------
# ChromaDB collection access
# ---------------------------------------------------------------------------


def _get_collection(
    persist_directory: str = ".chromadb",
    *,
    _client: Any = None,
    _embedding_function: Any = _USE_DEFAULT_EF,
) -> Any:
    """Return (or create) the ``published_articles`` ChromaDB collection.

    Args:
        persist_directory: Path to the ChromaDB persistence directory.
            Ignored when *_client* is supplied.
        _client: Optional pre-built ChromaDB client (e.g. ``EphemeralClient``
            for tests).  When supplied *persist_directory* is ignored.
        _embedding_function: Optional embedding function.  Pass ``None`` to
            force ChromaDB's built-in default.  Primarily used in tests to
            inject an offline-capable function so that no network access is
            required.

    Returns:
        A ChromaDB ``Collection`` object.

    Raises:
        RuntimeError: If ChromaDB is not installed.
    """
    if not CHROMADB_AVAILABLE:  # pragma: no cover
        raise RuntimeError("ChromaDB is not installed. Run: pip install chromadb")

    client = _client
    if client is None:
        client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )

    collection_kwargs: dict[str, Any] = {
        "name": COLLECTION_NAME,
        "metadata": {
            "description": (
                "Published blog articles indexed from search.json "
                "for topic duplicate detection"
            ),
            "hnsw:space": "cosine",
        },
    }
    if _embedding_function is not _USE_DEFAULT_EF:
        collection_kwargs["embedding_function"] = _embedding_function

    return client.get_or_create_collection(**collection_kwargs)


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------


def index_articles(
    articles: list[dict[str, Any]],
    collection: Any,
) -> dict[str, int]:
    """Upsert a list of articles into the ChromaDB collection.

    Each article is stored as a single document whose text is
    ``"<title>\\n\\n<summary>"``.  The document ID is derived from the
    article's ``url`` field so that re-indexing the same article is
    idempotent (ChromaDB ``upsert`` replaces existing documents with the
    same ID).

    Articles that have neither a ``title`` nor a ``url`` are skipped.

    Args:
        articles: List of article dicts, typically parsed from
                  ``search.json``.  Recognised keys: ``title``, ``url``,
                  ``date``, ``categories``, ``excerpt``, ``description``,
                  ``content``.
        collection: A ChromaDB ``Collection`` to upsert into.

    Returns:
        A dict with ``"indexed"`` (number of articles upserted) and
        ``"skipped"`` (number of articles that were skipped due to missing
        data or errors).
    """
    indexed = 0
    skipped = 0

    for item in articles:
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        date = str(item.get("date") or "").strip()
        categories = _categories_to_str(item.get("categories"))

        # Summary: prefer excerpt, then description, then truncated content
        summary = (
            str(item.get("excerpt") or item.get("description") or "").strip()
            or str(item.get("content") or "")[:200].strip()
        )

        if not title and not url:
            logger.debug("Skipping article with no title or URL")
            skipped += 1
            continue

        doc_id = _make_doc_id(url) if url else re.sub(r"[^a-zA-Z0-9_-]", "_", title)
        document_text = f"{title}\n\n{summary}" if summary else title

        metadata: dict[str, str] = {
            "title": title,
            "url": url,
            "date": date,
            "categories": categories,
            "summary": summary,
        }

        try:
            collection.upsert(
                documents=[document_text],
                metadatas=[metadata],
                ids=[doc_id],
            )
            indexed += 1
            logger.debug("Upserted: %s (id=%s)", title, doc_id)
        except Exception as exc:
            logger.warning("Failed to upsert '%s': %s", title, exc)
            skipped += 1

    return {"indexed": indexed, "skipped": skipped}


# ---------------------------------------------------------------------------
# High-level entry point
# ---------------------------------------------------------------------------


def run(
    source: str = DEFAULT_SOURCE,
    persist_directory: str = ".chromadb",
    *,
    _client: Any = None,
    _embedding_function: Any = _USE_DEFAULT_EF,
) -> dict[str, int]:
    """Fetch search.json and index all articles into ChromaDB.

    This is the main programmatic entry point.  It orchestrates
    :func:`fetch_search_json`, :func:`_get_collection`, and
    :func:`index_articles`.

    Args:
        source: URL or local file path to ``search.json``.
        persist_directory: ChromaDB persistence directory.
        _client: Optional pre-built ChromaDB client (for testing).
        _embedding_function: Optional embedding function (for testing).

    Returns:
        A dict with ``"indexed"`` and ``"skipped"`` article counts.

    Raises:
        RuntimeError: If ChromaDB is not installed.
        requests.HTTPError: If the HTTP request fails.
        ValueError: If the JSON is not an array.
    """
    articles = fetch_search_json(source)
    logger.info("Found %d articles in search.json", len(articles))

    collection = _get_collection(
        persist_directory,
        _client=_client,
        _embedding_function=_embedding_function,
    )
    result = index_articles(articles, collection)

    logger.info(
        "Indexing complete — %d indexed, %d skipped (collection total: %d)",
        result["indexed"],
        result["skipped"],
        collection.count(),
    )
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Command-line entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        description=(
            "Index published blog articles into the ChromaDB "
            "'published_articles' collection."
        )
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="URL or file path to the Jekyll search.json (default: %(default)s)",
    )
    parser.add_argument(
        "--db",
        default=".chromadb",
        dest="db",
        help="ChromaDB persistence directory (default: %(default)s)",
    )
    args = parser.parse_args()

    try:
        result = run(source=args.source, persist_directory=args.db)
        logger.info(
            "✅ Indexed %d articles (%d skipped)",
            result["indexed"],
            result["skipped"],
        )
    except Exception as exc:
        logger.error("Indexing failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
