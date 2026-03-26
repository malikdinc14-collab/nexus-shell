// BrowserTauri — webview surface for Nexus Shell.
// Currently uses iframe as a placeholder for a more robust Tauri webview.
// State is managed by dispatchCommand("browser.*").

import { useState, useEffect, useCallback, useRef } from "react";
import { dispatchCommand } from "../tauri";
import { listen } from "@tauri-apps/api/event";

interface BrowserSession {
  pane_id: string;
  url: string;
  title: string;
}

interface Props {
  paneId: string;
  isFocused?: boolean;
}

export default function BrowserTauri({ paneId, isFocused }: Props) {
  const [session, setSession] = useState<BrowserSession | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const refreshSession = useCallback(async () => {
    try {
      const state = await dispatchCommand("browser.state");
      if (state && state[paneId]) {
        setSession(state[paneId]);
      }
    } catch (e) {
      console.warn("browser.state failed:", e);
    }
  }, [paneId]);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  // Listen for layout/stack changes that might involve a URL update
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    listen("layout-changed", () => {
      refreshSession();
    }).then((fn) => { unlisten = fn; });
    return () => { if (unlisten) unlisten(); };
  }, [refreshSession]);

  if (!session) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          color: "var(--text-dim)",
          gap: 8,
        }}
      >
        <div>No browser session</div>
        <div style={{ fontSize: 11 }}>
          Use <code>browser.open [url]</code>
        </div>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Navigation bar (optional, could be move to a shared header) */}
      <div 
        style={{ 
          height: 32, 
          background: "var(--bg-panel)", 
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          padding: "0 8px",
          gap: 8,
          fontSize: 12
        }}
      >
        <div style={{ color: "var(--text-dim)", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap", flex: 1 }}>
          {session.url}
        </div>
      </div>
      <iframe
        ref={iframeRef}
        src={session.url}
        style={{ 
          flex: 1, 
          border: "none",
          background: "white" 
        }}
        title={session.title}
        sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
      />
    </div>
  );
}
