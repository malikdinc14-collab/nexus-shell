// TabListOverlay — Alt+T to show tabs in focused pane's stack.
// Select a tab to switch to it.

import { useEffect, useState } from "react";
import { Command } from "cmdk";
import { dispatchCommand } from "../tauri";

interface TabInfo {
  index: number;
  name: string;
  is_active: boolean;
}

interface Props {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  focusedPaneId: string;
}

export default function TabListOverlay({ isOpen, setIsOpen, focusedPaneId }: Props) {
  const [tabs, setTabs] = useState<TabInfo[]>([]);

  // Fetch tabs when overlay opens
  useEffect(() => {
    if (!isOpen) return;
    dispatchCommand("stack.list", { identity: focusedPaneId })
      .then((result: any) => {
        if (Array.isArray(result)) {
          setTabs(result);
        } else if (result && Array.isArray(result.tabs)) {
          setTabs(result.tabs);
        } else {
          setTabs([]);
        }
      })
      .catch(() => setTabs([]));
  }, [isOpen, focusedPaneId]);

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

  if (!isOpen) return null;

  const onSelect = async (index: number) => {
    await dispatchCommand("stack.switch", {
      identity: focusedPaneId,
      index: String(index),
    });
    setIsOpen(false);
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 100,
        display: "flex",
        justifyContent: "center",
        paddingTop: 60,
      }}
      onClick={() => setIsOpen(false)}
    >
      <div
        style={{
          width: 320,
          background: "var(--bg-panel)",
          border: "1px solid var(--border)",
          borderRadius: 6,
          overflow: "hidden",
          maxHeight: 300,
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <Command label="Tab Stack">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              padding: "10px 14px",
              borderBottom: "1px solid var(--border)",
              gap: 8,
            }}
          >
            <span style={{ color: "var(--accent)", fontSize: 12 }}>tabs:</span>
            <Command.Input
              placeholder="Filter tabs..."
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
              maxHeight: 220,
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
              No tabs in this pane.
            </Command.Empty>

            {tabs.map((tab, i) => (
              <Command.Item
                key={i}
                onSelect={() => onSelect(tab.index)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 12px",
                  borderRadius: 4,
                  fontSize: 13,
                  color: tab.is_active ? "var(--accent)" : "var(--text)",
                  cursor: "pointer",
                }}
              >
                <span>
                  <span style={{ color: "var(--text-dim)", marginRight: 8, fontSize: 11 }}>
                    {tab.index + 1}
                  </span>
                  {tab.name}
                </span>
                {tab.is_active && (
                  <span
                    style={{
                      fontSize: 10,
                      color: "var(--accent)",
                      background: "var(--accent-dim)",
                      padding: "1px 6px",
                      borderRadius: 3,
                    }}
                  >
                    active
                  </span>
                )}
              </Command.Item>
            ))}
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
