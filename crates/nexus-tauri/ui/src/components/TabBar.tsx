// TabBar — generic, reusable tab strip for any pane.
// Pure UI component. No engine knowledge. Receives data + callbacks.

export interface TabItem {
  name: string;
  isActive: boolean;
}

interface TabBarProps {
  tabs: TabItem[];
  onSelect: (index: number) => void;
  onClose?: (index: number) => void;
  paneLabel?: string;
}

export default function TabBar({ tabs, onSelect, onClose, paneLabel }: TabBarProps) {
  if (tabs.length <= 1 && !paneLabel) return null;

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
      {paneLabel && tabs.length <= 1 && (
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

      {tabs.length > 1 &&
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
    </div>
  );
}
