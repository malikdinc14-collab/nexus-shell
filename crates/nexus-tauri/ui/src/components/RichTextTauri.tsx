// RichTextTauri — Obsidian-like markdown surface for Nexus Shell.
// Currently a high-fidelity markdown renderer/editor stub with Mermaid support.

import { useState, useEffect, useCallback, useRef } from "react";
import { dispatchCommand } from "../tauri";
import { listen } from "@tauri-apps/api/event";
import mermaid from "mermaid";

// Initialize mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  securityLevel: "loose",
  fontFamily: "'Inter', sans-serif"
});

interface NoteNode {
  id: string;
  path: string;
  title: string;
  content: string;
  tags: string[];
  backlinks: string[];
}

interface Props {
  paneId: string;
  isFocused?: boolean;
}

export default function RichTextTauri({ paneId, isFocused }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [node, setNode] = useState<NoteNode | null>(null);
  const [editing, setEditing] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isFocused && containerRef.current) {
      containerRef.current.focus();
    }
  }, [isFocused]);

  const refreshNode = useCallback(async () => {
    try {
        const result = await dispatchCommand("markdown.state", { pane_id: paneId });
        if (result && (result as any).id) {
          setNode(result as NoteNode);
        }
    } catch (e) {
      console.warn("markdown.state failed:", e);
    }
  }, [paneId]);

  useEffect(() => {
    refreshNode();
  }, [refreshNode]);

  // Mermaid rendering effect
  useEffect(() => {
    if (!editing && contentRef.current && node?.content.includes("```mermaid")) {
        mermaid.run({
            nodes: contentRef.current.querySelectorAll(".mermaid")
        }).catch(err => console.warn("Mermaid run failed:", err));
    }
  }, [node, editing]);

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    listen("layout-changed", () => {
        refreshNode();
    }).then((fn) => { unlisten = fn; });
    return () => { if (unlisten) unlisten(); };
  }, [refreshNode]);

  const renderContent = (content: string) => {
    const parts = content.split(/(```mermaid[\s\S]*?```)/g);
    return parts.map((part, i) => {
        if (part.startsWith("```mermaid")) {
            const chart = part.replace(/^```mermaid\n?/, "").replace(/\n?```$/, "");
            return <pre key={i} className="mermaid" style={{ background: "transparent" }}>{chart}</pre>;
        }
        return <span key={i} style={{ whiteSpace: "pre-wrap" }}>{part}</span>;
    });
  };

  if (!node) {
    return (
      <div style={{
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          height: "100%", color: "var(--text-dim)", gap: 12, background: "var(--bg)", fontFamily: "'Inter', sans-serif",
      }}>
        <div style={{ fontSize: 24, opacity: 0.5 }}>📝</div>
        <div>No document open</div>
        <div style={{ fontSize: 11, opacity: 0.7 }}>Use <code>markdown.open [path]</code></div>
      </div>
    );
  }

  return (
    <div ref={containerRef} tabIndex={0} style={{
        display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)",
        color: "var(--text)", fontFamily: "'Inter', sans-serif", overflow: "hidden",
        outline: "none"
    }}>
      {/* Header */}
      <div style={{ 
          padding: "12px 20px", borderBottom: "1px solid var(--border)", display: "flex",
          alignItems: "center", gap: 12, background: "rgba(255,255,255,0.02)"
      }}>
        <span style={{ color: "var(--accent)", fontSize: 14 }}>◈</span>
        <span style={{ fontWeight: 600, fontSize: 13, letterSpacing: "-0.01em" }}>{node.title}</span>
        <div style={{ flex: 1 }} />
        <div style={{ display: "flex", gap: 8 }}>
            {node.tags.map(tag => (
                <span key={tag} style={{ 
                    fontSize: 10, padding: "2px 6px", borderRadius: 4, 
                    background: "var(--hover)", color: "var(--text-dim)"
                }}>#{tag}</span>
            ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: "auto", padding: "32px 40px" }} ref={contentRef}>
        <div style={{ maxWidth: 700, margin: "0 auto" }}>
            {editing ? (
                <textarea 
                    value={node.content}
                    onChange={(e) => setNode({ ...node, content: e.target.value })}
                    onBlur={() => setEditing(false)}
                    autoFocus
                    style={{
                        width: "100%", height: "80vh", background: "transparent", border: "none",
                        color: "inherit", fontFamily: "inherit", fontSize: 15, lineHeight: 1.6,
                        outline: "none", resize: "none"
                    }}
                />
            ) : (
                <div onClick={() => setEditing(true)} style={{ fontSize: 15, lineHeight: 1.7, cursor: "text" }}>
                    {renderContent(node.content)}
                </div>
            )}
        </div>
      </div>

      {/* Footer */}
      <div style={{ 
          padding: "8px 20px", borderTop: "1px solid var(--border)", fontSize: 10,
          color: "var(--text-dim)", display: "flex", justifyContent: "space-between"
      }}>
        <span>{node.backlinks.length} backlinks</span>
        <span>{node.path}</span>
      </div>
    </div>
  );
}
