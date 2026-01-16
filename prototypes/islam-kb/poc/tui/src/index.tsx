import React, { useState, useEffect } from "react";
import { render, Box, Text, useInput, useApp } from "ink";
import TextInput from "ink-text-input";
import { marked } from "marked";
import TerminalRenderer from "marked-terminal";
import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// When running from dist/, go up twice (dist -> tui -> poc)
const POC_DIR = path.join(__dirname, "../..");
const PYTHON_SCRIPT = path.join(POC_DIR, "query.py");
const VENV_PYTHON = path.join(POC_DIR, ".venv/bin/python");

// Configure marked with terminal renderer
marked.setOptions({
  renderer: new TerminalRenderer(),
});

interface Source {
  book: string;
  page: number;
  score: number;
  text: string;
}

interface ConversationTurn {
  question: string;
  answer: string;
  sources: Source[];
}

type AppState = "input" | "searching" | "streaming";

function Spinner() {
  const [frame, setFrame] = useState(0);
  const frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

  useEffect(() => {
    const timer = setInterval(() => {
      setFrame((f) => (f + 1) % frames.length);
    }, 80);
    return () => clearInterval(timer);
  }, []);

  return <Text color="yellow">{frames[frame]}</Text>;
}

function App() {
  const { exit } = useApp();
  const [query, setQuery] = useState("");
  const [state, setState] = useState<AppState>("input");
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [currentSources, setCurrentSources] = useState<Source[]>([]);
  const [conversation, setConversation] = useState<ConversationTurn[]>([]);
  const [status, setStatus] = useState("");
  const [selectedSource, setSelectedSource] = useState<number>(-1);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [error, setError] = useState("");

  useInput((input, key) => {
    if (key.ctrl && input === "c") {
      exit();
    }

    // Source navigation - only when viewing sources (not typing)
    if (selectedSource >= 0) {
      // Escape or 'q' to close source view
      if (key.escape || input === "\x1b" || input === "\u001b" || input === "q") {
        setSelectedSource(-1);
        return;
      }
      // Arrow keys or j/k to navigate
      if (key.downArrow || input === "j") {
        const lastTurn = conversation[conversation.length - 1];
        if (lastTurn?.sources.length > 0) {
          setSelectedSource((prev) => (prev + 1) % lastTurn.sources.length);
        }
        return;
      }
      if (key.upArrow || input === "k") {
        const lastTurn = conversation[conversation.length - 1];
        if (lastTurn?.sources.length > 0) {
          setSelectedSource((prev) =>
            prev === 0 ? lastTurn.sources.length - 1 : prev - 1
          );
        }
        return;
      }
    }

    // Number keys 1-5 to jump to specific source (works anytime when not typing in input)
    if (state === "input" && conversation.length > 0 && query === "") {
      const num = parseInt(input);
      if (num >= 1 && num <= 5) {
        const lastTurn = conversation[conversation.length - 1];
        if (lastTurn?.sources.length >= num) {
          setSelectedSource(num - 1);
          return;
        }
      }
      // 's' to toggle sources view
      if (input === "s") {
        const lastTurn = conversation[conversation.length - 1];
        if (lastTurn?.sources.length > 0) {
          setSelectedSource((prev) => (prev === -1 ? 0 : -1));
          return;
        }
      }
    }
  });

  const handleSubmit = (value: string) => {
    if (!value.trim()) return;

    // Handle slash commands
    const trimmed = value.trim().toLowerCase();
    if (trimmed === "/sources" || trimmed === "/s") {
      const lastTurn = conversation[conversation.length - 1];
      if (lastTurn?.sources.length > 0) {
        setSelectedSource(0);
        setQuery("");
      }
      return;
    }
    if (trimmed.startsWith("/source ") || trimmed.startsWith("/s ")) {
      const num = parseInt(trimmed.split(" ")[1]);
      const lastTurn = conversation[conversation.length - 1];
      if (num >= 1 && num <= 5 && lastTurn?.sources.length >= num) {
        setSelectedSource(num - 1);
        setQuery("");
      }
      return;
    }

    setState("searching");
    setStatus("Searching...");
    setCurrentAnswer("");
    setCurrentSources([]);
    setCurrentQuestion(value);
    setSelectedSource(-1);
    setQuery("");
    setError("");

    const proc = spawn(VENV_PYTHON, [PYTHON_SCRIPT, "--stream", value], {
      cwd: POC_DIR,
    });

    let fullOutput = "";
    let stderrOutput = "";

    proc.stdout.on("data", (data: Buffer) => {
      const text = data.toString();
      fullOutput += text;

      if (fullOutput.includes("---SOURCES---")) {
        const [answerPart, sourcesPart] = fullOutput.split("---SOURCES---");
        setCurrentAnswer(answerPart.trim());

        try {
          const parsedSources = JSON.parse(sourcesPart.trim());
          setCurrentSources(parsedSources);
        } catch {
          // Sources not fully received yet
        }
      } else {
        setState("streaming");
        setCurrentAnswer(fullOutput);
      }
    });

    proc.stderr.on("data", (data: Buffer) => {
      const text = data.toString().trim();
      stderrOutput += text + "\n";
      if (text.includes("Searching")) {
        setStatus("Searching knowledge base...");
      } else if (text.includes("Generating")) {
        setStatus("Generating answer...");
        setState("streaming");
      }
    });

    proc.on("close", (code) => {
      // Check for errors
      if (code !== 0 || (!fullOutput.trim() && stderrOutput.includes("Error"))) {
        // Extract error message
        const errorMatch = stderrOutput.match(/Error.*?:(.*?)(?:\n|$)/i)
          || stderrOutput.match(/(RateLimitError|insufficient_quota|exceeded.*quota)/i);
        const errorMsg = errorMatch
          ? errorMatch[0].trim()
          : "An error occurred. Check your API key and quota.";
        setError(errorMsg);
        setState("input");
        return;
      }

      // Parse answer and sources from full output
      let answer = fullOutput.trim();
      let parsedSources: Source[] = [];

      if (fullOutput.includes("---SOURCES---")) {
        const [answerPart, sourcesPart] = fullOutput.split("---SOURCES---");
        answer = answerPart.trim();
        try {
          parsedSources = JSON.parse(sourcesPart.trim());
        } catch {
          // Failed to parse sources
        }
      }

      if (answer) {
        setConversation((prev) => [
          ...prev,
          {
            question: value,
            answer,
            sources: parsedSources,
          },
        ]);
      }
      setState("input");
    });
  };

  // Update conversation with sources when they arrive
  useEffect(() => {
    if (currentSources.length > 0 && conversation.length > 0) {
      setConversation((prev) => {
        const updated = [...prev];
        if (updated.length > 0) {
          updated[updated.length - 1].sources = currentSources;
        }
        return updated;
      });
    }
  }, [currentSources]);

  const renderMarkdown = (text: string): string => {
    try {
      return marked.parse(text, { async: false }) as string;
    } catch {
      return text;
    }
  };

  const lastSources =
    conversation.length > 0
      ? conversation[conversation.length - 1].sources
      : [];

  return (
    <Box flexDirection="column" padding={1}>
      <Box marginBottom={1}>
        <Text bold color="cyan">
          Islamic Knowledge Base
        </Text>
        <Text color="gray"> (Ctrl+C to exit)</Text>
      </Box>

      {/* Conversation history */}
      {conversation.map((turn, turnIndex) => (
        <Box key={turnIndex} flexDirection="column" marginBottom={1}>
          {/* Question */}
          <Box>
            <Text color="green" bold>
              You:{" "}
            </Text>
            <Text>{turn.question}</Text>
          </Box>

          {/* Answer */}
          <Box marginTop={1} marginLeft={2}>
            <Box
              borderStyle="round"
              borderColor="gray"
              paddingX={1}
              flexDirection="column"
            >
              <Text>{renderMarkdown(turn.answer).trim()}</Text>
            </Box>
          </Box>

          {/* Sources summary (only show for last turn) */}
          {turnIndex === conversation.length - 1 && turn.sources.length > 0 && (
            <Box flexDirection="column" marginTop={1} marginLeft={2}>
              <Text color="cyan" dimColor>
                Sources ({turn.sources.length}):{" "}
                {turn.sources
                  .map((s, i) => `${s.book} p.${s.page}`)
                  .join(" • ")}
              </Text>
            </Box>
          )}
        </Box>
      ))}

      {/* Current streaming response */}
      {(state === "searching" || state === "streaming") && (
        <Box flexDirection="column" marginBottom={1}>
          <Box>
            <Text color="green" bold>
              You:{" "}
            </Text>
            <Text>{currentQuestion}</Text>
          </Box>

          <Box marginTop={1} marginLeft={2}>
            {state === "searching" ? (
              <Box>
                <Spinner />
                <Text color="gray"> {status}</Text>
              </Box>
            ) : (
              <Box
                borderStyle="round"
                borderColor="yellow"
                paddingX={1}
                flexDirection="column"
              >
                {currentAnswer.trim() && (
                  <Text>{renderMarkdown(currentAnswer).trim()}</Text>
                )}
                <Box marginTop={currentAnswer.trim() ? 1 : 0}>
                  <Spinner />
                  <Text color="gray"> generating...</Text>
                </Box>
              </Box>
            )}
          </Box>
        </Box>
      )}

      {/* Source excerpt viewer */}
      {state === "input" && selectedSource >= 0 && lastSources[selectedSource] && (
        <Box
          flexDirection="column"
          marginBottom={1}
          borderStyle="round"
          borderColor="cyan"
          paddingX={1}
        >
          <Text bold color="cyan">
            [{selectedSource + 1}/{lastSources.length}]{" "}
            {lastSources[selectedSource].book}, p.
            {lastSources[selectedSource].page}
            <Text color="gray">
              {" "}
              (score: {lastSources[selectedSource].score.toFixed(3)})
            </Text>
          </Text>
          <Box marginTop={1}>
            <Text>{lastSources[selectedSource].text}</Text>
          </Box>
          <Box marginTop={1}>
            <Text color="gray" dimColor>
              ↑/k: prev • ↓/j: next • 1-5: jump • q: close
            </Text>
          </Box>
        </Box>
      )}

      {/* Error display */}
      {error && (
        <Box marginBottom={1}>
          <Text color="red" bold>
            ⚠ Error:{" "}
          </Text>
          <Text color="red">{error}</Text>
        </Box>
      )}

      {/* Input prompt - hide when viewing sources */}
      {state === "input" && selectedSource === -1 && (
        <Box flexDirection="column">
          {conversation.length > 0 && !error && (
            <Box marginBottom={1}>
              <Text color="gray" dimColor>
                Type /sources or /s to view sources
              </Text>
            </Box>
          )}
          <Box>
            <Text color="green">❯ </Text>
            <TextInput
              value={query}
              onChange={setQuery}
              onSubmit={handleSubmit}
              placeholder={
                conversation.length === 0
                  ? "Ask a question..."
                  : "Ask a follow-up..."
              }
            />
          </Box>
        </Box>
      )}
    </Box>
  );
}

render(<App />);
