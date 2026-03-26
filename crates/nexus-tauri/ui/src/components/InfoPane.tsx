// Info pane — session info and keyboard shortcuts reference.

interface Props {
  paneId: string;
  session: string | null;
  cwd: string;
}

export default function InfoPane({ paneId, session, cwd }: Props) {
  return (
    <div style={{ padding: 12, fontSize: 12, lineHeight: 1.8 }}>
      <div style={{ color: "var(--accent)", marginBottom: 8 }}>
        Nexus Shell
      </div>
      <div>Rust engine embedded in-process.</div>

      <div style={{ color: "var(--text-dim)", marginTop: 16, marginBottom: 4 }}>
        Session
      </div>
      <div style={{ color: "var(--text-bright)" }}>{session || "none"}</div>
      <div style={{ color: "var(--text-bright)", fontSize: 11 }}>{cwd}</div>

      <div style={{ color: "var(--text-dim)", marginTop: 16, marginBottom: 4 }}>
        Keyboard
      </div>
      <Shortcut keys="Ctrl+\" label="Command palette" />
      <Shortcut keys="Alt+H/J/K/L" label="Navigate panes" />
      <Shortcut keys="Alt+V" label="Split vertical" />
      <Shortcut keys="Alt+S" label="Split horizontal" />
      <Shortcut keys="Alt+Z" label="Zoom toggle" />
      <Shortcut keys="Alt+W" label="Close pane" />
      <Shortcut keys="Alt+T" label="New terminal" />
    </div>
  );
}

function Shortcut({ keys, label }: { keys: string; label: string }) {
  return (
    <div style={{ display: "flex", gap: 8 }}>
      <span
        style={{
          color: "var(--text-bright)",
          minWidth: 120,
          fontFamily: "inherit",
        }}
      >
        {keys}
      </span>
      <span>{label}</span>
    </div>
  );
}
