// useTabStack — syncs a pane's tab stack with the engine.
// Fetches stack state on mount, subscribes to stack-changed events,
// and provides dispatch wrappers for tab operations.

import { useState, useEffect, useCallback, useRef } from "react";
import { dispatchCommand, onStackChanged } from "../tauri";

export interface StackTab {
  index: number;
  name: string;
  pane_handle: string | null;
  is_active: boolean;
}

export interface TabStackState {
  tabs: StackTab[];
  activeIndex: number;
  switchTab: (index: number) => void;
  closeTab: () => void;
  prevTab: () => void;
  nextTab: () => void;
}

export default function useTabStack(paneId: string): TabStackState {
  const [tabs, setTabs] = useState<StackTab[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const paneIdRef = useRef(paneId);
  paneIdRef.current = paneId;

  // Fetch initial stack state
  useEffect(() => {
    dispatchCommand("stack.list", { identity: paneId })
      .then((result: any) => {
        if (result?.status === "ok" && Array.isArray(result.tabs)) {
          setTabs(result.tabs);
          const active = result.tabs.findIndex((t: any) => t.is_active);
          setActiveIndex(active >= 0 ? active : 0);
        }
      })
      .catch(() => {
        // No stack for this pane yet — that's fine
      });
  }, [paneId]);

  // Subscribe to stack-changed events
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    onStackChanged((data: any) => {
      // Only update if this event is for our pane
      if (data?.identity === paneIdRef.current || data?.stack_id === paneIdRef.current) {
        if (Array.isArray(data.tabs)) {
          setTabs(data.tabs);
          const active = data.tabs.findIndex((t: any) => t.is_active);
          setActiveIndex(active >= 0 ? active : 0);
        }
      }
    }).then((fn) => { unlisten = fn; });
    return () => { if (unlisten) unlisten(); };
  }, []);

  const switchTab = useCallback(
    (index: number) => {
      dispatchCommand("stack.switch", { identity: paneId, index: String(index) });
      setActiveIndex(index);
    },
    [paneId],
  );

  const closeTab = useCallback(() => {
    dispatchCommand("stack.close", { identity: paneId });
  }, [paneId]);

  const prevTab = useCallback(() => {
    dispatchCommand("stack.prev", { identity: paneId });
  }, [paneId]);

  const nextTab = useCallback(() => {
    dispatchCommand("stack.next", { identity: paneId });
  }, [paneId]);

  return { tabs, activeIndex, switchTab, closeTab, prevTab, nextTab };
}
