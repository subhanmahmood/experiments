import {
  streamText,
  UIMessage,
  convertToModelMessages,
  createUIMessageStream,
  createUIMessageStreamResponse,
  tool,
  stepCountIs,
} from "ai";
import { openai } from "@ai-sdk/openai";
import { z } from "zod";
import { searchQdrant } from "@/lib/rag/vector-search";
import { SYSTEM_PROMPT, formatContext } from "@/lib/rag/prompts";

export const maxDuration = 60;

// Web search tool for current events and external information
const webSearchTool = openai.tools.webSearch({});

// Define Islamic texts search tool
const searchTool = tool({
  description:
    "Search the Islamic knowledge base for information from books by Ahmadiyya scholars and Khulafa. Use when you need factual information, quotes, or theological details not already covered in our conversation.",
  inputSchema: z.object({
    query: z
      .string()
      .describe("The search query - be specific about what information you need"),
  }),
  execute: async ({ query }) => {
    const searchResults = await searchQdrant(query);
    return {
      context: formatContext(searchResults),
      sources: searchResults.slice(0, 5).map((r, i) => ({
        id: `source-${i}`,
        book: r.book,
        page: r.page,
        score: r.score,
        text: r.text,
      })),
    };
  },
});

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();

  // Validate we have a query
  const userMessages = messages.filter((m) => m.role === "user");
  if (userMessages.length === 0) {
    return new Response("No query provided", { status: 400 });
  }

  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      const modelMessages = await convertToModelMessages(messages);

      const result = streamText({
        model: openai("gpt-4o"),
        system: SYSTEM_PROMPT,
        messages: modelMessages,
        tools: {
          search_islamic_texts: searchTool,
          web_search: webSearchTool,
        },
        stopWhen: stepCountIs(3),
        temperature: 0.3,
        onChunk: ({ chunk }) => {
          // Notify client when tool is being called
          if (chunk.type === "tool-call") {
            const input = chunk.input as { query?: string } | undefined;
            writer.write({
              type: "data-tool-status",
              data: {
                status: "searching",
                toolName: chunk.toolName,
                query: input?.query,
              },
            });
          }
        },
        onStepFinish: async (event) => {
          // When tool results come back, send sources to client
          if (event.toolResults) {
            for (const toolResult of event.toolResults) {
              if (toolResult.toolName === "search_islamic_texts") {
                const output = toolResult.output as {
                  context: string;
                  sources: Array<{
                    id: string;
                    book: string;
                    page: number;
                    score: number;
                    text: string;
                  }>;
                };
                // Notify client that search is complete
                writer.write({
                  type: "data-tool-status",
                  data: {
                    status: "complete",
                    toolName: toolResult.toolName,
                  },
                });
                if (output?.sources) {
                  writer.write({
                    type: "data-sources",
                    data: output.sources,
                  });
                }
              }
            }
          }
        },
      });

      writer.merge(result.toUIMessageStream());
    },
  });

  return createUIMessageStreamResponse({ stream });
}
