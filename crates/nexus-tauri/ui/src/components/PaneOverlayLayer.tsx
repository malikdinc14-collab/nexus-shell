// PanePortalLayer — renders pane components into persistent host elements
// via React portals. Host elements live inside layout slots (moved there by
// SlotPlaceholder via appendChild). Pane DOM nodes never unmount on swap —
// only the host element moves between slots.

import React from "react";
import { createPortal } from "react-dom";
import { usePanePortals } from "../contexts/PanePortalContext";
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
  renderPane: (paneId: string, node: LayoutNode, focused: boolean) => React.ReactNode;
}

export default function PaneOverlayLayer({
  leafNodes,
  focused,
  zoomed,
  renderPane,
}: Props) {
  const { getHost } = usePanePortals();

  return (
    <>
      {Array.from(leafNodes.entries()).map(([paneId, node]) => {
        // When zoomed, only render the zoomed pane
        if (zoomed && paneId !== zoomed) return null;

        const host = getHost(paneId);
        return createPortal(
          renderPane(paneId, node, paneId === focused),
          host,
          paneId, // stable key for the portal
        );
      })}
    </>
  );
}
