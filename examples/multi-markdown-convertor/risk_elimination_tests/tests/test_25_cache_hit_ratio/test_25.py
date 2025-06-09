#!/usr/bin/env python3
"""
Test 25: Cache hit ratio exceeds 70% with SHA-256 of input chunk
Deduplicate 100 similar docs
"""

import json
import sys
import hashlib
import tempfile
import random
from pathlib import Path
from typing import Dict, Any, List, Set


def generate_similar_documents(
    num_docs: int = 100, base_content: str = None
) -> List[str]:
    """
    Generate a set of similar documents with some variations.

    Args:
        num_docs: Number of documents to generate
        base_content: Base content to vary (if None, uses default)

    Returns:
        List of document contents
    """
    if base_content is None:
        base_content = """
        This is a sample document for testing cache hit ratios in document processing.
        The document contains standard business content that might be found in
        corporate reports, technical documentation, or academic papers.
        
        Key sections include:
        - Executive Summary
        - Introduction and Background
        - Methodology and Approach
        - Results and Analysis
        - Conclusions and Recommendations
        
        This content is designed to be similar across multiple documents
        while allowing for variations that test deduplication algorithms.
        """

    documents = []

    # Create variations of the base document
    variations = [
        "Executive Summary",
        "Introduction and Background",
        "Methodology and Approach",
        "Results and Analysis",
        "Conclusions and Recommendations",
        "Appendix A: Additional Data",
        "Appendix B: Technical Details",
        "References and Citations",
    ]

    for i in range(num_docs):
        # Start with base content
        doc_content = base_content

        # Add document-specific header
        doc_content = f"Document {i + 1:03d}\n{'=' * 20}\n" + doc_content

        # Randomly add some sections
        num_sections = random.randint(2, 5)
        selected_sections = random.sample(variations, num_sections)

        for section in selected_sections:
            section_content = f"\n\n{section}\n{'-' * len(section)}\n"
            section_content += f"This section contains specific information for {section.lower()}. "
            section_content += (
                f"Document {i + 1} includes detailed analysis and findings. "
            )
            section_content += "The content varies slightly between documents to simulate real-world scenarios."
            doc_content += section_content

        # Add some random variation to create different chunks
        if i % 10 == 0:  # Every 10th document gets significant changes
            doc_content += f"\n\nSpecial Note for Document {i + 1}:\n"
            doc_content += "This document contains unique information not found in other documents."
        elif i % 5 == 0:  # Every 5th document gets minor changes
            doc_content += f"\n\nNote: Document {i + 1} revision date: 2024-01-{(i % 28) + 1:02d}"

        documents.append(doc_content)

    return documents


def chunk_document(content: str, chunk_size: int = 1000) -> List[str]:
    """
    Split document content into chunks of approximately chunk_size characters.

    Args:
        content: Document content to chunk
        chunk_size: Target size for each chunk

    Returns:
        List of content chunks
    """
    chunks = []
    words = content.split()
    current_chunk = []
    current_size = 0

    for word in words:
        word_size = len(word) + 1  # +1 for space

        if current_size + word_size > chunk_size and current_chunk:
            # Finish current chunk
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_size = word_size
        else:
            current_chunk.append(word)
            current_size += word_size

    # Add final chunk if any content remains
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def calculate_sha256(content: str) -> str:
    """Calculate SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def test_cache_hit_ratio() -> Dict[str, Any]:
    """
    Test cache hit ratio with SHA-256 deduplication.

    Returns:
        Dict with test results
    """
    results: Dict[str, Any] = {
        "test_id": "25",
        "test_name": "Cache hit ratio exceeds 70% with SHA-256 of input chunk",
        "num_documents": 100,
        "chunk_size": 1000,
        "total_chunks": 0,
        "unique_chunks": 0,
        "duplicate_chunks": 0,
        "cache_hit_ratio": 0.0,
        "hash_distribution": {},
        "chunk_size_stats": {"min": float("inf"), "max": 0, "avg": 0.0},
        "success": False,
        "error": None,
    }

    try:
        print(f"Generating {results['num_documents']} similar documents...")

        # Generate similar documents
        documents = generate_similar_documents(results["num_documents"])

        # Track all chunks and their hashes
        chunk_hashes: Set[str] = set()
        hash_counts: Dict[str, int] = {}
        chunk_sizes: List[int] = []

        print("Processing documents and calculating chunk hashes...")

        for doc_idx, document in enumerate(documents):
            # Split document into chunks
            chunks = chunk_document(document, results["chunk_size"])

            for chunk in chunks:
                # Calculate hash
                chunk_hash = calculate_sha256(chunk)
                chunk_size = len(chunk)

                # Track statistics
                results["total_chunks"] += 1
                chunk_sizes.append(chunk_size)

                if chunk_hash in hash_counts:
                    # Cache hit - we've seen this chunk before
                    hash_counts[chunk_hash] += 1
                    results["duplicate_chunks"] += 1
                else:
                    # Cache miss - new unique chunk
                    chunk_hashes.add(chunk_hash)
                    hash_counts[chunk_hash] = 1
                    results["unique_chunks"] += 1

        # Calculate cache hit ratio
        if results["total_chunks"] > 0:
            results["cache_hit_ratio"] = (
                results["duplicate_chunks"] / results["total_chunks"]
            )

        # Calculate chunk size statistics
        if chunk_sizes:
            results["chunk_size_stats"]["min"] = min(chunk_sizes)
            results["chunk_size_stats"]["max"] = max(chunk_sizes)
            results["chunk_size_stats"]["avg"] = sum(chunk_sizes) / len(
                chunk_sizes
            )

        # Analyze hash distribution (top 10 most common hashes)
        sorted_hashes = sorted(
            hash_counts.items(), key=lambda x: x[1], reverse=True
        )
        results["hash_distribution"] = {
            "most_common_hashes": sorted_hashes[:10],
            "unique_hashes": len(chunk_hashes),
            "max_duplicates": max(hash_counts.values()) if hash_counts else 0,
        }

        print(f"Total chunks processed: {results['total_chunks']}")
        print(f"Unique chunks: {results['unique_chunks']}")
        print(f"Duplicate chunks: {results['duplicate_chunks']}")
        print(f"Cache hit ratio: {results['cache_hit_ratio']:.2%}")

        # Success criteria: cache hit ratio >= 70%
        results["success"] = results["cache_hit_ratio"] >= 0.70

        if results["success"]:
            print("✅ Cache hit ratio meets target (≥70%)")
        else:
            print("❌ Cache hit ratio below target (<70%)")

    except Exception as e:
        results["error"] = str(e)
        print(f"Error during test: {e}")

    return results


def main():
    """Run the cache hit ratio test."""
    print("Test 25: Cache hit ratio exceeds 70% with SHA-256 of input chunk")
    print("=" * 60)

    results = test_cache_hit_ratio()

    # Save results
    output_file = Path(__file__).parent / "results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\nResults saved to: {output_file}")
    print(f"Documents processed: {results['num_documents']}")
    print(f"Total chunks: {results['total_chunks']}")
    print(f"Unique chunks: {results['unique_chunks']}")
    print(f"Cache hit ratio: {results['cache_hit_ratio']:.2%}")
    print(
        f"Average chunk size: {results['chunk_size_stats']['avg']:.0f} chars"
    )

    if results["success"]:
        print("✅ PASS: Cache hit ratio exceeds 70%")
    else:
        print("❌ FAIL: Cache hit ratio below 70%")
        if results["error"]:
            print(f"Error: {results['error']}")

    return results


if __name__ == "__main__":
    main()
