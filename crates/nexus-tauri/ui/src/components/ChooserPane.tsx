// ChooserPane — inline module chooser that fills the pane content area.
// Rendered when a tab's name is "Chooser". Fetches module list from the
// engine's menu system. Picking a module dispatches stack.set_content.

import { useState, useEffect, useRef } from "react";
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
  isFocused?: boolean;
}

export default function ChooserPane({ paneId, isFocused }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
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
    if (item.type === "settings" && item.payload) {
      // Open the config file in the editor
      await dispatchCommand("editor.open", { path: item.payload, pane_id: paneId });
      await dispatchCommand("stack.set_content", { identity: paneId, name: "Editor" });
    } else {
      await dispatchCommand("stack.set_content", {
        identity: paneId,
        name: item.payload,
      });
    }
  };

  useEffect(() => {
    if (isFocused && containerRef.current) {
      containerRef.current.focus();
    }
  }, [isFocused]);

  // Pure CSS — container query handles the breakpoint, no JS measurement.
  return (
    <div ref={containerRef} tabIndex={0} className="chooser-root" style={{ outline: "none" }}>
      <div className="chooser-header">Choose module</div>
      <div className="chooser-items">
        {modules.map((mod_) => (
          <button
            key={mod_.label}
            className="chooser-item"
            onClick={() => onSelect(mod_)}
          >
            <span className="chooser-icon">{mod_.icon || mod_.label[0]}</span>
            <span className="chooser-label">{mod_.label}</span>
            {mod_.description && (
              <span className="chooser-desc">{mod_.description}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
