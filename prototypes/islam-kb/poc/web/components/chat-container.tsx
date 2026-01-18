"use client";

import { useChat } from "@ai-sdk/react";
import { useState, useRef, useEffect } from "react";
import { Streamdown } from "streamdown";
import { SourceModal } from "./source-modal";
import { Source } from "@/lib/rag/types";

export function ChatContainer() {
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [sourcesMap, setSourcesMap] = useState<Record<string, Source[]>>({});
  const [toolStatus, setToolStatus] = useState<{
    status: "searching" | "complete" | null;
    query?: string;
  }>({ status: null });
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { messages, status, sendMessage, error } = useChat({});

  // Extract sources and tool status from message parts
  useEffect(() => {
    messages.forEach((m) => {
      if (m.role === "assistant" && m.parts) {
        for (const part of m.parts) {
          // Check for data-tool-status type
          if (part.type === "data-tool-status" && "data" in part) {
            const data = part.data as { status: "searching" | "complete"; query?: string };
            if (data.status === "searching") {
              setToolStatus({ status: "searching", query: data.query });
            } else if (data.status === "complete") {
              setToolStatus({ status: null });
            }
          }
          // Check for data-sources type
          if (part.type === "data-sources" && "data" in part && !sourcesMap[m.id]) {
            const data = (part as { type: string; data: Source[] }).data;
            if (Array.isArray(data) && data.length > 0) {
              setSourcesMap((prev) => ({
                ...prev,
                [m.id]: data,
              }));
            }
          }
        }
      }
    });
  }, [messages, sourcesMap]);


  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || status !== "ready") return;

    sendMessage({ text: input });
    setInput("");
  };

  const isLoading = status === "submitted" || status === "streaming";

  // Extract text content from message parts
  const getMessageText = (
    message: (typeof messages)[0]
  ): string => {
    if (!message.parts) return "";
    return message.parts
      .filter((part): part is { type: "text"; text: string } => part.type === "text")
      .map((part) => part.text)
      .join("");
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      {/* Header */}
      <header className="p-4 border-b">
        <h1 className="text-2xl font-bold">Islamic Knowledge Base</h1>
        <p className="text-sm text-muted-foreground">
          Ask questions about Ahmadiyya Islamic literature
        </p>
      </header>

      {/* Chat Area */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 space-y-6">
            <p className="text-muted-foreground">Ask a question to get started</p>
            <div className="grid gap-2 w-full max-w-md">
              {[
                "What is Khatam-un-Nabiyyin?",
                "Who was the Promised Messiah?",
                "What is the Ahmadiyya view on Jihad?",
                "Explain the concept of Khilafat",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setInput(suggestion);
                  }}
                  className="text-left px-4 py-3 rounded-lg border hover:bg-muted transition-colors text-sm"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex flex-col ${
              message.role === "user" ? "items-end" : "items-start"
            }`}
          >
            {/* Message bubble */}
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                message.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              }`}
            >
              {message.role === "user" ? (
                <p className="whitespace-pre-wrap">{getMessageText(message)}</p>
              ) : (
                <div className="prose prose-sm dark:prose-invert max-w-none font-serif">
                  <Streamdown
                    components={{
                      a: ({ href, children }) => {
                        // Handle source: links as clickable citation buttons
                        if (href?.startsWith("source:")) {
                          const idx = parseInt(href.replace("source:", ""), 10);
                          const source = sourcesMap[message.id]?.[idx];
                          if (source) {
                            return (
                              <button
                                onClick={() => setSelectedSource(source)}
                                className="text-primary hover:underline font-medium"
                              >
                                {children}
                              </button>
                            );
                          }
                          // Source not found, render as plain text
                          return <span className="text-muted-foreground">{children}</span>;
                        }
                        // Regular links
                        return (
                          <a href={href} target="_blank" rel="noopener noreferrer">
                            {children}
                          </a>
                        );
                      },
                    }}
                  >
                    {getMessageText(message)}
                  </Streamdown>
                </div>
              )}
            </div>

            {/* Sources (for assistant messages) */}
            {message.role === "assistant" && sourcesMap[message.id] && (
              <div className="mt-2 flex flex-wrap gap-2">
                {sourcesMap[message.id].map((source) => (
                  <button
                    key={source.id}
                    onClick={() => setSelectedSource(source)}
                    className="text-xs px-2 py-1 rounded bg-secondary hover:bg-secondary/80 transition-colors"
                  >
                    {source.book} p.{source.page}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex items-start">
            <div className="bg-muted rounded-lg px-4 py-2">
              {toolStatus.status === "searching" ? (
                <div className="flex items-center gap-2">
                  <svg
                    className="animate-spin h-4 w-4"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  <span>
                    Searching: <em>&quot;{toolStatus.query}&quot;</em>
                  </span>
                </div>
              ) : (
                <span className="animate-pulse">
                  {status === "submitted" ? "Thinking..." : "Generating..."}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Error display */}
        {error && (
          <div className="flex items-start">
            <div className="bg-destructive/10 text-destructive rounded-lg px-4 py-2">
              <span>Error: {error.message}</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              messages.length === 0 ? "Ask a question..." : "Ask a follow-up..."
            }
            disabled={isLoading}
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary bg-background"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </form>
      </div>

      {/* Source Modal */}
      <SourceModal
        source={selectedSource}
        onClose={() => setSelectedSource(null)}
      />
    </div>
  );
}
