#!/usr/bin/env python3
"""
Run test queries against the Islamic KB and save results for analysis.
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime

from openai import OpenAI
from qdrant_client import QdrantClient
from query import search, format_context, generate_answer, QDRANT_PATH

# Test queries covering different aspects of the Seal of Prophets book
TEST_QUERIES = [
    # Core theological questions
    "What does Khatam-un-Nabiyyin mean?",
    "How does the Ahmadiyya community interpret the Seal of the Prophets?",
    "What is the relationship between Prophet Muhammad and later prophets?",

    # About the Promised Messiah
    "Who was Mirza Ghulam Ahmad?",
    "What are the claims of the Promised Messiah?",
    "What prophecies did the Promised Messiah fulfill?",

    # Jesus/Isa related
    "What happened to Jesus after the crucifixion?",
    "Where is Jesus buried according to Ahmadiyya belief?",
    "Did Jesus die on the cross?",

    # Prophethood concepts
    "What types of prophets are there in Islam?",
    "Can there be prophets after Muhammad?",
    "What is the difference between a law-bearing and non-law-bearing prophet?",

    # Historical/Contextual
    "What do other Muslim scholars say about Khatam-un-Nabiyyin?",
    "What Quranic verses discuss the finality of prophethood?",
    "What Hadith support the Ahmadiyya interpretation?",
]


def run_queries():
    """Run all test queries and collect results."""
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable not set")

    openai_client = OpenAI()
    qdrant_client = QdrantClient(path=str(QDRANT_PATH))

    results = []

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/{len(TEST_QUERIES)}] Query: {query}")
        print("-" * 60)

        try:
            # Search for relevant chunks
            sources = search(query, qdrant_client, openai_client)

            if not sources:
                result = {
                    "query": query,
                    "answer": "No relevant information found in the knowledge base.",
                    "sources": [],
                    "timestamp": datetime.now().isoformat(),
                    "success": True,
                }
            else:
                # Format context and generate answer
                context = format_context(sources)
                answer = "".join(generate_answer(query, context, openai_client, stream=False))

                result = {
                    "query": query,
                    "answer": answer,
                    "sources": [
                        {
                            "book": s["book"],
                            "page": s["page"],
                            "score": s["score"],
                            "text": s["text"],
                        }
                        for s in sources[:5]  # Top 5 sources
                    ],
                    "timestamp": datetime.now().isoformat(),
                    "success": True,
                }

                print(f"Answer preview: {answer[:200]}...")
                print(f"Sources: {len(sources)} chunks retrieved")

        except Exception as e:
            result = {
                "query": query,
                "answer": None,
                "sources": [],
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e),
            }
            print(f"Error: {e}")

        results.append(result)

    return results


def main():
    print("=" * 60)
    print("Running Test Queries on Islamic Knowledge Base")
    print("=" * 60)

    results = run_queries()

    # Save to JSON
    output_path = Path(__file__).parent / "query_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Results saved to: {output_path}")
    print(f"Total queries: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r['success'])}")
    print(f"Failed: {sum(1 for r in results if not r['success'])}")


if __name__ == "__main__":
    main()
