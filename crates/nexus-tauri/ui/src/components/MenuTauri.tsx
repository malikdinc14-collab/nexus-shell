// MenuPane — inline menu browser that fills the pane content area.
// Fetches menu items from the engine via menu.get/navigate/back/execute.
// Renders as a navigable list with folder drill-down and action dispatch.

import { useState, useEffect, useCallback } from "react";
import { dispatchCommand } from "../tauri";

interface MenuItem {
  label: string;
  type: string;
  payload: string;
  icon?: string;
  description?: string;
}

interface MenuList {
  name: string;
  icon?: string;
  layout: string; // "list" | "grid"
  items: MenuItem[];
}

interface Props {
  paneId: string;
  cwd?: string;
  session?: string | null;
}

export default function MenuPane({ paneId }: Props) {
  const [menu, setMenu] = useState<MenuList | null>(null);
  const [historyDepth, setHistoryDepth] = useState(0);
  const [filter, setFilter] = useState("");

  const fetchMenu = useCallback(async (context?: string) => {
    const args: Record<string, string> = {};
    if (context) args.context = context;
    const result = await dispatchCommand("menu.get", args);
    if (result && typeof result === "object") {
      setMenu(result as MenuList);
      setFilter("");
    }
  }, []);

  useEffect(() => {
    fetchMenu("home");
  }, [fetchMenu]);

  const handleNavigate = useCallback(async (context: string) => {
    const result = await dispatchCommand("menu.navigate", { context });
    if (result && typeof result === "object") {
      setMenu(result as MenuList);
      setHistoryDepth((d) => d + 1);
      setFilter("");
    }
  }, []);

  const handleBack = useCallback(async () => {
    const result = await dispatchCommand("menu.back");
    if (result && typeof result === "object") {
      setMenu(result as MenuList);
      setHistoryDepth((d) => Math.max(0, d - 1));
      setFilter("");
    }
  }, []);

  const handleSelect = useCallback(
    async (item: MenuItem) => {
      if (item.type === "separator" || item.type === "info") return;

      if (item.type === "folder") {
        handleNavigate(item.payload);
        return;
      }

      // For modules, set the tab content to the module name
      if (item.type === "module") {
        await dispatchCommand("stack.set_content", {
          identity: paneId,
          name: item.payload,
        });
        return;
      }

      // For all other types, let the engine handle it
      await dispatchCommand("menu.execute", {
        type: item.type,
        payload: item.payload,
      });
    },
    [paneId, handleNavigate],
  );

  if (!menu) {
    return (
      <div style={{ padding: 24, color: "var(--text-dim)" }}>Loading menu...</div>
    );
  }

  const filtered = menu.items.filter(
    (item) =>
      item.type === "separator" ||
      item.label.toLowerCase().includes(filter.toLowerCase()),
  );

  const isGrid = menu.layout === "grid";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 12px",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}
      >
        {historyDepth > 0 && (
          <button
            onClick={handleBack}
            style={{
              background: "none",
              border: "1px solid var(--border)",
              borderRadius: 4,
              color: "var(--text)",
              cursor: "pointer",
              padding: "2px 8px",
              fontSize: 12,
              fontFamily: "inherit",
            }}
          >
            &larr; Back
          </button>
        )}
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "var(--text)",
          }}
        >
          {menu.icon && (
            <span style={{ marginRight: 6, color: "var(--accent)" }}>
              {menu.icon}
            </span>
          )}
          {menu.name || "Menu"}
        </span>
      </div>

      {/* Filter */}
      <div style={{ padding: "6px 12px", flexShrink: 0 }}>
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter..."
          style={{
            width: "100%",
            background: "var(--bg-panel)",
            border: "1px solid var(--border)",
            borderRadius: 4,
            padding: "4px 8px",
            color: "var(--text)",
            fontSize: 12,
            fontFamily: "inherit",
            outline: "none",
          }}
          onFocus={(e) =>
            (e.currentTarget.style.borderColor = "var(--accent)")
          }
          onBlur={(e) =>
            (e.currentTarget.style.borderColor = "var(--border)")
          }
        />
      </div>

      {/* Items */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          padding: isGrid ? "8px 12px" : "4px 0",
          ...(isGrid
            ? {
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
                gap: 8,
                alignContent: "start",
              }
            : {}),
        }}
      >
        {filtered.map((item, i) =>
          item.type === "separator" ? (
            <div
              key={`sep-${i}`}
              style={{
                height: 1,
                background: "var(--border)",
                margin: isGrid ? "4px 0" : "4px 12px",
                gridColumn: isGrid ? "1 / -1" : undefined,
              }}
            />
          ) : isGrid ? (
            <GridItem key={item.label} item={item} onSelect={handleSelect} />
          ) : (
            <ListItem key={item.label} item={item} onSelect={handleSelect} />
          ),
        )}
        {filtered.length === 0 && (
          <div
            style={{
              padding: "24px 12px",
              color: "var(--text-dim)",
              fontSize: 12,
              textAlign: "center",
            }}
          >
            No items match "{filter}"
          </div>
        )}
      </div>
    </div>
  );
}

// ── List item ─────────────────────────────────────────────────────────

function ListItem({
  item,
  onSelect,
}: {
  item: MenuItem;
  onSelect: (item: MenuItem) => void;
}) {
  return (
    <div
      onClick={() => onSelect(item)}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "6px 12px",
        cursor: "pointer",
        fontSize: 13,
        transition: "background 0.1s",
      }}
      onMouseOver={(e) =>
        (e.currentTarget.style.background = "var(--hover)")
      }
      onMouseOut={(e) =>
        (e.currentTarget.style.background = "transparent")
      }
    >
      {item.icon && (
        <span
          style={{
            width: 20,
            textAlign: "center",
            color: "var(--accent)",
            fontSize: 14,
            flexShrink: 0,
          }}
        >
          {item.icon}
        </span>
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ color: "var(--text)" }}>{item.label}</div>
        {item.description && (
          <div
            style={{
              fontSize: 11,
              color: "var(--text-dim)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {item.description}
          </div>
        )}
      </div>
      {item.type === "folder" && (
        <span style={{ color: "var(--text-dim)", fontSize: 11 }}>&rsaquo;</span>
      )}
    </div>
  );
}

// ── Grid item ─────────────────────────────────────────────────────────

function GridItem({
  item,
  onSelect,
}: {
  item: MenuItem;
  onSelect: (item: MenuItem) => void;
}) {
  return (
    <button
      onClick={() => onSelect(item)}
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
      {item.icon && (
        <span style={{ fontSize: 16, color: "var(--accent)" }}>
          {item.icon}
        </span>
      )}
      <span>{item.label}</span>
      {item.description && (
        <span style={{ fontSize: 10, color: "var(--text-dim)" }}>
          {item.description}
        </span>
      )}
    </button>
  );
}
