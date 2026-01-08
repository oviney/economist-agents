#!/usr/bin/env python3
"""
Style Memory Tool - RAG-based Style Pattern Retrieval

Provides Editor Agent with concrete style examples from Gold Standard articles
for GATE 3 (VOICE) enhancement. Uses ChromaDB vector store for efficient
similarity search.

Features:
- Vector store populated from archived/*.md articles
- Query latency <500ms for real-time Editor feedback
- Graceful degradation when archive is empty
- Relevance scoring (>0.7 threshold for top results)

Usage:
    from src.tools.style_memory_tool import StyleMemoryTool

    tool = StyleMemoryTool()
    results = tool.query("How to handle banned phrases?")
    for result in results:
        print(result["text"], result["score"])
"""

from pathlib import Path
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️  ChromaDB not installed. Style Memory Tool in fallback mode.")


class StyleMemoryTool:
    """
    RAG-based style pattern retrieval for Editor Agent GATE 3 enhancement.

    Graceful Degradation:
    - If ChromaDB unavailable: returns empty results with warning
    - If archive empty: returns empty results but maintains API contract
    - If query fails: catches exceptions, returns empty list
    """

    def __init__(
        self,
        archive_path: str | Path = "archived",
        collection_name: str = "economist_style_patterns",
        persist_directory: str = ".chromadb",
    ):
        """
        Initialize Style Memory Tool with vector store.

        Args:
            archive_path: Path to archived/ directory with Gold Standard articles
            collection_name: ChromaDB collection name
            persist_directory: ChromaDB persistence directory
        """
        self.archive_path = Path(archive_path)
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self.indexed_count = 0

        if not CHROMADB_AVAILABLE:
            print("⚠️  ChromaDB unavailable - Style Memory Tool disabled")
            return

        try:
            # Initialize ChromaDB client with persistence
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "description": "Economist style patterns from Gold Standard articles"
                },
            )

            # Index archived articles if collection is empty
            if self.collection.count() == 0:
                self._index_archive()
            else:
                self.indexed_count = self.collection.count()
                print(f"✅ Style Memory loaded: {self.indexed_count} patterns indexed")

        except Exception as e:
            print(f"⚠️  Style Memory Tool initialization failed: {e}")
            self.client = None
            self.collection = None

    def _index_archive(self) -> None:
        """
        Index all markdown articles from archived/ directory.

        Graceful degradation: If archive is empty, continues without error.
        """
        if not self.archive_path.exists():
            print(f"ℹ️  Archive directory not found: {self.archive_path}")
            return

        # Find all markdown files
        md_files = list(self.archive_path.glob("**/*.md"))
        if not md_files:
            print(f"ℹ️  No Gold Standard articles found in {self.archive_path}")
            return

        print(f"📚 Indexing {len(md_files)} Gold Standard articles...")

        documents = []
        metadatas = []
        ids = []

        for _idx, md_file in enumerate(md_files):
            try:
                content = md_file.read_text(encoding="utf-8")

                # Skip empty files or README
                if len(content) < 100 or md_file.name.lower() == "readme.md":
                    continue

                # Extract chunks (by paragraph for better granularity)
                paragraphs = [
                    p.strip() for p in content.split("\n\n") if len(p.strip()) > 50
                ]

                for para_idx, paragraph in enumerate(paragraphs):
                    doc_id = f"{md_file.stem}_p{para_idx}"
                    documents.append(paragraph)
                    metadatas.append(
                        {
                            "source": md_file.name,
                            "paragraph": para_idx,
                            "path": str(md_file),
                        }
                    )
                    ids.append(doc_id)

            except Exception as e:
                print(f"⚠️  Failed to index {md_file.name}: {e}")
                continue

        if documents:
            try:
                self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
                self.indexed_count = len(documents)
                print(
                    f"✅ Indexed {self.indexed_count} style patterns from {len(md_files)} articles"
                )
            except Exception as e:
                print(f"❌ Failed to add documents to ChromaDB: {e}")
        else:
            print("ℹ️  No valid content found to index")

    def query(
        self,
        query_text: str,
        n_results: int = 3,
        min_score: float = 0.7,
    ) -> list[dict[str, Any]]:
        """
        Query vector store for relevant style patterns.

        Args:
            query_text: Natural language query (e.g., "How to handle banned phrases?")
            n_results: Number of results to return
            min_score: Minimum relevance score (0-1 scale, <0.7 filtered out)

        Returns:
            List of dicts with keys: text, score, source, paragraph

        Example:
            results = tool.query("banned phrases examples")
            for result in results:
                print(f"Score: {result['score']:.2f}")
                print(f"Source: {result['source']}")
                print(f"Text: {result['text'][:100]}...")
        """
        # Graceful degradation: return empty if tool unavailable
        if not self.collection:
            return []

        if not query_text.strip():
            return []

        try:
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query_text], n_results=n_results
            )

            # Format results
            formatted_results = []
            if results and results["documents"] and results["documents"][0]:
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                distances = (
                    results["distances"][0]
                    if "distances" in results
                    else [0] * len(documents)
                )

                for doc, metadata, distance in zip(documents, metadatas, distances, strict=False):
                    # Convert distance to similarity score (1 - distance)
                    # ChromaDB uses L2 distance, so lower is better
                    score = 1.0 - min(distance, 1.0)

                    # Filter by min_score threshold
                    if score >= min_score:
                        formatted_results.append(
                            {
                                "text": doc,
                                "score": round(score, 3),
                                "source": metadata.get("source", "unknown"),
                                "paragraph": metadata.get("paragraph", 0),
                            }
                        )

            return formatted_results

        except Exception as e:
            print(f"⚠️  Style Memory query failed: {e}")
            return []

    def get_stats(self) -> dict[str, Any]:
        """
        Get Style Memory Tool statistics.

        Returns:
            dict: {
                "available": bool,
                "indexed_count": int,
                "collection_name": str
            }
        """
        return {
            "available": self.collection is not None,
            "indexed_count": self.indexed_count,
            "collection_name": self.collection_name if self.collection else None,
        }


# CrewAI Tool wrapper for integration with Stage4Crew
def create_style_memory_tool():
    """
    Factory function to create CrewAI-compatible tool.

    Returns:
        Callable tool function for CrewAI Agent
    """
    tool = StyleMemoryTool()

    def style_query(query: str) -> str:
        """
        Query Style Memory for relevant style patterns.

        Args:
            query: Natural language query about style patterns

        Returns:
            Formatted string with top 3 relevant style examples
        """
        results = tool.query(query, n_results=3)

        if not results:
            return (
                "No relevant style patterns found. Use established style guide rules."
            )

        output = ["**Style Memory Results:**\n"]
        for idx, result in enumerate(results, 1):
            output.append(
                f"{idx}. (Score: {result['score']:.2f}, Source: {result['source']})"
            )
            output.append(f"   {result['text'][:200]}...")
            output.append("")

        return "\n".join(output)

    return style_query


if __name__ == "__main__":
    """CLI test for Style Memory Tool"""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║ STYLE MEMORY TOOL - RAG-based Style Pattern Retrieval          ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")

    tool = StyleMemoryTool()
    stats = tool.get_stats()

    print(f"Status: {'✅ Available' if stats['available'] else '❌ Unavailable'}")
    print(f"Indexed Patterns: {stats['indexed_count']}")
    print(f"Collection: {stats['collection_name']}\n")

    if stats["available"] and stats["indexed_count"] > 0:
        # Test query
        print("Test Query: 'banned phrases examples'")
        results = tool.query("banned phrases examples")

        if results:
            print(f"\nFound {len(results)} relevant patterns:\n")
            for idx, result in enumerate(results, 1):
                print(
                    f"{idx}. Score: {result['score']:.2f} | Source: {result['source']}"
                )
                print(f"   {result['text'][:150]}...\n")
        else:
            print(
                "No results found (may need more specific query or lower min_score)\n"
            )
    else:
        print(
            "⚠️  Tool not fully operational (check archive and ChromaDB installation)\n"
        )
