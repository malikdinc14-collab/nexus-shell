// EditorTauri — CodeMirror 6 editor surface with vim keybindings.
// All file state flows through dispatchCommand("editor.*").
// Editing is local (CodeMirror owns the buffer), saves go to the engine.

import { useState, useCallback, useEffect, useRef } from "react";
import { dispatchCommand } from "../tauri";
import { listen } from "@tauri-apps/api/event";

// CodeMirror core
import { EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter, drawSelection, rectangularSelection } from "@codemirror/view";
import { EditorState, Compartment } from "@codemirror/state";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { searchKeymap, highlightSelectionMatches } from "@codemirror/search";
import { bracketMatching, indentOnInput, syntaxHighlighting, defaultHighlightStyle } from "@codemirror/language";

// Vim mode
import { vim, Vim } from "@replit/codemirror-vim";

// Language support
import { javascript } from "@codemirror/lang-javascript";
import { rust } from "@codemirror/lang-rust";
import { python } from "@codemirror/lang-python";
import { json } from "@codemirror/lang-json";
import { html } from "@codemirror/lang-html";
import { css } from "@codemirror/lang-css";
import { markdown } from "@codemirror/lang-markdown";
import { yaml } from "@codemirror/lang-yaml";
import { cpp } from "@codemirror/lang-cpp";
import { java } from "@codemirror/lang-java";
import { go } from "@codemirror/lang-go";

// ── Language registry ────────────────────────────────────────────

const LANG_MAP: Record<string, () => any> = {
  javascript: () => javascript({ jsx: true, typescript: false }),
  typescript: () => javascript({ jsx: true, typescript: true }),
  rust: () => rust(),
  python: () => python(),
  json: () => json(),
  html: () => html(),
  css: () => css(),
  markdown: () => markdown(),
  yaml: () => yaml(),
  c: () => cpp(),
  cpp: () => cpp(),
  java: () => java(),
  go: () => go(),
  shell: () => [], // no CodeMirror shell lang, graceful fallback
  toml: () => [], // no CodeMirror toml lang yet
  ruby: () => [],
  lua: () => [],
};

function getLangExtension(language: string | null) {
  if (!language) return [];
  const factory = LANG_MAP[language];
  if (!factory) return [];
  const ext = factory();
  return ext ? [ext] : [];
}

// ── Tokyo Night theme ────────────────────────────────────────────

const tokyoNightTheme = EditorView.theme({
  "&": {
    backgroundColor: "var(--bg)",
    color: "var(--text-bright)",
    fontSize: "13px",
    height: "100%",
  },
  ".cm-content": {
    caretColor: "var(--accent)",
    fontFamily: "inherit",
    padding: "8px 0",
  },
  ".cm-cursor, .cm-dropCursor": {
    borderLeftColor: "var(--accent)",
    borderLeftWidth: "2px",
  },
  ".cm-activeLine": {
    backgroundColor: "rgba(255,255,255,0.04)",
  },
  ".cm-activeLineGutter": {
    backgroundColor: "rgba(255,255,255,0.04)",
    color: "var(--text-bright)",
  },
  ".cm-gutters": {
    backgroundColor: "var(--bg)",
    color: "var(--text-dim)",
    borderRight: "1px solid var(--border)",
    fontFamily: "inherit",
  },
  ".cm-lineNumbers .cm-gutterElement": {
    minWidth: "3em",
    paddingRight: "8px",
  },
  ".cm-selectionBackground, ::selection": {
    backgroundColor: "rgba(61, 89, 161, 0.4) !important",
  },
  ".cm-matchingBracket": {
    backgroundColor: "rgba(61, 89, 161, 0.3)",
    outline: "1px solid var(--accent)",
  },
  ".cm-searchMatch": {
    backgroundColor: "rgba(224, 175, 104, 0.3)",
  },
  ".cm-vim-panel": {
    backgroundColor: "var(--bg-panel)",
    color: "var(--text-bright)",
    padding: "2px 8px",
    fontSize: "12px",
    fontFamily: "inherit",
  },
  // Fat block cursor for normal mode
  "&.cm-focused .cm-fat-cursor .cm-cursor": {
    background: "var(--accent)",
    border: "none",
    width: "0.6em",
    opacity: "0.7",
  },
}, { dark: true });

// ── Buffer interface ─────────────────────────────────────────────

interface BufferData {
  path: string;
  name: string;
  content: string;
  modified: boolean;
  line_count: number;
  language: string | null;
}

interface Props {
  paneId: string;
  isFocused?: boolean;
}

// ── Component ────────────────────────────────────────────────────

export default function EditorTauri({ paneId, isFocused }: Props) {
  const [openFiles, setOpenFiles] = useState<BufferData[]>([]);
  const [activePath, setActivePath] = useState<string | null>(null);
  const [mode, setMode] = useState("normal");
  const [statusMsg, setStatusMsg] = useState("");
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const langCompartment = useRef(new Compartment());
  const activePathRef = useRef<string | null>(null);
  const openFilesRef = useRef<BufferData[]>([]);
  const paneIdRef = useRef(paneId);

  // Keep refs in sync
  activePathRef.current = activePath;
  openFilesRef.current = openFiles;
  paneIdRef.current = paneId;

  const activeFile = openFiles.find((f) => f.path === activePath);

  // ── Open file via engine ─────────────────────────────────────

  const openFile = useCallback(async (path: string) => {
    // Already open? Switch to it
    const existing = openFilesRef.current.find((f) => f.path === path);
    if (existing) {
      setActivePath(path);
      return;
    }

    try {
      const buffer = await dispatchCommand("editor.open", {
        path,
        pane_id: paneIdRef.current,
      });
      if (buffer && buffer.content !== undefined) {
        const buf = buffer as BufferData;
        setOpenFiles((prev) => [...prev, buf]);
        setActivePath(buf.path);
      }
    } catch (e) {
      console.error("editor.open failed:", e);
      setStatusMsg(`Error: ${e}`);
    }
  }, []);

  // ── Save active file via engine ──────────────────────────────

  const saveFile = useCallback(async () => {
    const path = activePathRef.current;
    if (!path || !viewRef.current) return;

    const content = viewRef.current.state.doc.toString();

    // Update engine buffer content first
    try {
      await dispatchCommand("editor.edit", {
        pane_id: paneIdRef.current,
        content,
      });
      await dispatchCommand("editor.save", {
        pane_id: paneIdRef.current,
      });

      // Update local state
      setOpenFiles((prev) =>
        prev.map((f) =>
          f.path === path ? { ...f, content, modified: false } : f
        )
      );
      setStatusMsg(`"${path}" written`);
      setTimeout(() => setStatusMsg(""), 2000);
    } catch (e) {
      setStatusMsg(`Save failed: ${e}`);
    }
  }, []);

  // ── Close file ───────────────────────────────────────────────

  const closeFile = useCallback((path: string) => {
    dispatchCommand("editor.close", { pane_id: paneIdRef.current });
    setOpenFiles((prev) => {
      const next = prev.filter((f) => f.path !== path);
      if (activePathRef.current === path) {
        setActivePath(next.length > 0 ? next[next.length - 1].path : null);
      }
      return next;
    });
  }, []);

  // ── Keep openFile ref current for event listener ─────────────

  const openFileRef = useRef(openFile);
  openFileRef.current = openFile;
  const saveFileRef = useRef(saveFile);
  saveFileRef.current = saveFile;
  const closeFileRef = useRef(closeFile);
  closeFileRef.current = closeFile;

  // ── Register vim ex commands ─────────────────────────────────

  useEffect(() => {
    // :w — save
    Vim.defineEx("write", "w", () => {
      saveFileRef.current();
    });

    // :q — close buffer
    Vim.defineEx("quit", "q", () => {
      const path = activePathRef.current;
      if (path) closeFileRef.current(path);
    });

    // :wq — save and close
    Vim.defineEx("wq", "wq", () => {
      saveFileRef.current().then(() => {
        const path = activePathRef.current;
        if (path) closeFileRef.current(path);
      });
    });

    // :e <path> — open file
    Vim.defineEx("edit", "e", (_cm: any, params: any) => {
      const path = params?.args?.[0];
      if (path) openFileRef.current(path);
    });

    // :sp — horizontal split
    Vim.defineEx("split", "sp", () => {
      dispatchCommand("pane.split.horizontal");
    });

    // :vsp — vertical split
    Vim.defineEx("vsplit", "vsp", () => {
      dispatchCommand("pane.split.vertical");
    });
  }, []);

  // ── Create/update CodeMirror instance ────────────────────────

  useEffect(() => {
    if (!editorRef.current) return;

    // If view exists, update content
    if (viewRef.current) {
      if (activeFile) {
        const currentContent = viewRef.current.state.doc.toString();
        if (currentContent !== activeFile.content) {
          viewRef.current.dispatch({
            changes: {
              from: 0,
              to: currentContent.length,
              insert: activeFile.content,
            },
          });
        }
        // Update language
        viewRef.current.dispatch({
          effects: langCompartment.current.reconfigure(
            getLangExtension(activeFile.language)
          ),
        });
      }
      return;
    }

    // Create new editor view
    const content = activeFile?.content || "";
    const lang = activeFile?.language || null;

    const state = EditorState.create({
      doc: content,
      extensions: [
        vim(),
        tokyoNightTheme,
        lineNumbers(),
        highlightActiveLine(),
        highlightActiveLineGutter(),
        drawSelection(),
        rectangularSelection(),
        bracketMatching(),
        indentOnInput(),
        history(),
        highlightSelectionMatches(),
        syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
        langCompartment.current.of(getLangExtension(lang)),
        keymap.of([
          ...defaultKeymap,
          ...historyKeymap,
          ...searchKeymap,
          indentWithTab,
        ]),
        // Track modifications
        EditorView.updateListener.of((update) => {
          if (update.docChanged && activePathRef.current) {
            setOpenFiles((prev) =>
              prev.map((f) =>
                f.path === activePathRef.current
                  ? { ...f, modified: true }
                  : f
              )
            );
          }
        }),
        // Track vim mode changes
        EditorView.updateListener.of(() => {
          // Check vim mode from the editor's vim state
          const cm = viewRef.current;
          if (cm) {
            const vimState = (cm as any).cm?.state?.vim;
            if (vimState) {
              const newMode = vimState.insertMode
                ? "insert"
                : vimState.visualMode
                ? "visual"
                : "normal";
              setMode(newMode);
            }
          }
        }),
      ],
    });

    const view = new EditorView({
      state,
      parent: editorRef.current,
    });

    viewRef.current = view;

    // Focus the editor
    view.focus();

    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, [activePath]); // Recreate when switching files

  // ── Focus CodeMirror when this pane becomes focused ──

  useEffect(() => {
    if (isFocused && viewRef.current) {
      viewRef.current.focus();
    }
  }, [isFocused]);

  // ── On mount: fetch current buffer from engine (handles tab-switch race) ──

  useEffect(() => {
    (async () => {
      try {
        const buf = await dispatchCommand("editor.read", {
          pane_id: paneIdRef.current,
        });
        if (buf && buf.path) {
          const buffer = buf as BufferData;
          const existing = openFilesRef.current.find((f) => f.path === buffer.path);
          if (!existing) {
            setOpenFiles((prev) => [...prev, buffer]);
          }
          setActivePath(buffer.path);
        }
      } catch {
        // No buffer yet — that's fine
      }
    })();
  }, []);

  // ── Listen for file open events from engine (scoped to this pane) ──

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    listen("editor-file-opened", (event: any) => {
      const { path, pane_id } = event.payload;
      // Only open if this event is for our pane
      if (path && pane_id === paneIdRef.current) {
        openFileRef.current(path);
      }
    }).then((fn) => {
      unlisten = fn;
    });
    return () => {
      if (unlisten) unlisten();
    };
  }, []);

  // ── Render ───────────────────────────────────────────────────

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Editor area — content tabs handled by ContentTabBar in App.tsx */}
      <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
        {activeFile ? (
          <div ref={editorRef} style={{ height: "100%" }} />
        ) : (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "var(--text-dim)",
              gap: 8,
            }}
          >
            <div>No file open</div>
            <div style={{ fontSize: 11 }}>
              Use <code>:e /path/to/file</code> or click from Explorer
            </div>
          </div>
        )}
      </div>

      {/* Status bar */}
      <div
        style={{
          height: 22,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 8px",
          background: "var(--bg-panel)",
          borderTop: "1px solid var(--border)",
          fontSize: 11,
          flexShrink: 0,
        }}
      >
        <span style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span
            style={{
              color:
                mode === "insert"
                  ? "var(--green)"
                  : mode === "visual"
                  ? "var(--magenta)"
                  : "var(--accent)",
              fontWeight: "bold",
              textTransform: "uppercase",
            }}
          >
            {mode}
          </span>
          {statusMsg && (
            <span style={{ color: "var(--text-dim)" }}>{statusMsg}</span>
          )}
        </span>
        <span style={{ color: "var(--text-dim)" }}>
          {activeFile
            ? `${activeFile.language || "plain"} | ${activeFile.line_count} lines`
            : ""}
        </span>
      </div>
    </div>
  );
}
