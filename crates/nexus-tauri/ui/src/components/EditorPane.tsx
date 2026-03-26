// Editor pane — file viewer with tabs.

import { useState, useCallback, useEffect, useRef } from "react";
import { readFile } from "../tauri";
import { listen } from "@tauri-apps/api/event";

interface OpenFile {
  path: string;
  name: string;
  content: string;
}

interface Props {
  paneId: string;
}

export default function EditorPane({ paneId }: Props) {
  const [openFiles, setOpenFiles] = useState<OpenFile[]>([]);
  const [activePath, setActivePath] = useState<string | null>(null);

  const activeFile = openFiles.find((f) => f.path === activePath);

  const openFile = useCallback(
    async (path: string, name: string) => {
      if (openFiles.find((f) => f.path === path)) {
        setActivePath(path);
        return;
      }
      try {
        const content = await readFile(path);
        setOpenFiles((prev) => [...prev, { path, name, content }]);
        setActivePath(path);
      } catch (e) {
        console.error("Failed to read file:", e);
      }
    },
    [openFiles],
  );

  const closeFile = (path: string) => {
    const next = openFiles.filter((f) => f.path !== path);
    setOpenFiles(next);
    if (activePath === path) {
      setActivePath(next.length > 0 ? next[next.length - 1].path : null);
    }
  };

  // Use a ref to keep openFile current without re-subscribing
  const openFileRef = useRef(openFile);
  openFileRef.current = openFile;

  // Listen for editor.file_opened events from engine
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    listen("editor-file-opened", (event: any) => {
      const { path, name } = event.payload;
      if (path) openFileRef.current(path, name || path.split("/").pop() || path);
    }).then((fn) => { unlisten = fn; });
    return () => { if (unlisten) unlisten(); };
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Tab bar */}
      <div
        style={{
          display: "flex",
          height: 28,
          background: "var(--bg-panel)",
          borderBottom: "1px solid var(--border)",
          overflow: "auto",
        }}
      >
        {openFiles.map((file) => (
          <div
            key={file.path}
            onClick={() => setActivePath(file.path)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "0 10px",
              fontSize: 11,
              cursor: "pointer",
              borderRight: "1px solid var(--border)",
              background:
                activePath === file.path ? "var(--bg)" : "var(--bg-panel)",
              color:
                activePath === file.path
                  ? "var(--text-bright)"
                  : "var(--text-dim)",
              whiteSpace: "nowrap",
            }}
          >
            <span>{file.name}</span>
            <span
              onClick={(e) => {
                e.stopPropagation();
                closeFile(file.path);
              }}
              style={{ cursor: "pointer", opacity: 0.5, fontSize: 14 }}
              onMouseOver={(e) =>
                ((e.target as HTMLElement).style.opacity = "1")
              }
              onMouseOut={(e) =>
                ((e.target as HTMLElement).style.opacity = "0.5")
              }
            >
              x
            </span>
          </div>
        ))}
      </div>

      {/* Content */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          padding: "8px 0",
          fontFamily: "inherit",
          lineHeight: 1.6,
          tabSize: 4,
        }}
      >
        {activeFile ? (
          <pre style={{ margin: 0 }}>
            {activeFile.content.split("\n").map((line, i) => (
              <div key={i} style={{ display: "flex", padding: "0 12px" }}>
                <span
                  style={{
                    color: "var(--text-dim)",
                    width: "3.5em",
                    textAlign: "right",
                    marginRight: "1em",
                    userSelect: "none",
                    flexShrink: 0,
                  }}
                >
                  {i + 1}
                </span>
                <span style={{ color: "var(--text-bright)" }}>{line}</span>
              </div>
            ))}
          </pre>
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "var(--text-dim)",
            }}
          >
            Click a file in the explorer to view it
          </div>
        )}
      </div>
    </div>
  );
}
