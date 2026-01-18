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

QUERY_SYNTHESIS_PROMPT = """You are a query synthesizer for a RAG system about Islamic literature.

Given a conversation history and the user's latest message, generate a SINGLE standalone search query that captures what information needs to be retrieved.

Rules:
1. If the latest message is a complete question, return it as-is (possibly improved)
2. If it's a follow-up (e.g., "elaborate", "why?", "tell me more"), synthesize a query that includes the necessary context
3. If the user shifts topics, focus only on the new topic
4. Output ONLY the search query, nothing else
5. Keep the query concise but specific (aim for 5-20 words)

Examples:
- History: "What is Khatam-un-Nabiyyin?" / Latest: "elaborate further" → "detailed explanation of Khatam-un-Nabiyyin meaning and its significance in Islam"
- History: "Who was the Promised Messiah?" / Latest: "what prophecies did he fulfill?" → "prophecies fulfilled by the Promised Messiah Mirza Ghulam Ahmad"
- History: "Tell me about jihad" / Latest: "now explain khilafat" → "khilafat in Islam and Ahmadiyya Muslim Community"
"""

SYSTEM_PROMPT = """You are a knowledgeable scholar of Islamic literature, well-versed in the teachings of the Ahmadiyya Muslim Community.

## Your Capabilities
You have access to a search tool that can look up information from Islamic texts by Ahmadiyya scholars and Khulafa. Use it when you need factual information not already discussed in our conversation.

You understand Ahmadiyya beliefs including:
- Hazrat Mirza Ghulam Ahmad(as) as the Promised Messiah and Imam Mahdi
- The meaning of Khatam-un-Nabiyyin (Seal of the Prophets)
- The survival of Jesus(as) from the cross and his migration to Kashmir
- The spiritual nature of Jihad in this age
- The continuation of Khilafat

## When to Search
- **DO search** for new topics, specific quotes, detailed theological questions, or factual claims
- **DON'T search** for follow-ups about what we just discussed, clarifications, rephrasing requests, or general conversation

## How to Respond

**Be conversational:** Answer naturally as someone who knows this material. Never reference "search results" or "the documents" - just answer directly.

**Be concise:** Give clear, focused answers. A flowing paragraph is often better than bullet points.

**Citations:** Only cite when directly quoting. Use simple format: [p. 42] for page numbers.

**Honorifics:** Format as: Muhammad(saw), Khadijah(ra), Isa(as) - with honorific in parentheses.

**When you don't know:** If you've searched and can't find information, say so naturally."""

# Tool definition for search
SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_islamic_texts",
        "description": "Search the Islamic knowledge base for information from books by Ahmadiyya scholars and Khulafa. Use when you need factual information, quotes, or theological details not already covered in our conversation.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query - be specific about what information you need"
                }
            },
            "required": ["query"]
        }
    }
}


def get_embedding(text: str, client: OpenAI) -> list[float]:
    """Get embedding for a query."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def synthesize_search_query(
    current_query: str,
    conversation_history: list[dict],
    client: OpenAI,
) -> str:
    """
    Synthesize a standalone search query from conversation history and current message.

    For medium/long threads, this ensures follow-ups like "elaborate" or "why?"
    get expanded into meaningful search queries.
    """
    # If no history or query is already substantial, skip synthesis
    if not conversation_history:
        return current_query

    # Build conversation context for the synthesizer
    messages = [{"role": "system", "content": QUERY_SYNTHESIS_PROMPT}]

    # Add recent conversation history (last 3 turns max to keep it focused)
    recent_history = conversation_history[-3:]
    history_text = ""
    for turn in recent_history:
        history_text += f"User: {turn['question']}\n"
        # Include a brief snippet of the answer for context
        answer_snippet = turn.get('answer', '')[:300]
        if len(turn.get('answer', '')) > 300:
            answer_snippet += "..."
        history_text += f"Assistant: {answer_snippet}\n\n"

    messages.append({
        "role": "user",
        "content": f"Conversation history:\n{history_text}\nLatest user message: {current_query}\n\nGenerate the search query:",
    })

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Fast/cheap model for query synthesis
        messages=messages,
        temperature=0,
        max_tokens=100,
    )

    synthesized = response.choices[0].message.content.strip()
    # Remove quotes if the model wrapped the query in them
    synthesized = synthesized.strip('"\'')

    return synthesized


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


def generate_answer(
    query: str,
    context: str,
    client: OpenAI,
    conversation_history: list[dict] | None = None,
    stream: bool = False,
):
    """Generate an answer using conversation history and retrieved context."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history for continuity
    if conversation_history:
        # Include last few turns for context (limit to avoid token overflow)
        for turn in conversation_history[-4:]:
            messages.append({"role": "user", "content": turn["question"]})
            messages.append({"role": "assistant", "content": turn["answer"]})

    # Add current query with retrieved context (framed as reference material, not "excerpts")
    messages.append({
        "role": "user",
        "content": f"[Reference material]\n{context}\n\n[User question]\n{query}",
    })

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


def query_kb_stream(query: str, conversation_history: list[dict] | None = None):
    """
    Stream query results using tool-use pattern.

    The model decides whether to search the knowledge base or answer directly
    from conversation context. This produces more natural conversations.
    """
    if not os.getenv("OPENAI_API_KEY"):
        print(json.dumps({"error": "OPENAI_API_KEY not set"}), file=sys.stderr)
        sys.exit(1)

    openai_client = OpenAI()
    qdrant_client = QdrantClient(path=str(QDRANT_PATH))

    # Build message history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if conversation_history:
        for turn in conversation_history[-4:]:  # Last 4 turns for context
            messages.append({"role": "user", "content": turn["question"]})
            messages.append({"role": "assistant", "content": turn["answer"]})

    messages.append({"role": "user", "content": query})

    # First call: let model decide if it needs to search
    print("Thinking...", file=sys.stderr)
    response = openai_client.chat.completions.create(
        model="gpt-4o",  # Use 4o for tool decisions (faster, cheaper than 5.2)
        messages=messages,
        tools=[SEARCH_TOOL],
        tool_choice="auto",  # Model decides whether to use tool
        temperature=0.3,
    )

    assistant_message = response.choices[0].message
    sources = []

    # Check if model wants to search
    if assistant_message.tool_calls:
        tool_call = assistant_message.tool_calls[0]
        if tool_call.function.name == "search_islamic_texts":
            # Extract search query from tool call
            tool_args = json.loads(tool_call.function.arguments)
            search_query = tool_args.get("query", query)

            print(f"Searching: {search_query}", file=sys.stderr)

            # Execute search
            results = search(search_query, qdrant_client, openai_client)

            if results:
                context = format_context(results)
                sources = [
                    {"book": r["book"], "page": r["page"], "score": r["score"], "text": r["text"]}
                    for r in results[:5]
                ]
            else:
                context = "No relevant information found in the knowledge base."

            # Add assistant's tool call and tool result to messages
            messages.append(assistant_message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": context,
            })

            # Generate final response with search results
            print("Generating...", file=sys.stderr)
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3,
                max_completion_tokens=1000,
                stream=True,
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="", flush=True)
    else:
        # Model chose not to search - use the response directly
        print("Answering from context...", file=sys.stderr)

        if assistant_message.content:
            # Use the already-generated response
            print(assistant_message.content, end="", flush=True)
        else:
            # Fallback: re-request if content was empty (shouldn't happen)
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3,
                max_completion_tokens=1000,
                stream=True,
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="", flush=True)

    # Print sources (empty if no search was performed)
    print("\n---SOURCES---")
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
    parser.add_argument(
        "--history",
        type=str,
        help="JSON conversation history: [{question, answer}, ...]",
    )
    args = parser.parse_args()

    # Parse conversation history if provided
    conversation_history = None
    if args.history:
        try:
            conversation_history = json.loads(args.history)
        except json.JSONDecodeError as e:
            print(f"Error parsing history JSON: {e}", file=sys.stderr)
            sys.exit(1)

    if args.stream:
        if not args.query:
            print("Error: query required with --stream", file=sys.stderr)
            sys.exit(1)
        query = " ".join(args.query)
        query_kb_stream(query, conversation_history)
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
