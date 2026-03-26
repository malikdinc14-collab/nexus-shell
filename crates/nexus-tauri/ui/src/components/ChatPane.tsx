// Chat pane — headless agent chat with streaming responses.
// NOT a terminal. Spawns agent CLI in headless mode, parses output.

import { useState, useEffect, useRef, useCallback } from "react";
import { agentSend, onAgentOutput, getCwd, getCapabilities, CapabilityInfo } from "../tauri";

interface Message {
  role: "user" | "assistant";
  content: string;
}

// Default colors assigned to backends by index
const BACKEND_COLORS = ["#d4a574", "#9ece6a", "#7dcfff", "#bb9af7", "#f7768e", "#e0af68"];

interface Props {
  paneId: string;
  cwd?: string;
  backend?: string;
}

export default function ChatPane({ paneId, cwd, backend }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [backends, setBackends] = useState<Array<{ name: string; label: string; color: string }>>([]);
  const [activeBackend, setActiveBackend] = useState(backend || "");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Fetch available chat backends from engine
  useEffect(() => {
    getCapabilities("chat").then((caps) => {
      const list = caps.map((c, i) => ({
        name: c.name,
        label: c.name.charAt(0).toUpperCase() + c.name.slice(1),
        color: BACKEND_COLORS[i % BACKEND_COLORS.length],
      }));
      setBackends(list);
      if (!activeBackend && list.length > 0) {
        setActiveBackend(list[0].name);
      }
    }).catch(() => {
      // Fallback if engine unavailable
      setBackends([{ name: "claude", label: "Claude", color: BACKEND_COLORS[0] }]);
      if (!activeBackend) setActiveBackend("claude");
    });
  }, []);

  const info = backends.find((b) => b.name === activeBackend) || { name: activeBackend, label: activeBackend, color: BACKEND_COLORS[0] };

  // Listen for agent output events
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
    agentSend(paneId, msg, activeBackend, dir).catch((e) => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${e}` },
      ]);
      setStreaming(false);
    });
  }, [input, streaming, paneId, activeBackend, cwd]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
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
            background: streaming ? "var(--green)" : info.color,
          }}
        />
        <span style={{ color: info.color, fontWeight: 600 }}>{info.label}</span>
        {streaming && (
          <span style={{ color: "var(--text-dim)", marginLeft: "auto" }}>
            thinking...
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
            Ask {info.label} anything
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i}>
            <div
              style={{
                fontSize: 10,
                color:
                  msg.role === "user" ? "var(--accent)" : info.color,
                marginBottom: 2,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              {msg.role === "user" ? "You" : info.label}
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
                    ? `2px solid ${info.color}`
                    : "none",
              }}
            >
              {msg.content || (streaming && i === messages.length - 1 ? "" : "")}
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
        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "flex-end",
          }}
        >
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
