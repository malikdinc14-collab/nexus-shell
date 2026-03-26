// ChatTauri — chat surface with streaming responses.
// Session state managed through dispatch("chat.*").
// Streaming uses Tauri IPC (surface-specific — needs real-time byte pipe).

import { useState, useEffect, useRef, useCallback } from "react";
import { agentSend, onAgentOutput, getCwd, dispatchCommand } from "../tauri";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const BACKEND_COLORS = ["#d4a574", "#9ece6a", "#7dcfff", "#bb9af7", "#f7768e", "#e0af68"];

interface Props {
  paneId: string;
  cwd?: string;
  backend?: string;
  isFocused?: boolean;
}

export default function ChatTauri({ paneId, cwd, backend, isFocused }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [backendName, setBackendName] = useState(backend || "echo");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Fetch backend info and restore history from engine
  useEffect(() => {
    dispatchCommand("chat.state").then((state: any) => {
      if (state?.backend?.name) setBackendName(state.backend.name);
    });
    dispatchCommand("chat.history", { pane_id: paneId }).then((conv: any) => {
      if (conv?.messages?.length) {
        setMessages(conv.messages.map((m: any) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
        })));
      }
    });
  }, [paneId]);

  // Focus input when this pane becomes focused
  useEffect(() => {
    if (isFocused && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isFocused]);

  const backendColor = BACKEND_COLORS[0];
  const backendLabel = backendName.charAt(0).toUpperCase() + backendName.slice(1);

  // Listen for agent output events (streaming)
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    onAgentOutput((event) => {
      if (event.paneId !== paneId) return;

      if (event.type === "start") {
        setStreaming(true);
        setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
      } else if (event.type === "text" && event.fullText) {
        setMessages((prev) => {
          const msgs = [...prev];
          if (msgs.length > 0 && msgs[msgs.length - 1].role === "assistant") {
            msgs[msgs.length - 1] = {
              role: "assistant",
              content: event.fullText!,
            };
          }
          return msgs;
        });
      } else if (event.type === "done") {
        setStreaming(false);
      }
    }).then((fn) => {
      unlisten = fn;
    });

    return () => {
      if (unlisten) unlisten();
    };
  }, [paneId]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useCallback(async () => {
    const msg = input.trim();
    if (!msg || streaming) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);

    const dir = cwd || (await getCwd());

    // Register with engine chat state
    dispatchCommand("chat.send", {
      pane_id: paneId,
      message: msg,
      cwd: dir,
    });

    // Also send via Tauri IPC for streaming (if agent adapter available)
    agentSend(paneId, msg, backendName, dir).catch((e) => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${e}` },
      ]);
      setStreaming(false);
    });
  }, [input, streaming, paneId, backendName, cwd]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const handleClear = () => {
    dispatchCommand("chat.clear", { pane_id: paneId });
    setMessages([]);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "var(--bg)",
      }}
    >
      {/* Backend indicator */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "0 10px",
          height: 22,
          background: "var(--bg-panel)",
          borderBottom: "1px solid var(--border)",
          fontSize: 10,
          flexShrink: 0,
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: streaming ? "var(--green)" : backendColor,
          }}
        />
        <span style={{ color: backendColor, fontWeight: 600 }}>{backendLabel}</span>
        {streaming && (
          <span style={{ color: "var(--text-dim)", marginLeft: "auto" }}>
            thinking...
          </span>
        )}
        {!streaming && messages.length > 0 && (
          <span
            onClick={handleClear}
            style={{ color: "var(--text-dim)", marginLeft: "auto", cursor: "pointer" }}
            title="Clear conversation"
          >
            clear
          </span>
        )}
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          padding: "8px 10px",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              color: "var(--text-dim)",
              textAlign: "center",
              marginTop: 40,
              fontSize: 12,
            }}
          >
            Ask {backendLabel} anything
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i}>
            <div
              style={{
                fontSize: 10,
                color: msg.role === "user" ? "var(--accent)" : backendColor,
                marginBottom: 2,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              {msg.role === "user" ? "You" : backendLabel}
            </div>
            <div
              style={{
                fontSize: 12,
                lineHeight: 1.6,
                color: "var(--text-bright)",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                background:
                  msg.role === "assistant"
                    ? "rgba(122, 162, 247, 0.04)"
                    : "transparent",
                padding: msg.role === "assistant" ? "6px 8px" : "0",
                borderRadius: 4,
                borderLeft:
                  msg.role === "assistant"
                    ? `2px solid ${backendColor}`
                    : "none",
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div
        style={{
          padding: "8px 10px",
          borderTop: "1px solid var(--border)",
          background: "var(--bg-panel)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              streaming ? "Waiting for response..." : "Send a message..."
            }
            disabled={streaming}
            rows={1}
            style={{
              flex: 1,
              background: "var(--bg)",
              border: "1px solid var(--border)",
              borderRadius: 4,
              padding: "6px 8px",
              color: "var(--text-bright)",
              fontFamily: "inherit",
              fontSize: 12,
              resize: "none",
              outline: "none",
              lineHeight: 1.5,
            }}
            onInput={(e) => {
              const t = e.target as HTMLTextAreaElement;
              t.style.height = "auto";
              t.style.height = Math.min(t.scrollHeight, 120) + "px";
            }}
          />
          <button
            onClick={send}
            disabled={streaming || !input.trim()}
            style={{
              background: streaming ? "var(--border)" : "var(--accent)",
              color: "#1a1b26",
              border: "none",
              borderRadius: 4,
              padding: "6px 12px",
              fontSize: 11,
              fontWeight: 600,
              cursor: streaming ? "not-allowed" : "pointer",
              flexShrink: 0,
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
