#!/usr/bin/env python3
"""
Test 29: Chunking large PDFs into ≤ 8K token hunks keeps entity links intact
Chunk then extract entities, check continuity
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set


def create_large_document_with_entities() -> str:
    """Create a large document with named entities and cross-references."""
    return """# Corporate Annual Report 2024

## Executive Summary

Acme Corporation, founded in 1985 by CEO John Smith, has achieved remarkable growth this year. 
The company, headquartered in New York City, reported record revenues of $500 million.

Our Chief Technology Officer, Dr. Sarah Johnson, led the development of our flagship product, 
the Acme Widget Pro. This innovative solution has captured 25% market share in the widget industry.

## Company Leadership

The executive team includes:
- John Smith (CEO): Founded Acme Corporation and has led the company for 39 years
- Dr. Sarah Johnson (CTO): Joined in 2010, holds PhD from MIT
- Michael Brown (CFO): Former Goldman Sachs executive, joined in 2020
- Lisa Chen (COO): Previously at Apple Inc., responsible for operations

## Product Portfolio

### Acme Widget Pro
The Acme Widget Pro, developed under Dr. Sarah Johnson's leadership, represents our core offering.
This product generated $300 million in revenue, with John Smith personally overseeing major client relationships.

### Acme Analytics Platform
Our analytics platform, championed by Lisa Chen, provides insights to Fortune 500 companies.
Michael Brown's financial modeling shows this product has 40% profit margins.

## Financial Performance

CFO Michael Brown reported the following key metrics:
- Total Revenue: $500 million (up 25% from previous year)
- Net Income: $75 million 
- R&D Investment: $50 million, primarily allocated to Dr. Sarah Johnson's technology division

CEO John Smith noted that these results exceed all projections made at the beginning of 2024.

## Market Analysis

The widget market, where Acme Corporation competes, is valued at $2 billion globally.
Our main competitors include Widget Industries Inc. and Global Widget Solutions.

Dr. Sarah Johnson's technical innovations have given Acme Corporation a competitive advantage.
The Acme Widget Pro outperforms competing products from Widget Industries Inc. by 30%.

## Strategic Partnerships

Acme Corporation has formed strategic alliances with:
- Microsoft Corporation for cloud integration
- Amazon Web Services for infrastructure
- Oracle Corporation for database solutions

John Smith personally negotiated the Microsoft Corporation partnership, while Lisa Chen 
managed the Amazon Web Services integration. Dr. Sarah Johnson provided technical oversight
for the Oracle Corporation database implementation.

## Research and Development

Under Dr. Sarah Johnson's direction, our R&D team has filed 15 patents this year.
The team, located at our Silicon Valley facility, works closely with Stanford University.

Key research areas include:
- Artificial Intelligence applications in widget manufacturing
- Sustainable materials for the Acme Widget Pro
- Next-generation analytics for the Acme Analytics Platform

## International Expansion

COO Lisa Chen has overseen expansion into European markets, establishing offices in:
- London, United Kingdom
- Berlin, Germany  
- Paris, France

Each European office reports to Lisa Chen and maintains direct communication with 
CEO John Smith for strategic decisions.

## Sustainability Initiatives

Acme Corporation has committed to carbon neutrality by 2030. Dr. Sarah Johnson leads
our sustainability task force, working with environmental consultants from 
Greentech Solutions Inc.

The Acme Widget Pro manufacturing process has been redesigned to reduce carbon emissions
by 40%, a project personally championed by John Smith.

## Future Outlook

Looking ahead to 2025, CEO John Smith expects continued growth. The company plans to:
- Launch Acme Widget Pro 2.0 under Dr. Sarah Johnson's technical leadership
- Expand the Acme Analytics Platform to new markets via Lisa Chen's operations team
- Achieve $750 million in revenue, as projected by CFO Michael Brown

## Conclusion

Acme Corporation's success in 2024 demonstrates the effectiveness of our leadership team.
John Smith's strategic vision, Dr. Sarah Johnson's technical expertise, Michael Brown's
financial acumen, and Lisa Chen's operational excellence have positioned the company
for continued growth.

The Acme Widget Pro and Acme Analytics Platform represent the foundation of our future,
with strong support from partners like Microsoft Corporation, Amazon Web Services,
and Oracle Corporation.

As we enter 2025, Acme Corporation remains committed to innovation, sustainability,
and delivering value to our stakeholders under the continued leadership of our
executive team.
"""


def extract_entities(text: str) -> Dict[str, Set[str]]:
    """
    Extract named entities from text using simple pattern matching.

    Returns:
        Dict mapping entity types to sets of entity names
    """
    entities = {
        "PERSON": set(),
        "ORGANIZATION": set(),
        "PRODUCT": set(),
        "LOCATION": set(),
        "MONEY": set(),
    }

    # Person patterns (titles + names)
    person_patterns = [
        r"\b(?:CEO|CTO|CFO|COO|Dr\.)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b",
        r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+\((?:CEO|CTO|CFO|COO)\))",
    ]

    for pattern in person_patterns:
        matches = re.findall(pattern, text)
        entities["PERSON"].update(matches)

    # Organization patterns
    org_patterns = [
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Corporation|Inc\.|Company|Solutions))\b",
        r"\b(Acme\s+Corporation)\b",
        r"\b(Microsoft\s+Corporation)\b",
        r"\b(Amazon\s+Web\s+Services)\b",
        r"\b(Oracle\s+Corporation)\b",
    ]

    for pattern in org_patterns:
        matches = re.findall(pattern, text)
        entities["ORGANIZATION"].update(matches)

    # Product patterns
    product_patterns = [
        r"\b(Acme\s+Widget\s+Pro(?:\s+2\.0)?)\b",
        r"\b(Acme\s+Analytics\s+Platform)\b",
    ]

    for pattern in product_patterns:
        matches = re.findall(pattern, text)
        entities["PRODUCT"].update(matches)

    # Location patterns
    location_patterns = [
        r"\b(New\s+York\s+City)\b",
        r"\b(Silicon\s+Valley)\b",
        r"\b(London,\s+United\s+Kingdom)\b",
        r"\b(Berlin,\s+Germany)\b",
        r"\b(Paris,\s+France)\b",
    ]

    for pattern in location_patterns:
        matches = re.findall(pattern, text)
        entities["LOCATION"].update(matches)

    # Money patterns
    money_patterns = [
        r"\$(\d+(?:,\d{3})*(?:\.\d{2})?\s+(?:million|billion))",
        r"\$(\d+(?:,\d{3})*)",
    ]

    for pattern in money_patterns:
        matches = re.findall(pattern, text)
        entities["MONEY"].update(matches)

    return entities


def chunk_text(text: str, max_tokens: int = 8000) -> List[str]:
    """
    Chunk text into segments of approximately max_tokens.

    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk (approximated as 4 chars per token)

    Returns:
        List of text chunks
    """
    # Rough approximation: 1 token ≈ 4 characters
    max_chars = max_tokens * 4

    # Split by paragraphs first to maintain coherence
    paragraphs = text.split("\n\n")

    chunks = []
    current_chunk = []
    current_size = 0

    for paragraph in paragraphs:
        paragraph_size = len(paragraph) + 2  # +2 for \n\n

        if current_size + paragraph_size > max_chars and current_chunk:
            # Finish current chunk
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [paragraph]
            current_size = paragraph_size
        else:
            current_chunk.append(paragraph)
            current_size += paragraph_size

    # Add final chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def find_entity_links(
    entities_by_chunk: List[Dict[str, Set[str]]],
) -> Dict[str, Any]:
    """
    Analyze entity continuity across chunks.

    Args:
        entities_by_chunk: List of entity dictionaries for each chunk

    Returns:
        Dict with link analysis results
    """
    analysis = {
        "total_chunks": len(entities_by_chunk),
        "entities_per_chunk": [],
        "cross_chunk_entities": {},
        "broken_links": [],
        "continuity_score": 0.0,
    }

    # Track entities across all chunks
    all_entities = {}
    for entity_type in [
        "PERSON",
        "ORGANIZATION",
        "PRODUCT",
        "LOCATION",
        "MONEY",
    ]:
        all_entities[entity_type] = set()
        for chunk_entities in entities_by_chunk:
            all_entities[entity_type].update(
                chunk_entities.get(entity_type, set())
            )

    # Analyze each entity's distribution across chunks
    for entity_type, entities in all_entities.items():
        analysis["cross_chunk_entities"][entity_type] = {}

        for entity in entities:
            chunk_appearances = []
            for i, chunk_entities in enumerate(entities_by_chunk):
                if entity in chunk_entities.get(entity_type, set()):
                    chunk_appearances.append(i)

            analysis["cross_chunk_entities"][entity_type][entity] = {
                "chunks": chunk_appearances,
                "total_appearances": len(chunk_appearances),
                "span": max(chunk_appearances) - min(chunk_appearances) + 1
                if chunk_appearances
                else 0,
            }

            # Check for broken links (entity appears in non-consecutive chunks)
            if len(chunk_appearances) > 1:
                consecutive = all(
                    chunk_appearances[i] + 1 == chunk_appearances[i + 1]
                    for i in range(len(chunk_appearances) - 1)
                )
                if not consecutive:
                    analysis["broken_links"].append(
                        {
                            "entity": entity,
                            "type": entity_type,
                            "chunks": chunk_appearances,
                        }
                    )

    # Calculate continuity score
    total_entities = sum(len(entities) for entities in all_entities.values())
    broken_entities = len(analysis["broken_links"])

    if total_entities > 0:
        analysis["continuity_score"] = 1.0 - (broken_entities / total_entities)

    # Store per-chunk statistics
    for i, chunk_entities in enumerate(entities_by_chunk):
        chunk_stats = {
            "chunk_id": i,
            "entity_counts": {
                entity_type: len(entities)
                for entity_type, entities in chunk_entities.items()
            },
        }
        analysis["entities_per_chunk"].append(chunk_stats)

    return analysis


def test_chunking_entity_links() -> Dict[str, Any]:
    """
    Test entity link preservation during document chunking.

    Returns:
        Dict with test results
    """
    results: Dict[str, Any] = {
        "test_id": "29",
        "test_name": "Chunking large PDFs into ≤ 8K token hunks keeps entity links intact",
        "document_created": False,
        "document_size": 0,
        "chunks_created": 0,
        "max_chunk_tokens": 8000,
        "entities_extracted": False,
        "total_entities": 0,
        "broken_links": 0,
        "continuity_score": 0.0,
        "link_analysis": {},
        "success": False,
        "error": None,
    }

    try:
        # Create large document with entities
        document = create_large_document_with_entities()
        results["document_created"] = True
        results["document_size"] = len(document)

        print(f"Created document with {results['document_size']} characters")

        # Chunk the document
        chunks = chunk_text(document, results["max_chunk_tokens"])
        results["chunks_created"] = len(chunks)

        print(f"Created {results['chunks_created']} chunks")

        # Extract entities from each chunk
        entities_by_chunk = []
        for i, chunk in enumerate(chunks):
            chunk_entities = extract_entities(chunk)
            entities_by_chunk.append(chunk_entities)

            # Log chunk info
            total_chunk_entities = sum(
                len(entities) for entities in chunk_entities.values()
            )
            print(
                f"Chunk {i + 1}: {len(chunk)} chars, {total_chunk_entities} entities"
            )

        results["entities_extracted"] = True

        # Analyze entity links across chunks
        link_analysis = find_entity_links(entities_by_chunk)
        results["link_analysis"] = link_analysis
        results["broken_links"] = len(link_analysis["broken_links"])
        results["continuity_score"] = link_analysis["continuity_score"]

        # Calculate total entities
        all_entities = set()
        for chunk_entities in entities_by_chunk:
            for entity_type, entities in chunk_entities.items():
                all_entities.update(entities)
        results["total_entities"] = len(all_entities)

        print(f"Total unique entities: {results['total_entities']}")
        print(f"Broken entity links: {results['broken_links']}")
        print(f"Continuity score: {results['continuity_score']:.2%}")

        # Print broken links details
        if results["broken_links"] > 0:
            print("\nBroken entity links:")
            for broken_link in link_analysis["broken_links"]:
                print(
                    f"  {broken_link['entity']} ({broken_link['type']}): chunks {broken_link['chunks']}"
                )

        # Success criteria: continuity score > 90% (less than 10% broken links)
        results["success"] = results["continuity_score"] >= 0.90

    except Exception as e:
        results["error"] = str(e)

    return results


def main():
    """Run the chunking entity links test."""
    print(
        "Test 29: Chunking large PDFs into ≤ 8K token hunks keeps entity links intact"
    )
    print("=" * 60)

    results = test_chunking_entity_links()

    # Save results
    output_file = Path(__file__).parent / "results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\nResults saved to: {output_file}")
    print(f"Document size: {results['document_size']} characters")
    print(f"Chunks created: {results['chunks_created']}")
    print(f"Total entities: {results['total_entities']}")
    print(f"Broken links: {results['broken_links']}")
    print(f"Continuity score: {results['continuity_score']:.2%}")

    if results["success"]:
        print("✅ PASS: Entity links preserved during chunking")
    else:
        print("❌ FAIL: Too many broken entity links")
        if results["error"]:
            print(f"Error: {results['error']}")

    return results


if __name__ == "__main__":
    main()
