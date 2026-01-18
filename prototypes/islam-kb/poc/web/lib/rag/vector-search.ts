import { QdrantClient } from "@qdrant/js-client-rest";
import OpenAI from "openai";
import { SearchResult } from "./types";

const EMBEDDING_MODEL = "text-embedding-3-large";
const COLLECTION_NAME = "islamic_books";
const TOP_K = 10;

// Singleton clients
let qdrantClient: QdrantClient | null = null;
let openaiClient: OpenAI | null = null;

function getQdrantClient(): QdrantClient {
  if (!qdrantClient) {
    qdrantClient = new QdrantClient({
      url: process.env.QDRANT_URL || "http://localhost:6333",
      checkCompatibility: false,
    });
  }
  return qdrantClient;
}

function getOpenAIClient(): OpenAI {
  if (!openaiClient) {
    openaiClient = new OpenAI();
  }
  return openaiClient;
}

async function getEmbedding(text: string): Promise<number[]> {
  const openai = getOpenAIClient();
  const response = await openai.embeddings.create({
    model: EMBEDDING_MODEL,
    input: text,
  });
  return response.data[0].embedding;
}

export async function searchQdrant(query: string): Promise<SearchResult[]> {
  const qdrant = getQdrantClient();
  const queryEmbedding = await getEmbedding(query);

  const results = await qdrant.search(COLLECTION_NAME, {
    vector: queryEmbedding,
    limit: TOP_K,
    with_payload: true,
  });

  return results.map((r) => ({
    text: r.payload?.text as string,
    book: r.payload?.book as string,
    page: r.payload?.page as number,
    score: r.score,
  }));
}
