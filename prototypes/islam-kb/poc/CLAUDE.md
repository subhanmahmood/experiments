# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG (Retrieval-Augmented Generation) proof-of-concept for an Islamic knowledge base. It scrapes books from alislam.org, chunks and embeds them, stores vectors in Qdrant, and provides a chat interface for querying the knowledge base.

## Commands

### Python Backend

```bash
# Setup (from poc/ directory)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Download PDFs from alislam.org
python download_books.py

# Process PDFs: extract text, chunk, embed, store in Qdrant
# Requires OPENAI_API_KEY environment variable
python pipeline.py

# Query the knowledge base
python query.py "your question here"          # Single query
python query.py                                # Interactive mode
python query.py --stream "your question"      # Streaming output for TUI
```

### TUI (Terminal UI)

```bash
cd tui
npm install
npm start       # Run the TUI
npm run dev     # Run with watch mode
```

### Web Interface (Next.js)

```bash
cd web
npm install
npm run dev     # Development server at http://localhost:3000
npm run build   # Production build
```

Features:
- Chat UI with GPT-4o and tool-calling
- Dual search: Islamic texts (Qdrant) + web search (OpenAI built-in)
- Interactive citations with source modal
- Streaming markdown with Streamdown

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────┐
│ alislam.org │────▶│ download_    │────▶│ pipeline.py │────▶│ Qdrant  │
│   (PDFs)    │     │ books.py     │     │ (chunk+embed)│     │ (local) │
└─────────────┘     └──────────────┘     └─────────────┘     └────┬────┘
                                                                  │
                    ┌──────────────┐     ┌─────────────┐     ┌────▼────┐
                    │ query.py     │◀────│ OpenAI      │◀────│ Vector  │
                    │ TUI or Web   │     │ GPT-4o      │     │ Search  │
                    └──────────────┘     └─────────────┘     └─────────┘
```

**Data Flow:**
1. `download_books.py` - Scrapes PDF links from alislam.org and downloads them to `pdfs/`
2. `pipeline.py` - Extracts text via PyMuPDF, chunks with 512-token sliding window (50 overlap), embeds with OpenAI text-embedding-3-large, stores in Qdrant
3. `query.py` - Embeds query, searches Qdrant for top-k chunks, sends to LLM with system prompt for RAG response
4. `tui/` - React/Ink terminal interface that spawns query.py with `--stream` and renders results
5. `web/` - Next.js web interface with AI SDK, tool-calling, and interactive citations

**Key Configuration (in source files):**
- `CHUNK_SIZE = 512` tokens, `CHUNK_OVERLAP = 50` tokens
- `EMBEDDING_MODEL = "text-embedding-3-large"` (3072 dims)
- `COLLECTION_NAME = "islamic_books"` in Qdrant
- `TOP_K = 10` chunks retrieved per query

## Directories

- `pdfs/` - Downloaded PDF files
- `chunks/` - JSON files with chunked text (for inspection)
- `qdrant_data/` - Local Qdrant database files (or `qdrant/` for Docker)
- `.venv/` - Python virtual environment
- `tui/` - Terminal UI (React/Ink)
- `web/` - Web interface (Next.js)

## Environment Variables

- `OPENAI_API_KEY` - Required for embedding and LLM calls
