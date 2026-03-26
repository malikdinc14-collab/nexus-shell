// Command palette — Alt+P to open.
// Commands fetched from engine, grouped by category.

import { useEffect, useMemo } from "react";
import { Command } from "cmdk";
import { CommandEntry } from "../tauri";

interface Props {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  onCommand: (cmd: string, args?: Record<string, string>) => void;
  commands: CommandEntry[];
}

export default function CommandPalette({ isOpen, setIsOpen, onCommand, commands }: Props) {
  // Escape to close (open/close is managed by App.tsx keyboard handler)
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [isOpen, setIsOpen]);

  // Group commands by category
  const groups = useMemo(() => {
    const map = new Map<string, CommandEntry[]>();
    for (const cmd of commands) {
      const list = map.get(cmd.category) || [];
      list.push(cmd);
      map.set(cmd.category, list);
    }
    return map;
  }, [commands]);

  if (!isOpen) return null;

  const run = (cmd: string) => {
    onCommand(cmd);
    setIsOpen(false);
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 100,
        background: "rgba(0, 0, 0, 0.5)",
        backdropFilter: "blur(4px)",
        display: "flex",
        justifyContent: "center",
        paddingTop: "20vh",
      }}
      onClick={() => setIsOpen(false)}
    >
      <div
        style={{
          width: 560,
          background: "var(--bg-panel)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          overflow: "hidden",
          maxHeight: "50vh",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <Command label="Nexus Command Palette">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              padding: "10px 14px",
              borderBottom: "1px solid var(--border)",
              gap: 8,
            }}
          >
            <span style={{ color: "var(--accent)", fontSize: 12 }}>:</span>
            <Command.Input
              placeholder="Type a command..."
              autoFocus
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                color: "var(--text-bright)",
                fontFamily: "inherit",
                fontSize: 13,
              }}
            />
          </div>

          <Command.List
            style={{
              maxHeight: "40vh",
              overflow: "auto",
              padding: 6,
            }}
          >
            <Command.Empty
              style={{
                padding: 20,
                textAlign: "center",
                color: "var(--text-dim)",
                fontSize: 12,
              }}
            >
              No commands found.
            </Command.Empty>

            {Array.from(groups.entries()).map(([category, cmds]) => (
              <Command.Group
                key={category}
                heading={category}
                style={{
                  fontSize: 10,
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  color: "var(--text-dim)",
                  padding: "6px 8px 2px",
                }}
              >
                {cmds.map((cmd) => (
                  <Command.Item
                    key={cmd.id}
                    onSelect={() => run(cmd.id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "6px 10px",
                      borderRadius: 4,
                      fontSize: 12,
                      color: "var(--text)",
                      cursor: "pointer",
                    }}
                  >
                    <span>{cmd.label}</span>
                    {cmd.binding && (
                      <span
                        style={{
                          fontSize: 10,
                          color: "var(--text-dim)",
                          background: "var(--bg)",
                          padding: "1px 6px",
                          borderRadius: 3,
                          border: "1px solid var(--border)",
                        }}
                      >
                        {cmd.binding}
                      </span>
                    )}
                  </Command.Item>
                ))}
              </Command.Group>
            ))}
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
