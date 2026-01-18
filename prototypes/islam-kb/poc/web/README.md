# Islamic Knowledge Base - Web Interface

A Next.js chat interface for querying Ahmadiyya Islamic literature using RAG (Retrieval-Augmented Generation).

## Features

- **AI-powered chat** with GPT-4o
- **Dual search tools**:
  - `search_islamic_texts` - Search the embedded knowledge base of Ahmadiyya books
  - `web_search` - Search the internet for current events and news
- **Interactive citations** - Click inline citations to view source text
- **Streaming responses** with Streamdown markdown rendering
- **Elegant typography** - Lora serif font for AI responses

## Setup

### 1. Prerequisites

- Node.js 18+
- Python 3.11+ (for data pipeline)
- Docker (for Qdrant) or Qdrant installed locally

### 2. Environment Variables

Create `.env.local` in the `web/` directory:

```bash
OPENAI_API_KEY=sk-your-openai-api-key
QDRANT_URL=http://localhost:6333
```

### 3. Install & Start Qdrant

**Option A: Docker (recommended)**
```bash
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant:/qdrant/storage \
  qdrant/qdrant
```

**Option B: Homebrew (macOS)**
```bash
brew install qdrant/tap/qdrant
qdrant --storage-path ./qdrant_data
```

**Option C: Binary download**
```bash
# Download from https://github.com/qdrant/qdrant/releases
# Extract and run:
./qdrant --storage-path ./qdrant_data
```

**Option D: Qdrant Cloud (hosted)**
1. Create account at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a cluster and get your URL + API key
3. Update `.env.local`:
   ```bash
   QDRANT_URL=https://your-cluster.qdrant.io
   QDRANT_API_KEY=your-api-key
   ```

Verify Qdrant is running: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

### 4. Populate the Knowledge Base (if not done)

From the parent `poc/` directory:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download books from alislam.org
python download_books.py

# Process PDFs and populate Qdrant
python pipeline.py
```

This will:
- Download PDFs to `pdfs/`
- Extract text, chunk with 512-token windows
- Embed with OpenAI `text-embedding-3-large`
- Store vectors in Qdrant

### 5. Install Web Dependencies

```bash
cd web
npm install
```

### 6. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Production Build

```bash
npm run build
npm start
```

## Architecture

```
app/
├── api/chat/route.ts    # Chat API with tool-calling (Islamic texts + web search)
├── layout.tsx           # Root layout with fonts
├── page.tsx             # Main page
└── globals.css          # Tailwind + typography

components/
├── chat-container.tsx   # Main chat UI with Streamdown rendering
└── source-modal.tsx     # Modal for viewing source citations

lib/rag/
├── prompts.ts           # System prompt and context formatting
├── vector-search.ts     # Qdrant search integration
└── types.ts             # TypeScript types
```

## Key Dependencies

- `ai` / `@ai-sdk/openai` - Vercel AI SDK for streaming chat
- `streamdown` - Markdown rendering optimized for AI streaming
- `@tailwindcss/typography` - Prose styling for rendered content
- `@qdrant/js-client-rest` - Qdrant vector database client

## Troubleshooting

**"Connection refused" to Qdrant**
- Ensure Qdrant is running on port 6333
- Check `lib/rag/vector-search.ts` for the Qdrant URL

**No search results**
- Verify the knowledge base is populated: `python query.py "test"` from `poc/`
- Check that `OPENAI_API_KEY` is set for embeddings

**Web search not working**
- Web search uses OpenAI's built-in tool - ensure your API key has access
