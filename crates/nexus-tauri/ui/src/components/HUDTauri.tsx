// HUDTauri — Generic telemetry display for Nexus Shell.
// Visualizes frames from HUDCapability adapters.

import { useState, useEffect, useRef } from "react";
import { dispatchCommand } from "../tauri";

interface HUDPart {
  id: string;
  part_type: string;
  label: string;
  value: any;
  metadata: Record<string, string>;
}

interface HUDFrame {
  source: string;
  parts: HUDPart[];
  timestamp: string;
}

interface Props {
  paneId?: string;
  isFocused?: boolean;
}

export default function HUDTauri({ isFocused }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [frames, setFrames] = useState<HUDFrame[]>([]);

  useEffect(() => {
    if (isFocused && containerRef.current) {
      containerRef.current.focus();
    }
  }, [isFocused]);

  useEffect(() => {
    const interval = setInterval(async () => {
        try {
            const result = await dispatchCommand("hud.frames", {});
            if (Array.isArray(result)) {
                setFrames(result as HUDFrame[]);
            }
        } catch (e) {
            console.warn("hud.list failed:", e);
        }
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const renderPart = (part: HUDPart) => {
    switch (part.part_type) {
        case "Gauge":
            const val = parseFloat(part.value);
            return (
                <div key={part.id} style={{
                    padding: 16, borderRadius: 12, background: "var(--hover)",
                    display: "flex", flexDirection: "column", gap: 8, minWidth: 140
                }}>
                    <div style={{ fontSize: 10, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                        {part.label}
                    </div>
                    <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                        <span style={{ fontSize: 24, fontWeight: 700, color: "var(--accent)" }}>{val.toFixed(1)}</span>
                        <span style={{ fontSize: 12, color: "var(--text-dim)" }}>{part.metadata.unit}</span>
                    </div>
                    <div style={{ height: 4, width: "100%", background: "rgba(255,255,255,0.05)", borderRadius: 2, overflow: "hidden" }}>
                        <div style={{ height: "100%", width: `${val}%`, background: "var(--accent)", transition: "width 0.3s ease" }} />
                    </div>
                </div>
            );
        default:
            return (
                <div key={part.id} style={{ padding: 16, borderRadius: 12, background: "var(--hover)" }}>
                    <div style={{ fontSize: 10, color: "var(--text-dim)" }}>{part.label}</div>
                    <div style={{ fontSize: 18 }}>{JSON.stringify(part.value)}</div>
                </div>
            );
    }
  };

  return (
    <div ref={containerRef} tabIndex={0} style={{
        display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)",
        color: "var(--text)", fontFamily: "'Inter', sans-serif", padding: 24, overflow: "auto",
        outline: "none"
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
          <span style={{ fontSize: 18 }}>📊</span>
          <h1 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>System HUD</h1>
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: 10, color: "var(--text-dim)" }}>REAL-TIME TELEMETRY</span>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 16 }}>
          {frames.map(frame => (
              <div key={frame.source} style={{ display: "contents" }}>
                  {frame.parts.map(part => renderPart(part))}
              </div>
          ))}
      </div>

      {frames.length === 0 && (
          <div style={{ opacity: 0.3, textAlign: "center", marginTop: 40 }}>
              No telemetry streams active
          </div>
      )}
    </div>
  );
}
