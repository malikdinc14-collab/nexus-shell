// PaneOverlayLayer — renders all pane instances in a fixed container,
// absolutely positioned over their layout slots. Pane DOM nodes never
// move on swap/rearrange; only CSS coordinates change.

import React from "react";
import { usePaneRects } from "../contexts/PaneRectContext";
import type { LayoutNode, DisplaySettings } from "../tauri";

interface Props {
  leafNodes: Map<string, LayoutNode>;
  focused: string;
  zoomed: string | null;
  onFocus: (id: string) => void;
  cwd: string;
  session: string | null;
  display: DisplaySettings;
  dragState: { sourcePaneId: string; active: boolean } | null;
  onDragStart: (paneId: string, e: React.MouseEvent) => void;
  onDropTargetChange: (target: { paneId: string; zone: "center" | "left" | "right" | "top" | "bottom" } | null) => void;
  renderPane: (paneId: string, node: LayoutNode, focused: boolean, rect: { width: number; height: number }) => React.ReactNode;
}

export default function PaneOverlayLayer({
  leafNodes,
  focused,
  zoomed,
  renderPane,
}: Props) {
  const { rects } = usePaneRects();

  return (
    <>
      {Array.from(leafNodes.entries()).map(([paneId, node]) => {
        const rect = rects.get(paneId);
        // Hide panes that don't have a measured slot yet, or are not the zoomed pane
        const isVisible = zoomed ? paneId === zoomed : !!rect;
        const style: React.CSSProperties = rect && isVisible
          ? {
              position: "absolute",
              top: rect.top,
              left: rect.left,
              width: rect.width,
              height: rect.height,
              overflow: "hidden",
              // no transition — instant repositioning for now
            }
          : {
              position: "absolute",
              top: 0,
              left: 0,
              width: 0,
              height: 0,
              overflow: "hidden",
              visibility: "hidden",
              pointerEvents: "none",
            };

        return (
          <div key={paneId} style={style}>
            {renderPane(paneId, node, paneId === focused, {
              width: rect?.width ?? 0,
              height: rect?.height ?? 0,
            })}
          </div>
        );
      })}
    </>
  );
}
