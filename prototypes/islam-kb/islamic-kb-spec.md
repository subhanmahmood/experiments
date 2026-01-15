# Islamic Knowledge Base - Enhanced Specification

## Vision & Purpose

### The Core Problem
The friction of opening books and searching through them is too high. Valuable knowledge sits unread in a vast digital library. **This tool makes the knowledge accessible through conversation.**

### What This Is
A RAG-powered conversational study tool that serves as the **primary entry point** to Islamic texts from alislam.org. Not a supplement to reading—a replacement for manual searching.

### What Success Looks Like
- Even if incomplete: **Learning RAG/AI implementation is valuable**
- Ideal: Faster than browsing alislam.org manually, helps understand topics deeply

### Key Concerns to Address
1. **Accuracy/hallucinations** - Religious content is sensitive; errors are serious
2. **Will I actually use it?** - Must reduce friction enough to become the default way to explore

---

## User Profile & Workflow

### Study Pattern
- **Event-driven**: Questions arise from Friday sermons, life situations, conversations, curiosity spirals
- **Go deeper immediately**: Conversation-first exploration, follow threads in the moment
- **Mix of query types**: Vague exploration ("tell me about prayer"), specific questions ("conditions for prayer acceptance"), reference lookups ("what did Khalifa IV say about X in book Y")

### Current Workflow (to replace)
- Doesn't currently read because friction is too high
- The chatbot surfaces what to read and explains it conversationally

---

## Core Requirements

### 1. Source Attribution & Authority

**Source Hierarchy (Critical)**
```
Quran > Hadith > Promised Messiah > Khalifas > Other Scholars
```

**Attribution Rules:**
- Always show who said what with clear breakdown
- Never blend sources into anonymous synthesis
- Display source authority level visibly
- Sources within the Ahmadiyya tradition should generally agree—highlight when they don't

### 2. Citation & Verification

**One-Click Verification (Required)**
- Every citation must deep-link to the exact page/paragraph on alislam.org
- User should be able to verify any claim with a single click
- Capture URLs during scraping, store with chunks

**Citation Format:**
```
[Source: Book Title, Chapter, Page] → clickable link to alislam.org
```

### 3. Knowledge Gap Handling

**When corpus doesn't have an answer:**
- Clearly state the topic isn't covered in indexed sources
- **Suggest where to look**: Point to books/sections that might cover it (even if not yet indexed)
- Do NOT use general AI knowledge to fill gaps—stay grounded

### 4. Contradiction Handling

**When sources appear to conflict:**
- **Flag for review** - highlight as something requiring careful study
- Show both viewpoints with full context
- Do NOT auto-resolve or pick sides
- Let user investigate and decide

### 5. Language Display

**Arabic/Urdu Text:**
- Show original + English translation side by side
- For Quranic verses: context-aware expansion
  - Important verses (main point): expand with full Arabic + translation
  - Minor references: show reference number, link to full verse

### 6. Conversation Design

**Broad Query Handling:**
- Return **structured outline** breaking topic into sub-topics
- Let user drill down into specific areas
- Don't overwhelm with a single massive response

**Conversation Memory:**
- Full context within a conversation session
- "What else did he say about this?" should work
- "He" refers to whoever was discussed earlier

**Follow-up Exploration:**
- Support natural follow-up questions
- Enable curiosity spirals—one thought leading to another

### 7. Related Content Suggestions

- **On request only** - don't proactively suggest
- When asked: "Show me related topics" → provide suggestions
- Don't distract during deep exploration

---

## Content-Specific Requirements

### Books
- Index by chapter/section structure
- Preserve author, title, language, publication info
- Page numbers for citation

### Friday Sermons (Rich Handling)

| Feature | Description |
|---------|-------------|
| Full chunks | Index entire sermons for retrieval |
| Summaries | Generate sermon summaries for overview |
| Topic extraction | Break into discrete topics for precise retrieval |
| Chronological context | Always show when given + historical context |

### Quran References
- Detect verse references in text (e.g., "2:256")
- Context-aware expansion:
  - Central to the argument → show full verse + Arabic + translation
  - Supporting reference → show reference, link to full

---

## Technical Decisions

### Architecture
```
[alislam.org] → [Scraper] → [Chunker] → [Embeddings] → [Qdrant]
                                                          ↓
[User Query] → [Vector Search] → [Rerank] → [Claude] → [Response]
                                                          ↓
                                               [Citations with deep links]
```

### Stack
| Component | Choice | Rationale |
|-----------|--------|-----------|
| Backend | Python (FastAPI) | Simple, good ecosystem |
| Scraping | BeautifulSoup + requests | HTML-first approach |
| Vector DB | Qdrant (Docker) | Free, powerful filtering |
| Embeddings | OpenAI text-embedding-3-large | Best multilingual support |
| LLM | Claude API | Long context, nuanced responses |
| UI (MVP) | CLI first | Cut UI if needed, add later |
| UI (Later) | Streamlit or Next.js | Simple web interface |

### Cost Tolerance
- **$10-30/month for Claude API is acceptable**
- Worth it for good experience
- Embedding costs are mostly one-time

### MVP Priorities (What to Cut First)
1. **Cut web UI** - CLI is acceptable for testing
2. Keep: Books from one author, vector search, Claude chat, citations

---

## Metadata Schema

```json
{
  "id": "uuid",
  "content": "chunk text",
  "source_type": "book|sermon|article",
  "authority_level": "quran|hadith|promised_messiah|khalifa|scholar",
  "book_title": "Philosophy of the Teachings of Islam",
  "author": "Hazrat Mirza Ghulam Ahmad",
  "author_slug": "promised-messiah",
  "chapter": "Chapter 2: The State of Man After Death",
  "page_number": 45,
  "language": "english",
  "original_url": "https://www.alislam.org/library/books/...",
  "chunk_index": 12,
  "sermon_date": null,
  "historical_context": null
}
```

---

## Prompt Engineering

### System Prompt (Draft)
```
You are a study assistant for Islamic texts from the Ahmadiyya Muslim Community.

CRITICAL RULES:
1. Use ONLY the provided context to answer. Never use outside knowledge.
2. If the answer isn't in the context, say: "This topic isn't covered in the indexed sources. You might find it in [suggest relevant unindexed books]."
3. Always cite sources with the format: [Book Title, Chapter, Page]
4. Show who said what—keep sources distinct, don't blend into anonymous synthesis.
5. Respect source authority: Quran > Hadith > Promised Messiah > Khalifas > Scholars
6. If sources appear to conflict, FLAG IT: "Note: These sources may present different perspectives. Review carefully."
7. For Quranic verses central to the answer, show Arabic + translation.

FOR BROAD QUESTIONS:
- Provide a structured outline of sub-topics
- Let the user choose which to explore deeper

CONVERSATION CONTEXT:
- Remember full conversation context
- Support follow-up questions naturally
```

---

## Development Roadmap

### Phase A: MVP (One Author)

**Infrastructure**
- [ ] Python project with uv/poetry
- [ ] Qdrant via Docker
- [ ] API keys configured

**Scraper**
- [ ] Fetch book list for one author from alislam.org
- [ ] Parse book HTML: chapters, content, metadata
- [ ] Cache raw HTML locally
- [ ] Capture original URLs for deep linking

**Processing**
- [ ] Chunk by chapter/section (~512-1024 tokens)
- [ ] Extract and normalize metadata
- [ ] Generate embeddings
- [ ] Store in Qdrant with full metadata

**Chat (CLI)**
- [ ] Vector similarity search
- [ ] Claude integration with citation prompt
- [ ] Display responses with clickable citations
- [ ] Conversation memory within session

**Verification**
- [ ] Test: Factual query → correct source retrieved
- [ ] Test: Citation link → opens correct page on alislam.org
- [ ] Test: Follow-up question → context maintained

### Phase B: Expand Coverage
- [ ] Add remaining authors
- [ ] Add Friday sermons with rich metadata
- [ ] Implement hybrid search (BM25 + vector)
- [ ] Add reranking layer

### Phase C: Web UI
- [ ] Streamlit or Next.js interface
- [ ] Chat with citations
- [ ] Conversation history (searchable)

### Phase D: Extended Sources
- [ ] Al Hakam, Review of Religions
- [ ] MTA sermon transcripts
- [ ] Classical Islamic texts

---

## Incremental Scope

| Phase | Content | Features |
|-------|---------|----------|
| A | Books from 1 author | CLI chat, citations, basic search |
| B | All authors' books | Hybrid search, reranking |
| C | Friday sermons | Topic extraction, summaries |
| D | Other sources | Al Hakam, classical texts |

---

## Operational Considerations

### Content Updates
- **Manual re-scrape** when I want new content
- No automated pipelines needed initially
- Sermons added weekly on alislam.org—update when desired

### Resumability (All Critical)
1. **Documentation**: Clear README, setup instructions
2. **Simple architecture**: Few dependencies, standard patterns
3. **State persistence**: All scraped/indexed data preserved

### Future Sharing
- May share with family/Jamaat eventually
- Design for single-user now, but keep multi-user possible later

---

## Verification & Testing

### Test Queries
1. **Factual**: "What did the Promised Messiah say about prayer?"
2. **Specific**: "What are the conditions for prayer to be accepted?"
3. **Reference**: "What does Khalifa IV say about Jihad in Islam's Response to Contemporary Issues?"
4. **Broad**: "What is Islam's view on marriage?" → should return structured outline
5. **Follow-up**: After above, "Tell me more about the rights of spouses"
6. **Missing**: Query about topic not in corpus → should suggest where to look
7. **Cross-reference**: "Find all references to Surah Al-Fatiha"

### Success Criteria
- [ ] Relevant chunks retrieved (manual verification)
- [ ] Citations link to correct source
- [ ] Source authority clearly displayed
- [ ] Conversation context maintained
- [ ] Knowledge gaps handled gracefully (suggest alternatives)
- [ ] No hallucinations—grounded responses only

---

## Cost Estimates

| Component | MVP (1 Author) | Full Corpus |
|-----------|----------------|-------------|
| Embeddings | ~$5-10 | ~$50-100 |
| Vector DB (Qdrant) | Free | Free |
| Claude API | ~$10-20/month | ~$20-40/month |

---

## Project Structure

```
islamic-kb/
├── scraper/
│   ├── alislam.py           # Main scraper
│   ├── book_parser.py       # Book content extraction
│   ├── sermon_parser.py     # Sermon parsing
│   └── cache.py             # Local caching
├── processing/
│   ├── chunker.py           # Semantic chunking
│   ├── cleaner.py           # Text normalization
│   └── metadata.py          # Metadata extraction
├── indexing/
│   ├── embedder.py          # OpenAI embeddings
│   └── store.py             # Qdrant client
├── retrieval/
│   ├── search.py            # Hybrid search
│   └── rerank.py            # Reranking
├── chat/
│   ├── client.py            # Claude API
│   ├── prompts.py           # System prompts
│   └── memory.py            # Conversation context
├── cli/
│   └── main.py              # CLI interface
├── api/
│   └── main.py              # FastAPI (later)
├── web/
│   └── (Streamlit/Next.js)  # Web UI (later)
├── data/
│   ├── raw/                 # Cached HTML
│   └── processed/           # Chunked content
├── tests/
│   └── ...
├── pyproject.toml
└── README.md
```

---

## Key Dependencies

```toml
[project]
name = "islamic-kb"
requires-python = ">=3.11"

dependencies = [
    # Core
    "fastapi>=0.109",
    "uvicorn>=0.27",
    "qdrant-client>=1.7",
    "openai>=1.12",
    "anthropic>=0.18",

    # Scraping
    "beautifulsoup4>=4.12",
    "requests>=2.31",
    "lxml>=5.1",

    # Processing
    "tiktoken>=0.6",

    # CLI
    "rich>=13.0",
    "typer>=0.9",
]
```
