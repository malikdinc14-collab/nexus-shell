// Nexus Shell — main app.
// Renders layout tree from Rust engine, routes keyboard commands.
// The UI is a dumb renderer. All state and logic lives in the engine.

import React, { useState, useEffect, useCallback, useRef, Component } from "react";
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
  setDecorations,
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
import SettingsTauri from "./components/SettingsTauri";
import ChooserPane from "./components/ChooserPane";
import MenuTauri from "./components/MenuTauri";
import CommandPalette from "./components/CommandPalette";
import CommandLine from "./components/CommandLine";
import TabListOverlay from "./components/TabListOverlay";
import TabBar, { ContentTabItem } from "./components/TabBar";
import useTabStack from "./hooks/useTabStack";
import { listen } from "@tauri-apps/api/event";

// ── Drag state for Alt+drag pane rearrangement ──────────────────
interface DragState {
  sourcePaneId: string;
  startX: number;
  startY: number;
  active: boolean; // true once moved past threshold
}

export default function App() {
  const [layout, setLayout] = useState<LayoutData | null>(null);
  const [session, setSession] = useState<string | null>(null);
  const [cwd, setCwd] = useState("");
  const [cmdOpen, setCmdOpen] = useState(false);
  const [cmdLineOpen, setCmdLineOpen] = useState(false);
  const [tabListOpen, setTabListOpen] = useState(false);
  const [keymap, setKeymap] = useState<KeyBinding[]>([]);
  const [commands, setCommands] = useState<CommandEntry[]>([]);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [dropTarget, setDropTarget] = useState<{ paneId: string; zone: "center" | "left" | "right" | "top" | "bottom" } | null>(null);
  const [display, setDisplay] = useState<DisplaySettings>({
    gap: 0,
    background: "var(--bg)",
    border_radius: 0,
    pane_opacity: 1,
    show_status_bar: true,
    show_decorations: true,
  });

  // Init — fetch all state from engine (each call independent so one failure doesn't block all)
  useEffect(() => {
    getLayout().then(setLayout).catch((e) => console.error("init getLayout failed:", e));
    getSession().then(setSession).catch((e) => console.error("init getSession failed:", e));
    getCwd().then(setCwd).catch((e) => console.error("init getCwd failed:", e));
    getKeymap().then(setKeymap).catch((e) => console.error("init getKeymap failed:", e));
    getCommands().then(setCommands).catch((e) => console.error("init getCommands failed:", e));
    dispatchCommand("display.get")
      .then((disp) => { if (disp) setDisplay(disp as DisplaySettings); })
      .catch(() => {});
  }, []);

  // Sync body transparency attribute (surface-specific DOM concern)
  useEffect(() => {
    document.body.dataset.transparent =
      display.background === "transparent" ? "true" : "false";
  }, [display.background]);

  // Sync window decorations with engine state
  useEffect(() => {
    setDecorations(display.show_decorations).catch(() => {});
  }, [display.show_decorations]);

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

  // ── Alt+drag handlers ───────────────────────────────────────────
  const handlePaneDragStart = useCallback((paneId: string, e: React.MouseEvent) => {
    if (!e.altKey) return;
    e.preventDefault();
    e.stopPropagation();
    setDragState({ sourcePaneId: paneId, startX: e.clientX, startY: e.clientY, active: false });
  }, []);

  useEffect(() => {
    if (!dragState) return;

    const onMove = (e: MouseEvent) => {
      if (!dragState.active) {
        const dx = e.clientX - dragState.startX;
        const dy = e.clientY - dragState.startY;
        if (Math.sqrt(dx * dx + dy * dy) > 8) {
          setDragState({ ...dragState, active: true });
        }
      }
    };

    document.body.style.cursor = "grabbing";

    const onUp = async () => {
      document.body.style.cursor = "";
      if (dragState.active && dropTarget && dropTarget.paneId !== dragState.sourcePaneId) {
        try {
          // All drop zones use direct swap — simple and predictable
          const result = await dispatchCommand("pane.swap", {
            pane_id: dragState.sourcePaneId,
            target_id: dropTarget.paneId,
          });
          if (result && typeof result === "object" && "root" in result && "focused" in result) {
            setLayout(result as LayoutData);
          }
        } catch (err) {
          console.warn("Drag rearrange failed:", err);
        }
      }
      setDragState(null);
      setDropTarget(null);
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
  }, [dragState, dropTarget]);

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
          flexShrink: 0,
        } as React.CSSProperties & { WebkitAppRegion: string }}
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
            dragState={dragState}
            onDragStart={handlePaneDragStart}
            onDropTargetChange={setDropTarget}
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
          display: display.show_status_bar === false ? "none" : "flex",
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

// ── Per-pane error boundary ───────────────────────────────────────

class PaneErrorBoundary extends Component<
  { paneId: string; children: React.ReactNode },
  { error: string | null }
> {
  constructor(props: { paneId: string; children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { error: error.message };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(`Pane ${this.props.paneId} crashed:`, error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 16, color: "var(--red)", fontSize: 11, overflow: "auto" }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>Pane error</div>
          <div style={{ opacity: 0.7 }}>{this.state.error}</div>
        </div>
      );
    }
    return this.props.children;
  }
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
  dragState,
  onDragStart,
  onDropTargetChange,
}: {
  node: LayoutNode;
  focused: string;
  onFocus: (id: string) => void;
  onResize: (paneId: string, ratio: number) => Promise<void>;
  cwd: string;
  session: string | null;
  display: DisplaySettings;
  dragState: DragState | null;
  onDragStart: (paneId: string, e: React.MouseEvent) => void;
  onDropTargetChange: (target: { paneId: string; zone: "center" | "left" | "right" | "top" | "bottom" } | null) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  if (node.type === "Leaf") {
    const isDragSource = dragState?.active && dragState.sourcePaneId === node.id;
    return (
      <PaneErrorBoundary paneId={node.id!}>
        <PaneComponent
          node={node}
          focused={node.id === focused}
          onFocus={onFocus}
          cwd={cwd}
          session={session}
          display={display}
          isDragSource={!!isDragSource}
          dragActive={!!dragState?.active}
          onDragStart={onDragStart}
          onDropTargetChange={onDropTargetChange}
        />
      </PaneErrorBoundary>
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
          key={firstLeafId(node.left!)}
          node={node.left!}
          focused={focused}
          onFocus={onFocus}
          onResize={onResize}
          cwd={cwd}
          session={session}
          display={display}
          dragState={dragState}
          onDragStart={onDragStart}
          onDropTargetChange={onDropTargetChange}
        />
      </div>

      {/* Resize handle */}
      <div
        style={{
          [isH ? "width" : "height"]: Math.max(display.gap, 6),
          [isH ? "marginLeft" : "marginTop"]: -(Math.max(display.gap, 6) / 2),
          [isH ? "marginRight" : "marginBottom"]: -(Math.max(display.gap, 6) / 2),
          cursor: isH ? "col-resize" : "row-resize",
          flexShrink: 0,
          background: "transparent",
          zIndex: 10,
          position: "relative",
        }}
        onMouseDown={handleResizeMouseDown}
        onMouseOver={(e) => {
          (e.target as HTMLElement).style.background =
            display.gap === 0 ? "var(--accent)" : "rgba(122,162,247,0.2)";
        }}
        onMouseOut={(e) =>
          ((e.target as HTMLElement).style.background = "transparent")
        }
      />

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <NodeRenderer
          key={firstLeafId(node.right!)}
          node={node.right!}
          focused={focused}
          onFocus={onFocus}
          onResize={onResize}
          cwd={cwd}
          session={session}
          display={display}
          dragState={dragState}
          onDragStart={onDragStart}
          onDropTargetChange={onDropTargetChange}
        />
      </div>
    </div>
  );
}

// ── Focus guard — blurs previous element so new pane can claim focus ──

function PaneFocusGuard({ focused, children }: { focused: boolean; children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (focused && ref.current) {
      // Blur whatever currently has focus so the child component's
      // useEffect can cleanly claim it
      const active = document.activeElement;
      if (active && active instanceof HTMLElement && !ref.current.contains(active)) {
        active.blur();
      }
    }
  }, [focused]);

  return <div ref={ref} style={{ display: "contents" }}>{children}</div>;
}

// ── Pane type registry ───────────────────────────────────────────

interface PaneProps {
  paneId: string;
  cwd?: string;
  session?: string | null;
  rootPath?: string;
  isFocused?: boolean;
  activeContentId?: string;
}

const PANE_REGISTRY: Record<string, React.ComponentType<PaneProps>> = {
  Terminal: TerminalTauri,
  Editor: EditorTauri,
  Explorer: ({ paneId, cwd, isFocused }) => <ExplorerTauri paneId={paneId} rootPath={cwd || ""} isFocused={isFocused} />,
  Chat: ChatTauri,
  Browser: BrowserTauri,
  RichText: RichTextTauri,
  HUD: HUDTauri,
  Settings: SettingsTauri,
  Info: InfoTauri,
  Chooser: ChooserPane,
  Menu: MenuTauri,
};

// ── Pane component (dispatches via registry) ─────────────────────

type DropZone = "center" | "left" | "right" | "top" | "bottom";

function PaneComponent({
  node,
  focused,
  onFocus,
  cwd,
  session,
  display,
  isDragSource = false,
  dragActive = false,
  onDragStart,
  onDropTargetChange,
}: {
  node: LayoutNode;
  focused: boolean;
  onFocus: (id: string) => void;
  cwd: string;
  session: string | null;
  display: DisplaySettings;
  isDragSource?: boolean;
  dragActive?: boolean;
  onDragStart?: (paneId: string, e: React.MouseEvent) => void;
  onDropTargetChange?: (target: { paneId: string; zone: DropZone } | null) => void;
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

  // Drop zone detection for drag targets
  const [localDropZone, setLocalDropZone] = useState<DropZone | null>(null);
  const paneRef = useRef<HTMLDivElement>(null);

  const handleDragMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragActive || isDragSource || !paneRef.current) return;
    const rect = paneRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;

    // Edge zones: 25% from each edge
    let zone: DropZone = "center";
    if (x < 0.25) zone = "left";
    else if (x > 0.75) zone = "right";
    else if (y < 0.25) zone = "top";
    else if (y > 0.75) zone = "bottom";

    setLocalDropZone(zone);
    onDropTargetChange?.({ paneId, zone });
  }, [dragActive, isDragSource, paneId, onDropTargetChange]);

  const handleDragMouseLeave = useCallback(() => {
    if (dragActive) {
      setLocalDropZone(null);
      onDropTargetChange?.(null);
    }
  }, [dragActive, onDropTargetChange]);

  // Clear local drop zone when drag ends
  useEffect(() => {
    if (!dragActive) setLocalDropZone(null);
  }, [dragActive]);

  return (
    <div
      ref={paneRef}
      style={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        overflow: "hidden",
        borderRadius: display.border_radius,
        border: focused
          ? "2px solid var(--accent)"
          : "2px solid transparent",
        opacity: isDragSource ? 0.4 : 1,
        transition: "border-color 0.15s, border-radius 0.2s, opacity 0.15s",
        position: "relative",
      }}
      onMouseDown={(e) => {
        if (e.altKey && onDragStart) {
          onDragStart(paneId, e);
        } else {
          onFocus(paneId);
        }
      }}
      onMouseMove={handleDragMouseMove}
      onMouseLeave={handleDragMouseLeave}
    >
      {/* Unified tab bar: module tabs | content tabs */}
      <TabBar
        tabs={tabItems}
        onSelect={stack.switchTab}
        onClose={async (index: number) => {
          const result = await stack.closeTab(index);
          // stack.close now returns a layout object — update layout to re-render
          if (result && typeof result === "object" && "root" in result && "focused" in result) {
            // Pane layout changed — update and refocus
            onFocus((result as any).focused ?? paneId);
          }
        }}
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
        <PaneFocusGuard focused={focused}>
          <PaneImpl paneId={paneId} cwd={cwd} session={session} isFocused={focused} activeContentId={contentState?.tabs?.[contentState.active]?.id} />
        </PaneFocusGuard>
      </div>

      {/* Drop zone overlay */}
      {dragActive && !isDragSource && localDropZone && (
        <DropZoneOverlay zone={localDropZone} />
      )}
    </div>
  );
}

// ── Drop zone indicator ─────────────────────────────────────────

function DropZoneOverlay({ zone }: { zone: DropZone }) {
  const baseStyle: React.CSSProperties = {
    position: "absolute",
    background: "var(--accent)",
    opacity: 0.2,
    borderRadius: 4,
    transition: "all 0.1s ease",
    pointerEvents: "none",
    zIndex: 20,
  };

  const positions: Record<DropZone, React.CSSProperties> = {
    center: { inset: "10%", ...baseStyle },
    left:   { top: 0, left: 0, bottom: 0, width: "30%", ...baseStyle },
    right:  { top: 0, right: 0, bottom: 0, width: "30%", ...baseStyle },
    top:    { top: 0, left: 0, right: 0, height: "30%", ...baseStyle },
    bottom: { bottom: 0, left: 0, right: 0, height: "30%", ...baseStyle },
  };

  return (
    <div style={positions[zone]}>
      <div style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        fontSize: 11,
        fontWeight: 700,
        color: "var(--accent)",
        opacity: 1,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
        pointerEvents: "none",
      }}>
        Swap
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

    // On macOS, Alt+key produces a special character in e.key (e.g. Alt+s → "ß").
    // Use e.code (physical key, e.g. "KeyS") as fallback when Alt is held.
    let pressedKey: string;
    if (needAlt && e.altKey) {
      if (e.code.startsWith("Key")) {
        pressedKey = e.code.slice(3).toLowerCase();
      } else if (e.code.startsWith("Digit")) {
        pressedKey = e.code.slice(5);
      } else {
        // Non-alpha keys (Equal, Minus, etc.) — use e.key directly
        pressedKey = e.key.toLowerCase();
      }
    } else {
      pressedKey = e.key.toLowerCase();
    }

    if (
      pressedKey === key &&
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
