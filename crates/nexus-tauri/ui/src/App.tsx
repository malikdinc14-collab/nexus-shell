// Nexus Shell — main app.
// Renders layout tree from Rust engine, routes keyboard commands.

import { useState, useEffect, useCallback, useRef } from "react";
import {
  getLayout,
  getSession,
  getCwd,
  focusPane,
  resizePane,
  onLayoutChanged,
  getKeymap,
  getCommands,
  dispatchCommand,
  KeyBinding,
  CommandEntry,
  LayoutData,
  LayoutNode,
} from "./tauri";
import TerminalPane from "./components/TerminalPane";
import EditorPane from "./components/EditorPane";
import ExplorerPane from "./components/ExplorerPane";
import InfoPane from "./components/InfoPane";
import ChatPane from "./components/ChatPane";
import CommandPalette from "./components/CommandPalette";
import TabBar from "./components/TabBar";
import useTabStack from "./hooks/useTabStack";

export default function App() {
  const [layout, setLayout] = useState<LayoutData | null>(null);
  const [session, setSession] = useState<string | null>(null);
  const [cwd, setCwd] = useState("");
  const [cmdOpen, setCmdOpen] = useState(false);
  const [keymap, setKeymap] = useState<KeyBinding[]>([]);
  const [commands, setCommands] = useState<CommandEntry[]>([]);

  // Init
  useEffect(() => {
    Promise.all([getLayout(), getSession(), getCwd(), getKeymap(), getCommands()]).then(
      ([layoutData, sess, dir, km, cmds]) => {
        setLayout(layoutData);
        setSession(sess);
        setCwd(dir);
        setKeymap(km);
        setCommands(cmds);
      },
    );
  }, []);

  // Event-driven layout updates (from daemon or other clients)
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    onLayoutChanged((newLayout) => setLayout(newLayout)).then((fn) => {
      unlisten = fn;
    });
    return () => { if (unlisten) unlisten(); };
  }, []);

  // Dynamic keyboard shortcuts from engine keymap
  useEffect(() => {
    const handler = async (e: KeyboardEvent) => {
      if (cmdOpen) return;

      const binding = matchBinding(e, keymap);
      if (!binding) return;

      e.preventDefault();
      try {
        const result = await dispatchCommand(binding.action);
        // If the result looks like layout data, update it
        if (result && typeof result === "object" && "root" in result && "focused" in result) {
          setLayout(result as LayoutData);
        }
      } catch (err) {
        console.warn("Dispatch failed:", binding.action, err);
      }
    };

    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [keymap, cmdOpen]);

  // Command palette handler — dispatches through engine
  const handleCommand = useCallback(
    async (cmd: string) => {
      try {
        const result = await dispatchCommand(cmd);
        if (result && typeof result === "object" && "root" in result && "focused" in result) {
          setLayout(result as LayoutData);
        }
      } catch (err) {
        console.warn("Command dispatch failed:", cmd, err);
      }
    },
    [],
  );

  const handleFocus = useCallback(
    async (paneId: string) => {
      const result = await focusPane(paneId);
      setLayout(result);
    },
    [],
  );

  const handleResize = useCallback(
    async (paneId: string, ratio: number) => {
      const result = await resizePane(paneId, ratio);
      setLayout(result);
    },
    [],
  );

  if (!layout) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          color: "var(--text-dim)",
        }}
      >
        Loading...
      </div>
    );
  }

  return (
    <>
      {/* Top bar */}
      <div
        style={{
          height: 28,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 12px",
          background: "var(--bg-panel)",
          borderBottom: "1px solid var(--border)",
          fontSize: 11,
          WebkitAppRegion: "drag" as any,
          flexShrink: 0,
        }}
      >
        <span style={{ color: "var(--accent)" }}>Nexus Shell</span>
        <span style={{ color: "var(--text-dim)" }}>
          Alt+P palette · Ctrl+\ command line
        </span>
      </div>

      {/* Layout */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {layout.zoomed ? (
          <PaneComponent
            node={findLeaf(layout.root, layout.zoomed)!}
            focused={true}
            onFocus={handleFocus}
            cwd={cwd}
            session={session}
          />
        ) : (
          <NodeRenderer
            node={layout.root}
            focused={layout.focused}
            onFocus={handleFocus}
            onResize={handleResize}
            cwd={cwd}
            session={session}
          />
        )}
      </div>

      {/* Status bar */}
      <div
        style={{
          height: 24,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 10px",
          background: "#3d59a1",
          color: "var(--text-bright)",
          fontSize: 11,
          flexShrink: 0,
        }}
      >
        <span>
          {layout.zoomed && (
            <span
              style={{
                background: "var(--green)",
                color: "#1a1b26",
                padding: "1px 6px",
                borderRadius: 3,
                fontWeight: "bold",
                marginRight: 8,
                fontSize: 10,
              }}
            >
              ZOOM
            </span>
          )}
          {layout.focused}
        </span>
        <span>{session ? `Session: ${session}` : "Engine ready"}</span>
      </div>

      <CommandPalette
        isOpen={cmdOpen}
        setIsOpen={setCmdOpen}
        onCommand={handleCommand}
        commands={commands}
      />
    </>
  );
}

// ── Recursive layout renderer ────────────────────────────────────

function NodeRenderer({
  node,
  focused,
  onFocus,
  onResize,
  cwd,
  session,
}: {
  node: LayoutNode;
  focused: string;
  onFocus: (id: string) => void;
  onResize: (paneId: string, ratio: number) => Promise<void>;
  cwd: string;
  session: string | null;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  if (node.type === "Leaf") {
    return (
      <PaneComponent
        node={node}
        focused={node.id === focused}
        onFocus={onFocus}
        cwd={cwd}
        session={session}
      />
    );
  }

  const isH = node.direction === "Horizontal";
  const pct = ((node.ratio || 0.5) * 100).toFixed(2) + "%";

  const handleResizeMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    const container = containerRef.current;
    if (!container) return;

    const paneId = firstLeafId(node.left!);
    if (!paneId) return;

    const onMouseMove = (mv: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const ratio = isH
        ? (mv.clientX - rect.left) / rect.width
        : (mv.clientY - rect.top) / rect.height;
      const clamped = Math.max(0.05, Math.min(0.95, ratio));
      // Live visual feedback via CSS variable on the container element
      if (isH) {
        (container.firstElementChild as HTMLElement | null)?.style.setProperty(
          "width",
          `${clamped * 100}%`,
        );
      } else {
        (container.firstElementChild as HTMLElement | null)?.style.setProperty(
          "height",
          `${clamped * 100}%`,
        );
      }
    };

    const onMouseUp = (mu: MouseEvent) => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);

      const rect = container.getBoundingClientRect();
      const ratio = isH
        ? (mu.clientX - rect.left) / rect.width
        : (mu.clientY - rect.top) / rect.height;
      const clamped = Math.max(0.05, Math.min(0.95, ratio));
      onResize(paneId, clamped);
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  return (
    <div
      ref={containerRef}
      style={{
        display: "flex",
        flexDirection: isH ? "row" : "column",
        flex: 1,
        overflow: "hidden",
      }}
    >
      <div
        style={
          isH
            ? { width: pct, flexShrink: 0, display: "flex", overflow: "hidden" }
            : { height: pct, flexShrink: 0, display: "flex", overflow: "hidden" }
        }
      >
        <NodeRenderer
          node={node.left!}
          focused={focused}
          onFocus={onFocus}
          onResize={onResize}
          cwd={cwd}
          session={session}
        />
      </div>

      {/* Resize handle */}
      <div
        style={{
          [isH ? "width" : "height"]: 4,
          cursor: isH ? "col-resize" : "row-resize",
          flexShrink: 0,
          background: "transparent",
        }}
        onMouseDown={handleResizeMouseDown}
        onMouseOver={(e) =>
          ((e.target as HTMLElement).style.background = "var(--accent)")
        }
        onMouseOut={(e) =>
          ((e.target as HTMLElement).style.background = "transparent")
        }
      />

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <NodeRenderer
          node={node.right!}
          focused={focused}
          onFocus={onFocus}
          onResize={onResize}
          cwd={cwd}
          session={session}
        />
      </div>
    </div>
  );
}

// ── Pane type registry ───────────────────────────────────────────
// New surfaces define their own registry mapping pane types to platform components.

interface PaneProps {
  paneId: string;
  cwd?: string;
  session?: string | null;
  rootPath?: string;
}

const PANE_REGISTRY: Record<string, React.ComponentType<PaneProps>> = {
  Terminal: TerminalPane,
  Editor: EditorPane,
  Explorer: ({ paneId, cwd }) => <ExplorerPane paneId={paneId} rootPath={cwd || ""} />,
  Chat: ChatPane,
  Info: ({ paneId, session, cwd }) => <InfoPane paneId={paneId} session={session ?? null} cwd={cwd || ""} />,
};

// ── Pane component (dispatches via registry) ─────────────────────

function PaneComponent({
  node,
  focused,
  onFocus,
  cwd,
  session,
}: {
  node: LayoutNode;
  focused: boolean;
  onFocus: (id: string) => void;
  cwd: string;
  session: string | null;
}) {
  const paneId = node.id!;
  const stack = useTabStack(paneId);

  // Render type comes from the active tab name, not from the pane itself
  const activeTabName = stack.tabs[stack.activeIndex]?.name || "Info";
  const PaneImpl = PANE_REGISTRY[activeTabName] || PANE_REGISTRY.Info;

  // Map engine tabs to TabBar items
  const tabItems = stack.tabs.length > 0
    ? stack.tabs.map((t) => ({ name: t.name, isActive: t.is_active }))
    : [];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        overflow: "hidden",
        border: focused
          ? "2px solid var(--accent)"
          : "2px solid transparent",
        transition: "border-color 0.15s",
      }}
      onMouseDown={() => onFocus(paneId)}
    >
      {/* Tab bar (shows tabs when stack has 2+, otherwise shows pane label) */}
      <TabBar
        tabs={tabItems}
        onSelect={stack.switchTab}
        onClose={() => stack.closeTab()}
        paneLabel={`${activeTabName} · ${paneId}`}
      />

      {/* Body */}
      <div
        style={{
          flex: 1,
          overflow: "hidden",
          background: "var(--bg)",
        }}
      >
        <PaneImpl paneId={paneId} cwd={cwd} session={session} />
      </div>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────

function findLeaf(
  node: LayoutNode,
  id: string,
): LayoutNode | null {
  if (node.type === "Leaf") return node.id === id ? node : null;
  return findLeaf(node.left!, id) || findLeaf(node.right!, id);
}

function firstLeafId(node: LayoutNode): string | null {
  if (node.type === "Leaf") return node.id ?? null;
  return firstLeafId(node.left!) || firstLeafId(node.right!);
}

// ── Keybinding matcher ──────────────────────────────────────────

function matchBinding(e: KeyboardEvent, keymap: KeyBinding[]): KeyBinding | null {
  for (const binding of keymap) {
    const parts = binding.key.split("+");
    const key = parts[parts.length - 1].toLowerCase();
    const needAlt = parts.some((p) => p === "Alt");
    const needCtrl = parts.some((p) => p === "Ctrl");
    const needMeta = parts.some((p) => p === "Meta" || p === "Cmd");
    const needShift = parts.some((p) => p === "Shift");

    if (
      e.key.toLowerCase() === key &&
      e.altKey === needAlt &&
      e.ctrlKey === needCtrl &&
      e.metaKey === needMeta &&
      e.shiftKey === needShift
    ) {
      return binding;
    }
  }
  return null;
}
