# Technical Implementation Plan - MVP

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────┐
│ alislam.org │────▶│ Scraper      │────▶│ Chunker     │────▶│ Embedder│
│ (HTML)      │     │ + Cache      │     │             │     │         │
└─────────────┘     └──────────────┘     └─────────────┘     └────┬────┘
                                                                  │
                    ┌──────────────┐     ┌─────────────┐     ┌────▼────┐
                    │ Claude +     │◀────│ Retriever   │◀────│ Qdrant  │
                    │ Citations    │     │ (top-k)     │     │         │
                    └──────────────┘     └─────────────┘     └─────────┘
```

## Embeddings

### Model Options

| Model | Dims | Multilingual | Cost | Notes |
|-------|------|--------------|------|-------|
| OpenAI text-embedding-3-large | 3072 | Good | $0.13/1M tokens | Solid default |
| OpenAI text-embedding-3-small | 1536 | Good | $0.02/1M tokens | 5x cheaper, slightly worse |
| Cohere embed-v3 | 1024 | Excellent | $0.10/1M tokens | Strong for multilingual |
| Voyage AI voyage-large-2 | 1536 | Good | $0.12/1M tokens | Top MTEB scores |

### Recommendation

Start with `text-embedding-3-small` (cheap), upgrade if recall is poor.

### Evaluation Method

1. Create a test set (10-20 query/passage pairs with known correct answers)
2. Measure Recall@k - does the correct chunk appear in top 5/10 results?
3. Test multilingual - embed Arabic quote, query in English, check retrieval

## Chunking Strategy

### Approach: Structural Chunking (Recommended)

Religious texts have clear hierarchies. Use the document's natural structure:

```python
# Chunk by section/chapter, respect boundaries
chunks = []
for chapter in book.chapters:
    for section in chapter.sections:
        if token_count(section) <= 1024:
            chunks.append(section)
        else:
            # Split large sections with overlap
            chunks.extend(split_with_overlap(section, size=512, overlap=50))
```

### Configuration

```python
CHUNK_SIZE = 512      # tokens
CHUNK_OVERLAP = 50    # tokens
RESPECT_SECTIONS = True  # don't split mid-section if possible
```

### Chunk Metadata

Include rich metadata for filtering and citation:

```python
chunk = {
    "text": "...",
    "book": "Philosophy of Teachings of Islam",
    "author": "promised-messiah",
    "chapter": "The State of Man After Death",
    "page": 45,
    "url": "https://alislam.org/library/books/...",  # deep link
}
```

## Retrieval

```python
TOP_K = 10  # retrieve 10 chunks, let Claude select the most relevant
```

## Evaluation Strategy

Before building the full system, run a retrieval-only test:

1. Scrape 1 book
2. Chunk it 3 different ways (512 tokens, 1024 tokens, section-based)
3. Embed with 2 models (OpenAI small vs large)
4. Run 20 test queries, measure which config retrieves the right chunks

This validates the optimal setup before building everything.
