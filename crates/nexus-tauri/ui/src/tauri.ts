// Tauri IPC bridge — typed wrappers around invoke/listen.

import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

// -- Layout ------------------------------------------------------------------

export interface LayoutData {
  root: LayoutNode;
  focused: string;
  zoomed: string | null;
}

export interface LayoutNode {
  type: "Leaf" | "Split";
  // Leaf fields
  id?: string;
  // Split fields
  direction?: "Horizontal" | "Vertical";
  ratio?: number;
  left?: LayoutNode;
  right?: LayoutNode;
}

export async function getLayout(): Promise<LayoutData> {
  return invoke("get_layout");
}

export async function splitPane(direction: string): Promise<LayoutData> {
  return invoke("split_pane", { direction });
}

export async function navigatePane(direction: string): Promise<LayoutData> {
  return invoke("navigate_pane", { direction });
}

export async function focusPane(paneId: string): Promise<LayoutData> {
  return invoke("focus_pane", { paneId });
}

export async function closePane(paneId: string): Promise<LayoutData> {
  return invoke("close_pane", { paneId });
}

export async function zoomPane(): Promise<LayoutData> {
  return invoke("zoom_pane");
}

export async function resizePane(paneId: string, ratio: number): Promise<LayoutData> {
  return invoke("resize_pane", { paneId, ratio });
}

// -- Session -----------------------------------------------------------------

export async function getSession(): Promise<string | null> {
  return invoke("get_session");
}

export async function getCwd(): Promise<string> {
  return invoke("get_cwd");
}

// -- Filesystem --------------------------------------------------------------

export interface DirEntry {
  name: string;
  path: string;
  is_dir: boolean;
}

export async function readDir(path: string): Promise<DirEntry[]> {
  return invoke("read_dir", { path });
}

export async function readFile(path: string): Promise<string> {
  return invoke("read_file", { path });
}

// -- PTY ---------------------------------------------------------------------

export async function ptySpawn(paneId: string, cwd?: string): Promise<void> {
  return invoke("pty_spawn", { paneId, cwd });
}

export async function ptySpawnCmd(paneId: string, program: string, args?: string[], cwd?: string): Promise<void> {
  return invoke("pty_spawn_cmd", { paneId, program, args, cwd });
}

export async function ptyWrite(paneId: string, data: string): Promise<void> {
  return invoke("pty_write", { paneId, data });
}

export async function ptyResize(paneId: string, cols: number, rows: number): Promise<void> {
  return invoke("pty_resize", { paneId, cols, rows });
}

export async function ptyKill(paneId: string): Promise<void> {
  return invoke("pty_kill", { paneId });
}

// -- Agent -------------------------------------------------------------------

export async function agentSend(paneId: string, message: string, backend?: string, cwd?: string): Promise<void> {
  return invoke("agent_send", { paneId, message, backend, cwd });
}

// -- Keymap & Commands -------------------------------------------------------

export interface KeyBinding {
  key: string;   // e.g. "Alt+h"
  action: string; // e.g. "navigate.left"
}

export interface CommandEntry {
  id: string;
  label: string;
  category: string;
  binding: string | null;
}

export async function getKeymap(): Promise<KeyBinding[]> {
  return invoke("get_keymap");
}

export async function getCommands(): Promise<CommandEntry[]> {
  return invoke("get_commands");
}

export async function dispatchCommand(command: string, args?: Record<string, any>): Promise<any> {
  return invoke("dispatch_command", { command, args });
}

// -- Capabilities ------------------------------------------------------------

export interface CapabilityInfo {
  name: string;
  type: string;
  priority: number;
  available: boolean;
}

export async function getCapabilities(typeFilter?: string): Promise<CapabilityInfo[]> {
  const args = typeFilter ? { type: typeFilter } : undefined;
  const result = await invoke("dispatch_command", { command: "capabilities.list", args });
  return Array.isArray(result) ? result : [];
}

// -- Events ------------------------------------------------------------------

export function onPtyOutput(callback: (event: { paneId: string; data: number[] }) => void): Promise<() => void> {
  return listen("pty-output", (event: any) => callback(event.payload));
}

export interface AgentEvent {
  paneId: string;
  type: "start" | "text" | "done";
  backend?: string;
  text?: string;
  fullText?: string;
  exitCode?: number;
}

export function onAgentOutput(callback: (event: AgentEvent) => void): Promise<() => void> {
  return listen("agent-output", (event: any) => callback(event.payload));
}

// -- Layout & stack events ---------------------------------------------------

export function onLayoutChanged(callback: (layout: LayoutData) => void): Promise<() => void> {
  return listen("layout-changed", (event: any) => callback(event.payload));
}

export function onStackChanged(callback: (data: any) => void): Promise<() => void> {
  return listen("stack-changed", (event: any) => callback(event.payload));
}
