#!/usr/bin/env python3
"""
Dock Actions
============
Collapse/expand panes while preserving proportional sizing.
All multiplexer operations go through the adapter layer.
"""

import sys
from pathlib import Path

_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

from engine.actions.resolver import AdapterResolver


def toggle(handle: str = "") -> None:
    """Toggle dock state (minimize/restore) of a pane."""
    mux = AdapterResolver.multiplexer()
    pane_id = handle or mux.get_focused_pane_id()
    if not pane_id:
        print("[INVARIANT] No focused pane for dock toggle.", file=sys.stderr)
        return

    is_min = mux.get_tag(pane_id, "nexus_minimized")

    if is_min == "1":
        # RESTORE
        prev_val = mux.get_tag(pane_id, "nexus_pre_min_val")
        dim = mux.get_tag(pane_id, "nexus_min_dim")

        if dim == "zoom":
            mux._run(["resize-pane", "-t", pane_id, "-Z"])
        elif prev_val and prev_val != "null":
            mux._run(["resize-pane", "-t", pane_id, f"-{dim}", prev_val])

        mux.set_tag(pane_id, "@nexus_minimized", "0")
    else:
        # MINIMIZE — detect orientation
        dims = mux.get_dimensions(pane_id)
        cur_w = dims.get("width", 80)
        cur_h = dims.get("height", 24)

        # Use pane-specific dimensions (not window)
        raw = mux._run(["display-message", "-t", pane_id, "-p",
                        "#{pane_width},#{pane_height}"])
        if raw:
            try:
                cur_w, cur_h = (int(x) for x in raw.split(","))
            except ValueError:
                pass

        if cur_h > cur_w:
            # Vertical sidebar → collapse to strip, restore via zoom
            mux.set_tag(pane_id, "@nexus_pre_min_val", str(cur_w))
            mux.set_tag(pane_id, "@nexus_min_dim", "zoom")
            mux.set_tag(pane_id, "@nexus_minimized", "1")
            target_size = 3
            if cur_w <= target_size:
                return
            mux._run(["resize-pane", "-t", pane_id, "-x", str(target_size)])
        else:
            # Horizontal bar → collapse vertically
            target_size = 2
            if cur_h <= target_size:
                return
            mux.set_tag(pane_id, "@nexus_pre_min_val", str(cur_h))
            mux.set_tag(pane_id, "@nexus_min_dim", "y")
            mux.set_tag(pane_id, "@nexus_minimized", "1")
            mux._run(["resize-pane", "-t", pane_id, "-y", str(target_size)])


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "toggle"
    handle = sys.argv[2] if len(sys.argv) > 2 else ""
    if action == "toggle":
        toggle(handle)
    else:
        print(f"Usage: dock.py toggle [handle]", file=sys.stderr)
        sys.exit(1)
