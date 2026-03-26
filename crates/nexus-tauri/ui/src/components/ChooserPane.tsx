// ChooserPane — inline module chooser that fills the pane content area.
// Rendered when a tab's name is "Chooser". Fetches module list from the
// engine's menu system. Picking a module dispatches stack.set_content.

import { useState, useEffect } from "react";
import { dispatchCommand } from "../tauri";

interface MenuItem {
  label: string;
  type: string;
  payload: string;
  icon?: string;
  description?: string;
}

interface Props {
  paneId: string;
  cwd?: string;
  session?: string | null;
}

export default function ChooserPane({ paneId }: Props) {
  const [modules, setModules] = useState<MenuItem[]>([]);

  useEffect(() => {
    dispatchCommand("menu.get", { context: "modules" })
      .then((result: any) => {
        if (result && Array.isArray(result.items)) {
          setModules(result.items);
        }
      })
      .catch(() => {});
  }, []);

  const onSelect = async (item: MenuItem) => {
    await dispatchCommand("stack.set_content", {
      identity: paneId,
      name: item.payload,
    });
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        gap: 12,
        padding: 24,
      }}
    >
      <div
        style={{
          fontSize: 12,
          color: "var(--text-dim)",
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          marginBottom: 8,
        }}
      >
        Choose module
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
          gap: 8,
          width: "100%",
          maxWidth: 400,
        }}
      >
        {modules.map((mod_) => (
          <button
            key={mod_.label}
            onClick={() => onSelect(mod_)}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 4,
              padding: "16px 12px",
              background: "var(--bg-panel)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              color: "var(--text)",
              cursor: "pointer",
              fontFamily: "inherit",
              fontSize: 13,
              transition: "border-color 0.15s, background 0.15s",
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.borderColor = "var(--accent)";
              e.currentTarget.style.background = "var(--hover)";
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.background = "var(--bg-panel)";
            }}
          >
            <span style={{ fontSize: 16, color: "var(--accent)" }}>
              {mod_.icon || mod_.label[0]}
            </span>
            <span>{mod_.label}</span>
            {mod_.description && (
              <span style={{ fontSize: 10, color: "var(--text-dim)" }}>
                {mod_.description}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
