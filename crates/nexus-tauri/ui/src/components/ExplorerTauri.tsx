// ExplorerTauri — file tree surface, renders engine state.
// All data flows through dispatchCommand("explorer.*").

import { useState, useEffect, useCallback, useRef } from "react";
import { dispatchCommand } from "../tauri";

interface ExplorerEntry {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  depth: number;
  expanded: boolean;
}

interface ExplorerState {
  root: string;
  backend: string;
  show_hidden: boolean;
  entries: ExplorerEntry[];
  cursor: number;
}

interface Props {
  paneId: string;
  rootPath: string;
  isFocused?: boolean;
}

export default function ExplorerTauri({ paneId, rootPath, isFocused }: Props) {
  const [state, setState] = useState<ExplorerState | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchTree = useCallback(async () => {
    try {
      const result = await dispatchCommand("explorer.tree");
      if (result && result.entries) {
        setState(result as ExplorerState);
      }
    } catch (e) {
      console.error("explorer.tree failed:", e);
    }
  }, []);

  useEffect(() => {
    // Navigate explorer to rootPath on mount
    if (rootPath) {
      dispatchCommand("explorer.navigate", { path: rootPath }).then((result) => {
        if (result && result.entries) setState(result as ExplorerState);
      });
    } else {
      fetchTree();
    }
  }, [rootPath, fetchTree]);

  const handleToggle = async (entry: ExplorerEntry) => {
    if (!entry.is_dir) {
      // Route through FileRouter — auto-selects Editor, RichText, etc.
      dispatchCommand("file.open", { path: entry.path });
      return;
    }
    const result = await dispatchCommand("explorer.toggle", { path: entry.path });
    if (result && result.entries) setState(result as ExplorerState);
  };

  const handleUp = async () => {
    const result = await dispatchCommand("explorer.up");
    if (result && result.entries) setState(result as ExplorerState);
  };

  // Focus container when this pane becomes focused
  useEffect(() => {
    if (isFocused && containerRef.current) {
      containerRef.current.focus();
    }
  }, [isFocused]);

  const handleToggleHidden = async () => {
    const result = await dispatchCommand("explorer.hidden");
    if (result && result.entries) setState(result as ExplorerState);
  };

  // Keyboard navigation (pane-scoped — only fires when explorer has DOM focus)
  const handleKeyDown = useCallback(async (e: React.KeyboardEvent) => {
    let result: any = null;
    switch (e.key) {
      case "j":
      case "ArrowDown":
        e.preventDefault();
        result = await dispatchCommand("explorer.cursor_down");
        break;
      case "k":
      case "ArrowUp":
        e.preventDefault();
        result = await dispatchCommand("explorer.cursor_up");
        break;
      case "l":
      case "ArrowRight":
      case "Enter":
        e.preventDefault();
        result = await dispatchCommand("explorer.cursor_toggle");
        break;
      case "h":
      case "ArrowLeft":
        e.preventDefault();
        result = await dispatchCommand("explorer.cursor_collapse");
        break;
      default:
        return;
    }
    if (result && result.entries) setState(result as ExplorerState);
  }, []);

  // Scroll cursor into view
  const cursorRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    cursorRef.current?.scrollIntoView({ block: "nearest" });
  }, [state?.cursor]);

  if (!state) {
    return (
      <div style={{ padding: 16, color: "var(--text-dim)", fontSize: 12 }}>
        Loading...
      </div>
    );
  }

  const rootName = state.root.split("/").pop() || state.root;

  return (
    <div ref={containerRef} tabIndex={0} onKeyDown={handleKeyDown} style={{ height: "100%", display: "flex", flexDirection: "column", outline: "none" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "6px 10px",
          borderBottom: "1px solid var(--border)",
          fontSize: 11,
          color: "var(--text-dim)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            onClick={handleUp}
            style={{ cursor: "pointer", color: "var(--accent)" }}
            title="Go up"
          >
            ..
          </span>
          <span title={state.root}>{rootName}/</span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <span
            onClick={handleToggleHidden}
            style={{
              cursor: "pointer",
              color: state.show_hidden ? "var(--accent)" : "var(--text-dim)",
            }}
            title="Toggle hidden files"
          >
            .*
          </span>
          <span style={{ color: "var(--text-dim)" }}>{state.backend}</span>
        </div>
      </div>

      {/* Tree */}
      <div style={{ flex: 1, overflow: "auto", padding: "4px 0" }}>
        {state.entries.map((entry, i) => {
          const isCursor = i === state.cursor;
          return (
          <div
            key={entry.path}
            ref={isCursor ? cursorRef : undefined}
            onClick={() => handleToggle(entry)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              padding: "3px 8px",
              paddingLeft: 8 + entry.depth * 16,
              cursor: "pointer",
              fontSize: 12,
              color: isCursor
                ? "var(--text-bright)"
                : entry.is_dir ? "var(--accent)" : "var(--text)",
              background: isCursor ? "rgba(122, 162, 247, 0.15)" : undefined,
              whiteSpace: "nowrap",
            }}
            onMouseOver={(e) => {
              if (!isCursor) {
                (e.currentTarget as HTMLElement).style.background = "var(--hover)";
                (e.currentTarget as HTMLElement).style.color = "var(--text-bright)";
              }
            }}
            onMouseOut={(e) => {
              if (!isCursor) {
                (e.currentTarget as HTMLElement).style.background = "";
                (e.currentTarget as HTMLElement).style.color = entry.is_dir
                  ? "var(--accent)"
                  : "var(--text)";
              }
            }}
          >
            <span style={{ width: 16, textAlign: "center", fontSize: 11 }}>
              {entry.is_dir ? (entry.expanded ? "\u25BE" : "\u25B8") : "\u00B7"}
            </span>
            <span>{entry.name}</span>
          </div>
          );
        })}
        {state.entries.length === 0 && (
          <div style={{ padding: 16, color: "var(--text-dim)", fontSize: 12, textAlign: "center" }}>
            Empty directory
          </div>
        )}
      </div>
    </div>
  );
}
