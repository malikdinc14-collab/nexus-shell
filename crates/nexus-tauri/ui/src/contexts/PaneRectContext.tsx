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
  containerRef: React.RefObject<HTMLDivElement | null>;
  setContainer: (el: HTMLDivElement | null) => void;
  reportRect: (paneId: string, rect: PaneRect) => void;
  removeRect: (paneId: string) => void;
}

const Ctx = createContext<PaneRectContextValue | null>(null);

export function PaneRectProvider({ children }: { children: React.ReactNode }) {
  const [rects, setRects] = useState<Map<string, PaneRect>>(new Map());
  const containerRef = useRef<HTMLDivElement | null>(null);

  const setContainer = useCallback((el: HTMLDivElement | null) => {
    containerRef.current = el;
  }, []);

  // No manual batching — React 18 auto-batches within the same task/microtask.
  const reportRect = useCallback(
    (paneId: string, rect: PaneRect) => {
      setRects((prev) => {
        const next = new Map(prev);
        next.set(paneId, rect);
        return next;
      });
    },
    [],
  );

  const removeRect = useCallback(
    (paneId: string) => {
      setRects((prev) => {
        const next = new Map(prev);
        next.delete(paneId);
        return next;
      });
    },
    [],
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
