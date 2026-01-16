#!/usr/bin/env python3
"""
Query the Islamic Knowledge Base using RAG.
"""

import os
import sys
import json
import argparse
from pathlib import Path

from openai import OpenAI
from qdrant_client import QdrantClient
from pipeline import normalize_honorifics

# Configuration
EMBEDDING_MODEL = "text-embedding-3-large"
COLLECTION_NAME = "islamic_books"
TOP_K = 10
QDRANT_PATH = Path(__file__).parent / "qdrant_data"

SYSTEM_PROMPT = """You are a knowledgeable assistant specializing in Islamic literature from the Ahmadiyya Muslim Community perspective, particularly the works of Hazrat Mirza Tahir Ahmad (1928-2003), the Fourth Caliph (Khalifatul Masih IV).

## About the Ahmadiyya Muslim Community

The Ahmadiyya Muslim Community is a revivalist movement within Islam founded in 1889 by Hazrat Mirza Ghulam Ahmad (1835-1908) in Qadian, India. Key beliefs include:

**Core Islamic Beliefs:**
- Complete adherence to the Five Pillars of Islam (Shahada, Salat, Zakat, Sawm, Hajj)
- Belief in the Holy Quran as the final and perfect scripture
- Belief in Prophet Muhammad (peace be upon him) as Khatam-un-Nabiyyin (Seal of the Prophets)

**Distinctive Beliefs:**
- Hazrat Mirza Ghulam Ahmad is believed to be the Promised Messiah and Imam Mahdi, whose advent was prophesied by Prophet Muhammad
- "Seal of the Prophets" means Prophet Muhammad brought prophethood to perfection; prophets fully subordinate to him and his teachings can still appear
- Jesus (peace be upon him) survived the crucifixion, migrated to Kashmir, lived a full life, and died a natural death. He is buried in Srinagar, Kashmir
- Jihad by the sword is not permitted in the current age; the focus is on Jihad of the pen (intellectual discourse) and self-reformation
- The Ahmadiyya Khilafat (spiritual successorship) continues today, currently led by Hazrat Mirza Masroor Ahmad, the Fifth Caliph

**Motto:** "Love for All, Hatred for None"

**Mission:** Peaceful propagation of Islam, interfaith dialogue, humanitarian service, and building mosques worldwide.

## Instructions

Answer questions based on the provided context from the books. When answering:
1. Use direct quotes when relevant, citing the book and page number
2. If the context doesn't contain enough information to answer, say so
3. Be accurate and don't make up information not found in the sources
4. Format citations as [Book Name, p. X]
5. Frame answers within the Ahmadiyya understanding of Islam when relevant
6. IMPORTANT: Always format honorifics in parentheses, separated from the name:
   - Prophet Muhammad(saw) or Muhammad(sa) - NOT "Muhammadsaw"
   - Hadhrat Khadijah(ra) - NOT "Khadijahra"
   - Prophet Isa(as) - NOT "Isaas"
   - Use (saw) or (sa) for the Holy Prophet, (ra) for companions, (as) for other prophets

Context from the books will be provided below."""


def get_embedding(text: str, client: OpenAI) -> list[float]:
    """Get embedding for a query."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def search(query: str, qdrant: QdrantClient, openai_client: OpenAI) -> list[dict]:
    """Search for relevant chunks."""
    query_embedding = get_embedding(query, openai_client)

    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=TOP_K,
    ).points

    return [
        {
            "text": r.payload["text"],
            "book": r.payload["book"],
            "page": r.payload["page"],
            "score": r.score,
        }
        for r in results
    ]


def format_context(results: list[dict]) -> str:
    """Format search results as context for the LLM."""
    context_parts = []
    for i, r in enumerate(results, 1):
        context_parts.append(
            f"[Source {i}] {r['book']}, Page {r['page']}:\n{r['text']}\n"
        )
    return "\n---\n".join(context_parts)


def generate_answer(query: str, context: str, client: OpenAI, stream: bool = False):
    """Generate an answer using Claude-style prompting with OpenAI."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Context:\n{context}\n\n---\n\nQuestion: {query}",
        },
    ]

    if stream:
        response = client.chat.completions.create(
            model="gpt-5.2",
            messages=messages,
            temperature=0.3,
            max_completion_tokens=1000,
            stream=True,
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    else:
        response = client.chat.completions.create(
            model="gpt-5.2",
            messages=messages,
            temperature=0.3,
            max_completion_tokens=1000,
        )
        yield response.choices[0].message.content


def query_kb(query: str, stream: bool = False):
    """Main query function. If stream=True, yields tokens and returns sources at end."""
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable not set")

    openai_client = OpenAI()
    qdrant_client = QdrantClient(path=str(QDRANT_PATH))

    # Search
    print("Searching...", file=sys.stderr)
    results = search(query, qdrant_client, openai_client)

    if not results:
        if stream:
            yield "No relevant information found in the knowledge base."
            return []
        return "No relevant information found in the knowledge base.", []

    # Format context
    context = format_context(results)

    # Generate answer
    print("Generating answer...", file=sys.stderr)

    if stream:
        for token in generate_answer(query, context, openai_client, stream=True):
            yield token
        return results
    else:
        answer = "".join(generate_answer(query, context, openai_client, stream=False))
        return answer, results


def query_kb_stream(query: str):
    """Stream query results to stdout with sources at end."""
    if not os.getenv("OPENAI_API_KEY"):
        print(json.dumps({"error": "OPENAI_API_KEY not set"}), file=sys.stderr)
        sys.exit(1)

    openai_client = OpenAI()
    qdrant_client = QdrantClient(path=str(QDRANT_PATH))

    # Search
    print("Searching...", file=sys.stderr)
    results = search(query, qdrant_client, openai_client)

    if not results:
        print("No relevant information found in the knowledge base.")
        print("\n---SOURCES---")
        print(json.dumps([]))
        return

    # Format context
    context = format_context(results)

    # Generate and stream answer
    print("Generating...", file=sys.stderr)
    for token in generate_answer(query, context, openai_client, stream=True):
        print(token, end="", flush=True)

    # Print sources with full text
    print("\n---SOURCES---")
    sources = [{"book": r["book"], "page": r["page"], "score": r["score"], "text": r["text"]} for r in results[:5]]
    print(json.dumps(sources))


def interactive_mode():
    """Run in interactive mode."""
    print("Islamic Knowledge Base - Interactive Query")
    print("Type 'quit' to exit\n")

    while True:
        query = input("\nYour question: ").strip()
        if query.lower() in ('quit', 'exit', 'q'):
            break
        if not query:
            continue

        try:
            answer, sources = query_kb(query)
            print(f"\n{'='*60}")
            print("ANSWER:")
            print(answer)
            print(f"\n{'='*60}")
            print("SOURCES:")
            for i, s in enumerate(sources[:5], 1):
                print(f"  {i}. {s['book']}, p.{s['page']} (score: {s['score']:.3f})")
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Query the Islamic Knowledge Base")
    parser.add_argument("query", nargs="*", help="The question to ask")
    parser.add_argument("--stream", action="store_true", help="Stream output for TUI consumption")
    args = parser.parse_args()

    if args.stream:
        if not args.query:
            print("Error: query required with --stream", file=sys.stderr)
            sys.exit(1)
        query = " ".join(args.query)
        query_kb_stream(query)
    elif args.query:
        query = " ".join(args.query)
        answer, sources = query_kb(query)
        print(f"\nAnswer:\n{answer}")
        print(f"\nSources:")
        for i, s in enumerate(sources[:5], 1):
            print(f"  {i}. {s['book']}, p.{s['page']}")
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
