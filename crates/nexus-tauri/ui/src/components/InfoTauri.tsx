// InfoTauri — Tauri surface for the Info module.
// Fetches all data from the engine via info.get dispatch.

import { useState, useEffect } from "react";
import { dispatchCommand } from "../tauri";

interface InfoData {
  session: string | null;
  cwd: string;
  layout: {
    pane_count: number;
    focused: string;
    zoomed: string | null;
    panes: { id: string; is_focused: boolean }[];
  };
  display: {
    gap: number;
    background: string;
    border_radius: number;
    pane_opacity: number;
  };
  backends: {
    entries: { module: string; backend: string; available: boolean }[];
  };
  stacks: {
    identity: string;
    tab_count: number;
    active_tab: string;
    tabs: string[];
  }[];
  surfaces: {
    id: string;
    name: string;
    mode: string;
  }[];
  system: {
    version: string;
    pid: number;
    uptime_secs: number;
  };
}

interface Props {
  paneId: string;
  cwd?: string;
  session?: string | null;
}

export default function InfoTauri({ paneId }: Props) {
  const [info, setInfo] = useState<InfoData | null>(null);

  useEffect(() => {
    dispatchCommand("info.get")
      .then((result: any) => {
        if (result && typeof result === "object") {
          setInfo(result as InfoData);
        }
      })
      .catch(() => {});
  }, []);

  if (!info) {
    return (
      <div style={{ padding: 12, fontSize: 12, color: "var(--text-dim)" }}>
        Loading info...
      </div>
    );
  }

  return (
    <div
      style={{
        padding: 12,
        fontSize: 12,
        lineHeight: 1.8,
        overflow: "auto",
        height: "100%",
      }}
    >
      <div style={{ color: "var(--accent)", marginBottom: 8, fontSize: 14 }}>
        Nexus Shell v{info.system.version}
      </div>

      <Section title="Session">
        <Row label="Session" value={info.session || "none"} />
        <Row label="CWD" value={info.cwd || "not set"} />
        <Row label="PID" value={String(info.system.pid)} />
      </Section>

      <Section title="Layout">
        <Row label="Panes" value={String(info.layout.pane_count)} />
        <Row label="Focused" value={info.layout.focused} />
        <Row label="Zoomed" value={info.layout.zoomed || "none"} />
      </Section>

      <Section title="Display">
        <Row label="Gap" value={`${info.display.gap}px`} />
        <Row label="Background" value={info.display.background} />
        <Row label="Border Radius" value={`${info.display.border_radius}px`} />
        <Row label="Opacity" value={String(info.display.pane_opacity)} />
      </Section>

      <Section title="Backends">
        {info.backends?.entries?.map((b) => (
          <Row key={b.module} label={b.module} value={b.backend} />
        )) || <div style={{ color: "var(--text-dim)" }}>No backend info</div>}
      </Section>

      <Section title="Stacks">
        {info.stacks.map((s) => (
          <Row
            key={s.identity}
            label={s.identity}
            value={`${s.active_tab} (${s.tab_count} tabs)`}
          />
        ))}
        {info.stacks.length === 0 && (
          <div style={{ color: "var(--text-dim)" }}>No stacks</div>
        )}
      </Section>

      <Section title="Surfaces">
        {info.surfaces.map((s) => (
          <Row key={s.id} label={s.name} value={s.mode} />
        ))}
        {info.surfaces.length === 0 && (
          <div style={{ color: "var(--text-dim)" }}>No surfaces registered</div>
        )}
      </Section>

      <Section title="Keyboard">
        <Row label="Alt+P" value="Command palette" />
        <Row label="Ctrl+\" value="Command line" />
        <Row label="Alt+H/J/K/L" value="Navigate panes" />
        <Row label="Alt+V / Alt+S" value="Split H / V" />
        <Row label="Alt+F" value="Zoom toggle" />
        <Row label="Alt+W" value="Close pane" />
        <Row label="Alt+N" value="New tab (chooser)" />
        <Row label="Alt+O" value="Open menu" />
        <Row label="Alt+T" value="Tab list" />
        <Row label="Alt+G" value="Toggle gaps" />
        <Row label="Alt+B" value="Toggle transparency" />
      </Section>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <div
        style={{
          color: "var(--text-dim)",
          marginTop: 16,
          marginBottom: 4,
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          fontSize: 11,
        }}
      >
        {title}
      </div>
      {children}
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", gap: 8 }}>
      <span
        style={{
          color: "var(--text-bright)",
          minWidth: 120,
          fontFamily: "inherit",
        }}
      >
        {label}
      </span>
      <span style={{ color: "var(--text)" }}>{value}</span>
    </div>
  );
}
