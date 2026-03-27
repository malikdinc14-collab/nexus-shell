// PaneRectContext — registry of bounding rects for layout leaf slots.
// NodeRenderer reports rects via ResizeObserver; PaneOverlayLayer reads them
// to absolutely-position pane components over their layout slots.

import { createContext, useContext, useRef, useState, useCallback, useMemo } from "react";
import type React from "react";

interface PaneRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

interface PaneRectContextValue {
  rects: Map<string, PaneRect>;
  reportRect: (paneId: string, rect: PaneRect) => void;
  removeRect: (paneId: string) => void;
}

const Ctx = createContext<PaneRectContextValue | null>(null);

export function PaneRectProvider({ children }: { children: React.ReactNode }) {
  const [rects, setRects] = useState<Map<string, PaneRect>>(new Map());
  // Accumulate updates in a microtask batch to avoid per-slot re-renders
  const pendingRef = useRef<Map<string, PaneRect | null>>(new Map());
  const scheduledRef = useRef(false);

  const flush = useCallback(() => {
    scheduledRef.current = false;
    const pending = pendingRef.current;
    if (pending.size === 0) return;
    setRects((prev) => {
      const next = new Map(prev);
      for (const [id, rect] of pending) {
        if (rect === null) {
          next.delete(id);
        } else {
          next.set(id, rect);
        }
      }
      pending.clear();
      return next;
    });
  }, []);

  const schedule = useCallback(() => {
    if (!scheduledRef.current) {
      scheduledRef.current = true;
      queueMicrotask(flush);
    }
  }, [flush]);

  const reportRect = useCallback(
    (paneId: string, rect: PaneRect) => {
      pendingRef.current.set(paneId, rect);
      schedule();
    },
    [schedule],
  );

  const removeRect = useCallback(
    (paneId: string) => {
      pendingRef.current.set(paneId, null);
      schedule();
    },
    [schedule],
  );

  const value = useMemo(
    () => ({ rects, reportRect, removeRect }),
    [rects, reportRect, removeRect],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePaneRects() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("usePaneRects must be inside PaneRectProvider");
  return ctx;
}
