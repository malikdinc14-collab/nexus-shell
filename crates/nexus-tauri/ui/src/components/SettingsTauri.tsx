// SettingsTauri — visual settings panel.
// Background color/transparency, pane opacity, gaps, border radius, themes.

import { useState, useEffect, useRef } from "react";
import { dispatchCommand } from "../tauri";

interface DisplaySettings {
  gap: number;
  background: string;
  border_radius: number;
  pane_opacity: number;
  show_status_bar: boolean;
  show_decorations: boolean;
}

interface Theme {
  id: string;
  label: string;
  vars: Record<string, string>;
}

const THEMES: Theme[] = [
  {
    id: "tokyonight",
    label: "Tokyo Night",
    vars: {
      "--bg": "#1a1b26",
      "--bg-panel": "#16161e",
      "--border": "#2f3549",
      "--text": "#a9b1d6",
      "--text-bright": "#c0caf5",
      "--text-dim": "#565f89",
      "--accent": "#7aa2f7",
    },
  },
  {
    id: "catppuccin",
    label: "Catppuccin Mocha",
    vars: {
      "--bg": "#1e1e2e",
      "--bg-panel": "#181825",
      "--border": "#313244",
      "--text": "#cdd6f4",
      "--text-bright": "#cdd6f4",
      "--text-dim": "#6c7086",
      "--accent": "#cba6f7",
    },
  },
  {
    id: "gruvbox",
    label: "Gruvbox Dark",
    vars: {
      "--bg": "#282828",
      "--bg-panel": "#1d2021",
      "--border": "#3c3836",
      "--text": "#ebdbb2",
      "--text-bright": "#fbf1c7",
      "--text-dim": "#928374",
      "--accent": "#d79921",
    },
  },
  {
    id: "onedark",
    label: "One Dark",
    vars: {
      "--bg": "#282c34",
      "--bg-panel": "#21252b",
      "--border": "#3e4452",
      "--text": "#abb2bf",
      "--text-bright": "#e5c07b",
      "--text-dim": "#5c6370",
      "--accent": "#61afef",
    },
  },
  {
    id: "nord",
    label: "Nord",
    vars: {
      "--bg": "#2e3440",
      "--bg-panel": "#272c36",
      "--border": "#3b4252",
      "--text": "#d8dee9",
      "--text-bright": "#eceff4",
      "--text-dim": "#4c566a",
      "--accent": "#88c0d0",
    },
  },
  {
    id: "solarized",
    label: "Solarized Dark",
    vars: {
      "--bg": "#002b36",
      "--bg-panel": "#073642",
      "--border": "#0d3c48",
      "--text": "#839496",
      "--text-bright": "#eee8d5",
      "--text-dim": "#586e75",
      "--accent": "#268bd2",
    },
  },
];

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  for (const [key, val] of Object.entries(theme.vars)) {
    root.style.setProperty(key, val);
  }
}

function getCurrentThemeId(): string {
  return document.documentElement.dataset.themeId || "tokyonight";
}

interface Props {
  paneId?: string;
  isFocused?: boolean;
}

export default function SettingsTauri({ isFocused }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [display, setDisplay] = useState<DisplaySettings | null>(null);
  const [themeId, setThemeId] = useState(getCurrentThemeId());

  useEffect(() => {
    if (isFocused && containerRef.current) {
      containerRef.current.focus();
    }
  }, [isFocused]);

  useEffect(() => {
    dispatchCommand("display.get")
      .then((r: any) => { if (r) setDisplay(r as DisplaySettings); })
      .catch(() => {});
  }, []);

  const set = async (key: string, value: string) => {
    const r: any = await dispatchCommand("display.set", { key, value }).catch(() => null);
    if (r) setDisplay(r as DisplaySettings);
  };

  const selectTheme = (theme: Theme) => {
    applyTheme(theme);
    document.documentElement.dataset.themeId = theme.id;
    setThemeId(theme.id);
  };

  if (!display) {
    return <div style={{ padding: 16, fontSize: 12, color: "var(--text-dim)" }}>Loading...</div>;
  }

  return (
    <div ref={containerRef} tabIndex={0} style={{
      padding: 20,
      fontSize: 12,
      color: "var(--text)",
      height: "100%",
      overflow: "auto",
      display: "flex",
      flexDirection: "column",
      gap: 24,
      outline: "none",
    }}>

      {/* Themes */}
      <Section title="Theme">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {THEMES.map((t) => (
            <button
              key={t.id}
              onClick={() => selectTheme(t)}
              style={{
                padding: "6px 12px",
                borderRadius: 6,
                border: `1px solid ${themeId === t.id ? "var(--accent)" : "var(--border)"}`,
                background: themeId === t.id ? "var(--accent-dim)" : "var(--bg-panel)",
                color: themeId === t.id ? "var(--accent)" : "var(--text)",
                cursor: "pointer",
                fontFamily: "inherit",
                fontSize: 11,
                transition: "all 0.15s",
              }}
            >
              <span style={{ marginRight: 6 }}>
                <ThemeSwatch theme={t} />
              </span>
              {t.label}
            </button>
          ))}
        </div>
      </Section>

      {/* Background */}
      <Section title="Background">
        <Row label="Transparent">
          <Toggle
            value={display.background === "transparent"}
            onChange={(v) => set("background", v ? "transparent" : "var(--bg)")}
          />
        </Row>
        {display.background !== "transparent" && (
          <Row label="Color">
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="color"
                value={cssVarToHex(display.background)}
                onChange={(e) => set("background", e.target.value)}
                style={{ width: 32, height: 24, border: "none", background: "none", cursor: "pointer" }}
              />
              <span style={{ color: "var(--text-dim)", fontFamily: "monospace" }}>
                {display.background}
              </span>
            </div>
          </Row>
        )}
      </Section>

      {/* Window */}
      <Section title="Window">
        <Row label="Title bar">
          <Toggle
            value={display.show_decorations !== false}
            onChange={(v) => set("show_decorations", String(v))}
          />
        </Row>
        <Row label="Status bar">
          <Toggle
            value={display.show_status_bar !== false}
            onChange={(v) => set("show_status_bar", String(v))}
          />
        </Row>
      </Section>

      {/* Panes */}
      <Section title="Panes">
        <Row label={`Opacity  ${Math.round(display.pane_opacity * 100)}%`}>
          <Slider
            min={0.2} max={1} step={0.05}
            value={display.pane_opacity}
            onChange={(v) => set("opacity", String(v))}
          />
        </Row>
        <Row label={`Gap  ${display.gap}px`}>
          <Slider
            min={0} max={24} step={2}
            value={display.gap}
            onChange={(v) => set("gap", String(v))}
          />
        </Row>
        <Row label={`Border radius  ${display.border_radius}px`}>
          <Slider
            min={0} max={16} step={1}
            value={display.border_radius}
            onChange={(v) => set("border_radius", String(v))}
          />
        </Row>
      </Section>

    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{
        fontSize: 10,
        color: "var(--text-dim)",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        marginBottom: 10,
      }}>
        {title}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {children}
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <span style={{ color: "var(--text-dim)", minWidth: 140 }}>{label}</span>
      {children}
    </div>
  );
}

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!value)}
      style={{
        width: 36,
        height: 20,
        borderRadius: 10,
        border: "none",
        background: value ? "var(--accent)" : "var(--border)",
        cursor: "pointer",
        position: "relative",
        transition: "background 0.2s",
        flexShrink: 0,
      }}
    >
      <div style={{
        position: "absolute",
        top: 2,
        left: value ? 18 : 2,
        width: 16,
        height: 16,
        borderRadius: "50%",
        background: "white",
        transition: "left 0.2s",
      }} />
    </button>
  );
}

function Slider({ min, max, step, value, onChange }: {
  min: number; max: number; step: number;
  value: number; onChange: (v: number) => void;
}) {
  return (
    <input
      type="range"
      min={min} max={max} step={step}
      value={value}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      style={{ flex: 1, accentColor: "var(--accent)", cursor: "pointer" }}
    />
  );
}

function ThemeSwatch({ theme }: { theme: Theme }) {
  return (
    <span style={{ display: "inline-flex", gap: 2, verticalAlign: "middle" }}>
      {[theme.vars["--bg"], theme.vars["--accent"], theme.vars["--text-bright"]].map((c, i) => (
        <span key={i} style={{ width: 8, height: 8, borderRadius: "50%", background: c, display: "inline-block" }} />
      ))}
    </span>
  );
}

function cssVarToHex(val: string): string {
  if (val.startsWith("#")) return val;
  // For CSS vars, return a neutral fallback for the color picker
  return "#1a1b26";
}
