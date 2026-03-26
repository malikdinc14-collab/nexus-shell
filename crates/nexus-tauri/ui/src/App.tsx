// Nexus Shell — main app.
// Renders layout tree from Rust engine, routes keyboard commands.
// The UI is a dumb renderer. All state and logic lives in the engine.

import { useState, useEffect, useCallback, useRef } from "react";
import {
  getLayout,
  getSession,
  getCwd,
  focusPane,
  resizePane,
  onLayoutChanged,
  onDisplayChanged,
  getKeymap,
  getCommands,
  dispatchCommand,
  KeyBinding,
  CommandEntry,
  DisplaySettings,
  LayoutData,
  LayoutNode,
} from "./tauri";
import TerminalTauri from "./components/TerminalTauri";
import EditorTauri from "./components/EditorTauri";
import ExplorerTauri from "./components/ExplorerTauri";
import InfoTauri from "./components/InfoTauri";
import ChatTauri from "./components/ChatTauri";
import BrowserTauri from "./components/BrowserTauri";
import RichTextTauri from "./components/RichTextTauri";
import HUDTauri from "./components/HUDTauri";
import ChooserPane from "./components/ChooserPane";
import MenuTauri from "./components/MenuTauri";
import CommandPalette from "./components/CommandPalette";
import CommandLine from "./components/CommandLine";
import TabListOverlay from "./components/TabListOverlay";
import TabBar, { ContentTabItem } from "./components/TabBar";
import useTabStack from "./hooks/useTabStack";
import { listen } from "@tauri-apps/api/event";

export default function App() {
  const [layout, setLayout] = useState<LayoutData | null>(null);
  const [session, setSession] = useState<string | null>(null);
  const [cwd, setCwd] = useState("");
  const [cmdOpen, setCmdOpen] = useState(false);
  const [cmdLineOpen, setCmdLineOpen] = useState(false);
  const [tabListOpen, setTabListOpen] = useState(false);
  const [keymap, setKeymap] = useState<KeyBinding[]>([]);
  const [commands, setCommands] = useState<CommandEntry[]>([]);
  const [display, setDisplay] = useState<DisplaySettings>({
    gap: 0,
    background: "var(--bg)",
    border_radius: 0,
    pane_opacity: 1,
  });

  // Init — fetch all state from engine
  useEffect(() => {
    Promise.all([
      getLayout(),
      getSession(),
      getCwd(),
      getKeymap(),
      getCommands(),
    ]).then(([layoutData, sess, dir, km, cmds]) => {
      setLayout(layoutData);
      setSession(sess);
      setCwd(dir);
      setKeymap(km);
      setCommands(cmds);
    });
    // Display settings fetched separately — non-blocking
    dispatchCommand("display.get")
      .then((disp) => { if (disp) setDisplay(disp as DisplaySettings); })
      .catch(() => {});
  }, []);

  // Sync body transparency attribute (surface-specific DOM concern)
  useEffect(() => {
    document.body.dataset.transparent =
      display.background === "transparent" ? "true" : "false";
  }, [display.background]);

  // Event-driven layout updates (from daemon or other clients)
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    onLayoutChanged((newLayout) => setLayout(newLayout)).then((fn) => {
      unlisten = fn;
    });
    return () => { if (unlisten) unlisten(); };
  }, []);

  // Event-driven display updates (from engine)
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    onDisplayChanged((settings) => setDisplay(settings)).then((fn) => {
      unlisten = fn;
    });
    return () => { if (unlisten) unlisten(); };
  }, []);

  // Frontend-local commands — ONLY pure view toggles
  const FRONTEND_COMMANDS = new Set([
    "command_palette.toggle",
    "command_line.toggle",
    "stack.list",
  ]);

  // Dynamic keyboard shortcuts from engine keymap
  useEffect(() => {
    const handler = async (e: KeyboardEvent) => {
      const binding = matchBinding(e, keymap);
      if (!binding) return;

      // Allow toggles even when overlays are open
      if (cmdOpen && !FRONTEND_COMMANDS.has(binding.action)) return;

      e.preventDefault();
      e.stopPropagation();

      // Handle view toggles
      if (binding.action === "command_palette.toggle") {
        setCmdOpen((prev) => !prev);
        return;
      }
      if (binding.action === "command_line.toggle") {
        setCmdLineOpen((prev) => !prev);
        return;
      }
      if (binding.action === "stack.list") {
        setTabListOpen((prev) => !prev);
        return;
      }

      // Everything else goes through the engine
      try {
        const result = await dispatchCommand(binding.action);
        if (result && typeof result === "object" && "root" in result && "focused" in result) {
          setLayout(result as LayoutData);
        }
      } catch (err) {
        console.warn("Dispatch failed:", binding.action, err);
      }
    };

    document.addEventListener("keydown", handler, { capture: true });
    return () => document.removeEventListener("keydown", handler, { capture: true });
  }, [keymap, cmdOpen]);

  // Command palette handler — dispatches through engine
  const handleCommand = useCallback(
    async (cmd: string) => {
      if (cmd === "command_palette.toggle") {
        setCmdOpen((prev) => !prev);
        return;
      }
      if (cmd === "command_line.toggle") {
        setCmdLineOpen((prev) => !prev);
        return;
      }
      if (cmd === "stack.list") {
        setTabListOpen(true);
        return;
      }

      // Everything else goes through the engine
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

  // Vim command line — just forwards to engine
  const handleCmdLine = useCallback(
    async (raw: string) => {
      try {
        const result = await dispatchCommand("command_line.execute", { raw });
        if (result && typeof result === "object" && "root" in result && "focused" in result) {
          setLayout(result as LayoutData);
        }
      } catch (err) {
        console.warn("Command line dispatch failed:", raw, err);
      }
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
      <div
        style={{
          flex: 1,
          display: "flex",
          overflow: "hidden",
          padding: display.gap,
          background: display.background,
          transition: "padding 0.2s, background 0.3s",
        }}
      >
        {layout.zoomed ? (
          <PaneComponent
            node={findLeaf(layout.root, layout.zoomed)!}
            focused={true}
            onFocus={handleFocus}
            cwd={cwd}
            session={session}
            display={display}
          />
        ) : (
          <NodeRenderer
            node={layout.root}
            focused={layout.focused}
            onFocus={handleFocus}
            onResize={handleResize}
            cwd={cwd}
            session={session}
            display={display}
          />
        )}
      </div>

      {/* Vim command line */}
      <CommandLine
        isOpen={cmdLineOpen}
        setIsOpen={setCmdLineOpen}
        onExecute={handleCmdLine}
      />

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

      <TabListOverlay
        isOpen={tabListOpen}
        setIsOpen={setTabListOpen}
        focusedPaneId={layout.focused}
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
  display,
}: {
  node: LayoutNode;
  focused: string;
  onFocus: (id: string) => void;
  onResize: (paneId: string, ratio: number) => Promise<void>;
  cwd: string;
  session: string | null;
  display: DisplaySettings;
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
        display={display}
      />
    );
  }

  const isH = node.direction === "Horizontal";
  const pct = ((node.ratio || 0.5) * 100).toFixed(2) + "%";

  const handleResizeMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const container = containerRef.current;
    if (!container) return;

    const paneId = firstLeafId(node.left!);
    if (!paneId) return;

    let didMove = false;
    let lastClamped = node.ratio || 0.5;

    const onMouseMove = (mv: MouseEvent) => {
      didMove = true;
      const rect = container.getBoundingClientRect();
      const ratio = isH
        ? (mv.clientX - rect.left) / rect.width
        : (mv.clientY - rect.top) / rect.height;
      lastClamped = Math.max(0.05, Math.min(0.95, ratio));
      if (isH) {
        (container.firstElementChild as HTMLElement | null)?.style.setProperty(
          "width",
          `${lastClamped * 100}%`,
        );
      } else {
        (container.firstElementChild as HTMLElement | null)?.style.setProperty(
          "height",
          `${lastClamped * 100}%`,
        );
      }
    };

    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      // Only commit if the user actually dragged
      if (didMove) {
        onResize(paneId, lastClamped);
      }
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
        gap: display.gap,
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
          display={display}
        />
      </div>

      {/* Resize handle */}
      <div
        style={{
          [isH ? "width" : "height"]: display.gap > 0 ? display.gap : 4,
          [isH ? "marginLeft" : "marginTop"]: display.gap > 0 ? -(display.gap / 2) : 0,
          [isH ? "marginRight" : "marginBottom"]: display.gap > 0 ? -(display.gap / 2) : 0,
          cursor: isH ? "col-resize" : "row-resize",
          flexShrink: 0,
          background: "transparent",
          zIndex: 10,
          position: "relative",
        }}
        onMouseDown={handleResizeMouseDown}
        onMouseOver={(e) => {
          if (display.gap === 0)
            (e.target as HTMLElement).style.background = "var(--accent)";
        }}
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
          display={display}
        />
      </div>
    </div>
  );
}

// ── Pane type registry ───────────────────────────────────────────

interface PaneProps {
  paneId: string;
  cwd?: string;
  session?: string | null;
  rootPath?: string;
  isFocused?: boolean;
}

const PANE_REGISTRY: Record<string, React.ComponentType<PaneProps>> = {
  Terminal: TerminalTauri,
  Editor: EditorTauri,
  Explorer: ({ paneId, cwd, isFocused }) => <ExplorerTauri paneId={paneId} rootPath={cwd || ""} isFocused={isFocused} />,
  Chat: ChatTauri,
  Browser: BrowserTauri,
  RichText: RichTextTauri,
  HUD: HUDTauri,
  Info: InfoTauri,
  Chooser: ChooserPane,
  Menu: MenuTauri,
};

// ── Pane component (dispatches via registry) ─────────────────────

function PaneComponent({
  node,
  focused,
  onFocus,
  cwd,
  session,
  display,
}: {
  node: LayoutNode;
  focused: boolean;
  onFocus: (id: string) => void;
  cwd: string;
  session: string | null;
  display: DisplaySettings;
}) {
  const paneId = node.id!;
  const stack = useTabStack(paneId);
  const paneIdRef = useRef(paneId);
  paneIdRef.current = paneId;

  // Render type comes from the active tab name, not from the pane itself
  const activeTabName = stack.tabs[stack.activeIndex]?.name || "Info";
  const PaneImpl = PANE_REGISTRY[activeTabName] || PANE_REGISTRY.Info;

  // Map engine tabs to TabBar items
  const tabItems = stack.tabs.length > 0
    ? stack.tabs.map((t) => ({ name: t.name, isActive: t.is_active }))
    : [];

  // ── Content tabs (editor buffers, terminal sessions, etc.) ──
  const [contentState, setContentState] = useState<{
    tabs: { id: string; name: string; modified: boolean; preview: boolean }[];
    active: number;
  } | null>(null);

  const refreshContent = useCallback(async () => {
    try {
      const result = await dispatchCommand("content.tabs", {
        pane_id: paneIdRef.current,
      });
      if (result && result.tabs) {
        setContentState(result as any);
      } else {
        setContentState(null);
      }
    } catch {
      setContentState(null);
    }
  }, []);

  useEffect(() => {
    refreshContent();
  }, [paneId, activeTabName, refreshContent]);

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    listen("content-changed", (event: any) => {
      const payload = event.payload;
      if (payload?.pane_id === paneIdRef.current) {
        if (payload.state) {
          setContentState(payload.state as any);
        } else {
          refreshContent();
        }
      }
    }).then((fn) => { unlisten = fn; });
    return () => { if (unlisten) unlisten(); };
  }, [refreshContent]);

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    listen("editor-file-opened", (event: any) => {
      if (event.payload?.pane_id === paneIdRef.current) {
        setTimeout(refreshContent, 50);
      }
    }).then((fn) => { unlisten = fn; });
    return () => { if (unlisten) unlisten(); };
  }, [refreshContent]);

  // Map content state to ContentTabItem[]
  const contentTabs: ContentTabItem[] | undefined =
    contentState && contentState.tabs.length > 1
      ? contentState.tabs.map((t, i) => ({
          id: t.id,
          name: t.name,
          modified: t.modified,
          isActive: i === contentState.active,
        }))
      : undefined;

  const handleContentSelect = useCallback(async (index: number) => {
    try {
      const result = await dispatchCommand("content.switch", {
        pane_id: paneIdRef.current,
        index,
      });
      if (result && result.tabs) {
        setContentState(result as any);
      }
    } catch (e) {
      console.warn("content.switch failed:", e);
    }
  }, []);

  const handleContentClose = useCallback(async (index: number) => {
    try {
      const result = await dispatchCommand("content.close", {
        pane_id: paneIdRef.current,
        index,
      });
      if (result?.empty) {
        setContentState(null);
      } else if (result?.tabs) {
        setContentState(result as any);
      } else {
        refreshContent();
      }
    } catch (e) {
      console.warn("content.close failed:", e);
    }
  }, [refreshContent]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        overflow: "hidden",
        borderRadius: display.border_radius,
        border: focused
          ? "2px solid var(--accent)"
          : "2px solid transparent",
        transition: "border-color 0.15s, border-radius 0.2s",
      }}
      onMouseDown={() => onFocus(paneId)}
    >
      {/* Unified tab bar: module tabs | content tabs */}
      <TabBar
        tabs={tabItems}
        onSelect={stack.switchTab}
        onClose={() => stack.closeTab()}
        paneLabel={`${activeTabName} · ${paneId}`}
        contentTabs={contentTabs}
        onContentSelect={handleContentSelect}
        onContentClose={handleContentClose}
      />

      {/* Body */}
      <div
        style={{
          flex: 1,
          overflow: "hidden",
          background: "var(--bg)",
          opacity: display.pane_opacity,
        }}
      >
        <PaneImpl paneId={paneId} cwd={cwd} session={session} isFocused={focused} />
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
