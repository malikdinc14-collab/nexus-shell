// PaneRectContext — registry of bounding rects for layout leaf slots.
// SlotPlaceholder reports rects via ResizeObserver; PaneOverlayLayer reads
// them to absolutely-position pane components over their layout slots.

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
  /** The positioned container that overlay panes are children of. */
  containerRef: React.RefObject<HTMLDivElement | null>;
  setContainer: (el: HTMLDivElement | null) => void;
  reportRect: (paneId: string, rect: PaneRect) => void;
  removeRect: (paneId: string) => void;
}

const Ctx = createContext<PaneRectContextValue | null>(null);

export function PaneRectProvider({ children }: { children: React.ReactNode }) {
  const [rects, setRects] = useState<Map<string, PaneRect>>(new Map());
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Accumulate updates in a rAF batch — ensures browser layout is settled
  const pendingRef = useRef<Map<string, PaneRect | null>>(new Map());
  const rafRef = useRef(0);

  const flush = useCallback(() => {
    rafRef.current = 0;
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
    if (!rafRef.current) {
      rafRef.current = requestAnimationFrame(flush);
    }
  }, [flush]);

  const setContainer = useCallback((el: HTMLDivElement | null) => {
    containerRef.current = el;
  }, []);

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
    () => ({ rects, containerRef, setContainer, reportRect, removeRect }),
    [rects, setContainer, reportRect, removeRect],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePaneRects() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("usePaneRects must be inside PaneRectProvider");
  return ctx;
}
