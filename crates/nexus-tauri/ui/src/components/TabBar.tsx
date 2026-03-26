// TabBar — generic, reusable tab strip for any pane.
// Pure UI component. No engine knowledge. Receives data + callbacks.
// Supports optional content tabs (editor buffers, etc.) after a separator.

export interface TabItem {
  name: string;
  isActive: boolean;
}

export interface ContentTabItem {
  id: string;
  name: string;
  modified: boolean;
  isActive: boolean;
}

interface TabBarProps {
  tabs: TabItem[];
  onSelect: (index: number) => void;
  onClose?: (index: number) => void;
  paneLabel?: string;
  contentTabs?: ContentTabItem[];
  onContentSelect?: (index: number) => void;
  onContentClose?: (index: number) => void;
}

export default function TabBar({
  tabs,
  onSelect,
  onClose,
  paneLabel,
  contentTabs,
  onContentSelect,
  onContentClose,
}: TabBarProps) {
  const hasContentTabs = contentTabs && contentTabs.length > 1;

  if (tabs.length <= 1 && !paneLabel && !hasContentTabs) return null;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        height: 26,
        background: "var(--bg-panel)",
        borderBottom: "1px solid var(--border)",
        overflow: "hidden",
        flexShrink: 0,
        fontSize: 11,
      }}
    >
      {/* Pane label (when single module tab) */}
      {paneLabel && tabs.length <= 1 && !hasContentTabs && (
        <span
          style={{
            padding: "0 10px",
            color: "var(--text-dim)",
            textTransform: "uppercase",
            letterSpacing: 0.5,
          }}
        >
          {paneLabel}
        </span>
      )}

      {/* Module tabs */}
      {(tabs.length > 1 || hasContentTabs) &&
        tabs.map((tab, i) => (
          <div
            key={i}
            onClick={() => onSelect(i)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              padding: "0 10px",
              height: "100%",
              cursor: "pointer",
              borderRight: "1px solid var(--border)",
              background: tab.isActive ? "var(--bg)" : "var(--bg-panel)",
              color: tab.isActive ? "var(--text-bright)" : "var(--text-dim)",
              whiteSpace: "nowrap",
              transition: "background 0.1s",
            }}
          >
            <span>{tab.name}</span>
            {onClose && i > 0 && (
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  onClose(i);
                }}
                style={{ cursor: "pointer", opacity: 0.4, fontSize: 13, lineHeight: 1 }}
                onMouseOver={(e) => ((e.target as HTMLElement).style.opacity = "1")}
                onMouseOut={(e) => ((e.target as HTMLElement).style.opacity = "0.4")}
              >
                x
              </span>
            )}
          </div>
        ))}

      {/* Separator */}
      {hasContentTabs && (
        <div
          style={{
            width: 1,
            height: 14,
            background: "var(--text-dim)",
            opacity: 0.3,
            margin: "0 2px",
            flexShrink: 0,
          }}
        />
      )}

      {/* Content tabs */}
      {hasContentTabs &&
        contentTabs!.map((tab, i) => (
          <div
            key={tab.id}
            onClick={() => onContentSelect?.(i)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              padding: "0 10px",
              height: "100%",
              cursor: "pointer",
              borderRight: "1px solid var(--border)",
              background: tab.isActive ? "var(--bg)" : "var(--bg-panel)",
              color: tab.isActive ? "var(--text-bright)" : "var(--text-dim)",
              whiteSpace: "nowrap",
              transition: "background 0.1s",
              borderBottom: tab.isActive
                ? "2px solid var(--accent)"
                : "2px solid transparent",
            }}
          >
            <span>
              {tab.modified ? "\u25CF " : ""}
              {tab.name}
            </span>
            {onContentClose && (
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  onContentClose(i);
                }}
                style={{
                  cursor: "pointer",
                  opacity: 0.4,
                  fontSize: 12,
                  lineHeight: 1,
                  marginLeft: 2,
                }}
                onMouseOver={(e) => ((e.target as HTMLElement).style.opacity = "1")}
                onMouseOut={(e) => ((e.target as HTMLElement).style.opacity = "0.4")}
              >
                x
              </span>
            )}
          </div>
        ))}
    </div>
  );
}
