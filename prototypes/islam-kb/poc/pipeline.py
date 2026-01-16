#!/usr/bin/env python3
"""
RAG Pipeline: Extract text from PDFs, chunk, embed, and store in Qdrant.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, asdict

import fitz  # PyMuPDF
import tiktoken
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Configuration
CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 50  # tokens
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMS = 3072
COLLECTION_NAME = "islamic_books"

PDF_DIR = Path(__file__).parent / "pdfs"
CHUNKS_DIR = Path(__file__).parent / "chunks"
QDRANT_PATH = Path(__file__).parent / "qdrant_data"


# Common Islamic names that may have honorifics attached
ISLAMIC_NAMES = {
    # Female companions and family
    "Khadijah", "Khadija", "Aisha", "Ayesha", "Fatimah", "Fatima",
    "Hafsa", "Hafsah", "Maryam", "Mariam", "Zainab", "Zaynab",
    "Safiyyah", "Safiyya", "Maymunah", "Maimuna", "Sawdah", "Sawda",
    "Juwayriyah", "Juwairiya", "Umm", "Asma", "Sumayyah", "Sumayya",
    # Male companions
    "Abu", "Umar", "Uthman", "Ali", "Zaid", "Zayd", "Bilal",
    "Hamza", "Hamzah", "Abbas", "Khalid", "Salman", "Ammar",
    "Muadh", "Saad", "Sa'd", "Talha", "Talhah", "Zubair", "Zubayr",
    "Abdur", "Abdul", "Anas", "Jabir", "Hudhaifa", "Hudhayfah",
    # Prophets
    "Ibrahim", "Ibraheem", "Musa", "Moosa", "Isa", "Eisa",
    "Nuh", "Nooh", "Yusuf", "Yaqub", "Ishaq", "Ismail",
    "Dawud", "Dawood", "Sulaiman", "Suleiman", "Yunus", "Younus",
    "Ayyub", "Ayub", "Zakariya", "Zakariyya", "Yahya", "Yahiya",
    "Idris", "Hud", "Salih", "Shuaib", "Lut", "Adam",
    "Jesus", "Christ", "Moses", "Abraham", "Noah", "Joseph",
    # The Prophet
    "Muhammad", "Mohammed", "Mohammad", "Prophet", "Messenger",
    # Ahmadiyya specific
    "Mirza", "Ghulam", "Ahmad", "Masroor", "Tahir", "Bashir",
    "Mahmud", "Mahmood",
    # Titles that may precede names
    "Hadhrat", "Hadrat", "Hazrat", "Syedna", "Sayyidina",
}

# Honorific patterns (lowercase) - order matters, longer ones first
HONORIFICS = ["pbuh", "saw", "rta", "aba", "ata", "ra", "sa", "as", "rh"]


def normalize_honorifics(text: str) -> str:
    """
    Fix honorifics that got merged with names during PDF extraction.
    e.g., "Khadijahra" -> "Khadijah(ra)", "Muhammadsaw" -> "Muhammad(saw)"
    """
    result = text

    # Pattern 1: Known name + honorific directly attached
    # Process longer honorifics first to avoid partial matches
    for hon in HONORIFICS:
        for name in ISLAMIC_NAMES:
            # Case-insensitive pattern for name+honorific at word boundary
            pattern = rf'\b({name})({hon})\b'
            replacement = rf'\1({hon})'
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Pattern 2: Generic pattern for names not in our list
    # Look for words ending in common Arabic name endings + honorific
    for hon in HONORIFICS:
        # Match names ending in -ah, -a, -i, -d, -r, -n, -m, -s, -b, -l + honorific
        # But only at actual word boundaries
        pattern = rf'\b([A-Z][a-z]*[ahindrmsbl])({hon})\b'

        def replace_if_valid(match):
            name_part = match.group(1)
            hon_part = match.group(2)
            full = match.group(0).lower()
            # Skip common English words
            skip_words = {'extra', 'ultra', 'aura', 'flora', 'zebra', 'cobra',
                         'opera', 'camera', 'era', 'umbrella', 'formula',
                         'was', 'has', 'is', 'as'}
            if full in skip_words or name_part.lower() in skip_words:
                return match.group(0)
            # Skip if name part is too short (likely not a name)
            if len(name_part) < 3:
                return match.group(0)
            return f"{name_part}({hon_part})"

        result = re.sub(pattern, replace_if_valid, result)

    return result


@dataclass
class Chunk:
    text: str
    book: str
    page: int
    chunk_index: int
    pdf_filename: str

    def to_dict(self):
        return asdict(self)


def extract_text_from_pdf(pdf_path: Path) -> list[tuple[int, str]]:
    """Extract text from PDF, returning list of (page_num, text) tuples."""
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():
            # Normalize honorifics that got merged with names
            text = normalize_honorifics(text)
            pages.append((page_num, text))
    doc.close()
    return pages


def count_tokens(text: str, encoding) -> int:
    """Count tokens in text."""
    return len(encoding.encode(text))


def chunk_text(
    pages: list[tuple[int, str]],
    book_name: str,
    pdf_filename: str,
    encoding,
) -> list[Chunk]:
    """
    Chunk text using a sliding window approach with overlap.
    Respects page boundaries where possible.
    """
    chunks = []
    chunk_index = 0

    # Combine all text with page markers
    current_text = ""
    current_page = pages[0][0] if pages else 1
    current_tokens = 0

    for page_num, page_text in pages:
        # Clean the text
        page_text = re.sub(r'\s+', ' ', page_text).strip()
        page_tokens = count_tokens(page_text, encoding)

        # If adding this page would exceed chunk size, save current chunk
        if current_tokens + page_tokens > CHUNK_SIZE and current_text:
            chunks.append(Chunk(
                text=current_text.strip(),
                book=book_name,
                page=current_page,
                chunk_index=chunk_index,
                pdf_filename=pdf_filename,
            ))
            chunk_index += 1

            # Keep overlap from the end of current text
            overlap_text = get_overlap_text(current_text, CHUNK_OVERLAP, encoding)
            current_text = overlap_text
            current_tokens = count_tokens(overlap_text, encoding)
            current_page = page_num

        current_text += " " + page_text
        current_tokens += page_tokens

        # If current chunk is too large, split it
        while current_tokens > CHUNK_SIZE:
            # Find a good split point
            split_text, remaining_text = split_at_token_limit(
                current_text, CHUNK_SIZE, encoding
            )

            chunks.append(Chunk(
                text=split_text.strip(),
                book=book_name,
                page=current_page,
                chunk_index=chunk_index,
                pdf_filename=pdf_filename,
            ))
            chunk_index += 1

            # Keep overlap
            overlap_text = get_overlap_text(split_text, CHUNK_OVERLAP, encoding)
            current_text = overlap_text + remaining_text
            current_tokens = count_tokens(current_text, encoding)

    # Don't forget the last chunk
    if current_text.strip():
        chunks.append(Chunk(
            text=current_text.strip(),
            book=book_name,
            page=current_page,
            chunk_index=chunk_index,
            pdf_filename=pdf_filename,
        ))

    return chunks


def get_overlap_text(text: str, overlap_tokens: int, encoding) -> str:
    """Get the last N tokens of text as overlap."""
    tokens = encoding.encode(text)
    if len(tokens) <= overlap_tokens:
        return text
    overlap_tokens_list = tokens[-overlap_tokens:]
    return encoding.decode(overlap_tokens_list)


def split_at_token_limit(text: str, limit: int, encoding) -> tuple[str, str]:
    """Split text at approximately the token limit, preferring sentence boundaries."""
    tokens = encoding.encode(text)
    if len(tokens) <= limit:
        return text, ""

    # Decode up to the limit
    split_text = encoding.decode(tokens[:limit])

    # Try to find a sentence boundary
    for sep in ['. ', '.\n', '? ', '!\n', '\n\n']:
        last_sep = split_text.rfind(sep)
        if last_sep > len(split_text) // 2:  # Don't split too early
            split_point = last_sep + len(sep)
            return text[:split_point], text[split_point:]

    # Fall back to word boundary
    last_space = split_text.rfind(' ')
    if last_space > 0:
        return text[:last_space], text[last_space:]

    return split_text, text[len(split_text):]


def get_book_name(pdf_filename: str) -> str:
    """Convert PDF filename to a readable book name."""
    name = pdf_filename.replace('.pdf', '')
    name = name.replace('-', ' ').replace('_', ' ')
    # Title case but preserve acronyms
    words = name.split()
    return ' '.join(w if w.isupper() else w.title() for w in words)


def embed_chunks(chunks: list[Chunk], client: OpenAI) -> list[list[float]]:
    """Generate embeddings for chunks using OpenAI."""
    texts = [c.text for c in chunks]

    # Batch requests (max 2048 inputs per request for OpenAI)
    all_embeddings = []
    batch_size = 100

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"    Embedding batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}")

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        batch_embeddings = [e.embedding for e in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


def chunk_id(chunk: Chunk) -> str:
    """Generate a unique ID for a chunk."""
    content = f"{chunk.pdf_filename}:{chunk.page}:{chunk.chunk_index}"
    return hashlib.md5(content.encode()).hexdigest()


def setup_qdrant(client: QdrantClient):
    """Set up Qdrant collection."""
    collections = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMS,
                distance=Distance.COSINE,
            ),
        )
        print(f"Created collection: {COLLECTION_NAME}")
    else:
        print(f"Collection {COLLECTION_NAME} already exists")


def store_chunks(
    chunks: list[Chunk],
    embeddings: list[list[float]],
    qdrant: QdrantClient,
):
    """Store chunks and embeddings in Qdrant."""
    points = []
    for chunk, embedding in zip(chunks, embeddings):
        point = PointStruct(
            id=chunk_id(chunk),
            vector=embedding,
            payload=chunk.to_dict(),
        )
        points.append(point)

    # Upsert in batches
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        qdrant.upsert(collection_name=COLLECTION_NAME, points=batch)


def process_pdf(
    pdf_path: Path,
    encoding,
    openai_client: OpenAI,
    qdrant_client: QdrantClient,
) -> int:
    """Process a single PDF file. Returns number of chunks created."""
    print(f"\nProcessing: {pdf_path.name}")

    # Extract text
    print("  Extracting text...")
    pages = extract_text_from_pdf(pdf_path)
    if not pages:
        print("  No text found, skipping")
        return 0

    # Chunk
    print("  Chunking...")
    book_name = get_book_name(pdf_path.name)
    chunks = chunk_text(pages, book_name, pdf_path.name, encoding)
    print(f"  Created {len(chunks)} chunks")

    # Save chunks to JSON for inspection
    chunks_file = CHUNKS_DIR / f"{pdf_path.stem}.json"
    with open(chunks_file, 'w') as f:
        json.dump([c.to_dict() for c in chunks], f, indent=2)

    # Embed
    print("  Embedding...")
    embeddings = embed_chunks(chunks, openai_client)

    # Store
    print("  Storing in Qdrant...")
    store_chunks(chunks, embeddings, qdrant_client)

    return len(chunks)


def main():
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    # Setup
    CHUNKS_DIR.mkdir(exist_ok=True)
    QDRANT_PATH.mkdir(exist_ok=True)

    encoding = tiktoken.encoding_for_model("gpt-4")
    openai_client = OpenAI()
    qdrant_client = QdrantClient(path=str(QDRANT_PATH))

    setup_qdrant(qdrant_client)

    # Process all PDFs
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files")

    total_chunks = 0
    for pdf_path in pdf_files:
        chunks = process_pdf(pdf_path, encoding, openai_client, qdrant_client)
        total_chunks += chunks

    print(f"\n{'='*50}")
    print(f"Total chunks created: {total_chunks}")
    print(f"Chunks saved to: {CHUNKS_DIR}")
    print(f"Qdrant data saved to: {QDRANT_PATH}")


if __name__ == "__main__":
    main()
