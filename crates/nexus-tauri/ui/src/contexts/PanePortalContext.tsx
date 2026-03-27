// PanePortalContext — manages persistent host <div>s for each pane.
// Host elements are created once per pane and never destroyed until pane closes.
// SlotPlaceholder moves them via appendChild; React portals render into them.

import { createContext, useContext, useRef, useCallback } from "react";
import type React from "react";

interface PanePortalContextValue {
  /** Get (or lazily create) the persistent host element for a pane. */
  getHost: (paneId: string) => HTMLDivElement;
  /** Remove a host element when a pane is closed. */
  removeHost: (paneId: string) => void;
}

const Ctx = createContext<PanePortalContextValue | null>(null);

export function PanePortalProvider({ children }: { children: React.ReactNode }) {
  const hostsRef = useRef(new Map<string, HTMLDivElement>());

  const getHost = useCallback((paneId: string) => {
    let host = hostsRef.current.get(paneId);
    if (!host) {
      host = document.createElement("div");
      host.style.display = "flex";
      host.style.flex = "1";
      host.style.overflow = "hidden";
      host.style.width = "100%";
      host.style.height = "100%";
      host.dataset.paneHost = paneId;
      hostsRef.current.set(paneId, host);
    }
    return host;
  }, []);

  const removeHost = useCallback((paneId: string) => {
    const host = hostsRef.current.get(paneId);
    if (host) {
      host.remove();
      hostsRef.current.delete(paneId);
    }
  }, []);

  return <Ctx.Provider value={{ getHost, removeHost }}>{children}</Ctx.Provider>;
}

export function usePanePortals() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("usePanePortals must be inside PanePortalProvider");
  return ctx;
}
