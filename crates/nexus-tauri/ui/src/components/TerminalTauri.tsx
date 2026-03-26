// TerminalTauri — xterm.js with Tauri PTY backend.
// Session metadata managed through dispatch("terminal.*").
// PTY I/O uses Tauri IPC (surface-specific — raw bytes need direct pipe).

import { useEffect, useRef } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { ptySpawn, ptyWrite, ptyResize, onPtyOutput, dispatchCommand } from "../tauri";

const THEME = {
  background: "#1a1b26",
  foreground: "#c0caf5",
  cursor: "#7aa2f7",
  selectionBackground: "rgba(122, 162, 247, 0.3)",
  black: "#15161e",
  red: "#f7768e",
  green: "#9ece6a",
  yellow: "#e0af68",
  blue: "#7aa2f7",
  magenta: "#bb9af7",
  cyan: "#7dcfff",
  white: "#a9b1d6",
  brightBlack: "#414868",
  brightRed: "#f7768e",
  brightGreen: "#9ece6a",
  brightYellow: "#e0af68",
  brightBlue: "#7aa2f7",
  brightMagenta: "#bb9af7",
  brightCyan: "#7dcfff",
  brightWhite: "#c0caf5",
};

interface Props {
  paneId: string;
  cwd?: string;
  onExit?: () => void;
  isFocused?: boolean;
}

export default function TerminalTauri({ paneId, cwd, onExit, isFocused }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const term = new Terminal({
      cursorBlink: true,
      theme: THEME,
      fontFamily: '"JetBrains Mono", "Fira Code", monospace',
      fontSize: 13,
      allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(containerRef.current);
    fitAddon.fit();

    termRef.current = term;
    fitRef.current = fitAddon;

    // Register session with engine
    dispatchCommand("terminal.register", { pane_id: paneId, cwd });

    // PTY output -> xterm
    let unlisten: (() => void) | null = null;
    onPtyOutput((event) => {
      if (event.paneId === paneId) {
        const bytes = new Uint8Array(event.data);
        term.write(bytes);
      }
    }).then((fn) => {
      unlisten = fn;
    });

    // User input -> PTY
    term.onData((data) => {
      ptyWrite(paneId, data);
    });

    // Resize -> PTY
    term.onResize((size) => {
      ptyResize(paneId, size.cols, size.rows);
    });

    // Spawn the PTY
    ptySpawn(paneId, cwd).catch((e) => {
      term.writeln(`\r\n\x1b[31mFailed to spawn PTY: ${e}\x1b[0m`);
    });

    // Auto-fit on container resize
    const observer = new ResizeObserver(() => {
      fitAddon.fit();
    });
    observer.observe(containerRef.current);

    return () => {
      // Unregister session
      dispatchCommand("terminal.remove", { pane_id: paneId });
      term.dispose();
      observer.disconnect();
      if (unlisten) unlisten();
    };
  }, [paneId]);

  // Focus xterm when this pane becomes focused
  useEffect(() => {
    if (isFocused && termRef.current) {
      termRef.current.focus();
    }
  }, [isFocused]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", background: "#1a1b26" }}
    />
  );
}
