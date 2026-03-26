// Explorer pane — file tree with lazy directory loading.

import { useState, useEffect } from "react";
import { readDir, DirEntry, dispatchCommand } from "../tauri";

interface Props {
  paneId: string;
  rootPath: string;
}

function FileItem({
  entry,
  depth,
  rootPath,
}: {
  entry: DirEntry;
  depth: number;
  rootPath: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [children, setChildren] = useState<DirEntry[] | null>(null);

  const toggle = async () => {
    if (!entry.is_dir) {
      // Open file in editor via engine dispatch
      dispatchCommand("editor.open", { path: entry.path, name: entry.name });
      return;
    }

    if (!expanded && children === null) {
      try {
        const entries = await readDir(entry.path);
        setChildren(entries);
      } catch {
        setChildren([]);
      }
    }
    setExpanded(!expanded);
  };

  return (
    <>
      <div
        onClick={toggle}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          padding: "3px 8px",
          paddingLeft: 8 + depth * 16,
          cursor: "pointer",
          fontSize: 12,
          color: entry.is_dir ? "var(--accent)" : "var(--text)",
          whiteSpace: "nowrap",
        }}
        onMouseOver={(e) => {
          (e.currentTarget as HTMLElement).style.background = "var(--hover)";
          (e.currentTarget as HTMLElement).style.color = "var(--text-bright)";
        }}
        onMouseOut={(e) => {
          (e.currentTarget as HTMLElement).style.background = "";
          (e.currentTarget as HTMLElement).style.color = entry.is_dir
            ? "var(--accent)"
            : "var(--text)";
        }}
      >
        <span style={{ width: 16, textAlign: "center", fontSize: 11 }}>
          {entry.is_dir ? (expanded ? "▾" : "▸") : "·"}
        </span>
        <span>{entry.name}</span>
      </div>
      {expanded &&
        children?.map((child) => (
          <FileItem
            key={child.path}
            entry={child}
            depth={depth + 1}
            rootPath={rootPath}
          />
        ))}
    </>
  );
}

export default function ExplorerPane({ paneId, rootPath }: Props) {
  const [entries, setEntries] = useState<DirEntry[]>([]);

  useEffect(() => {
    if (rootPath) {
      readDir(rootPath).then(setEntries).catch(console.error);
    }
  }, [rootPath]);

  return (
    <div style={{ padding: "4px 0", overflow: "auto", height: "100%" }}>
      {entries.map((entry) => (
        <FileItem
          key={entry.path}
          entry={entry}
          depth={0}
          rootPath={rootPath}
        />
      ))}
    </div>
  );
}
