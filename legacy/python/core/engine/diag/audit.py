#!/usr/bin/env python3
# core/engine/diag/audit.py
"""
Nexus Live System Auditor (V2)
==============================
Uses the TmuxAdapter (MultiplexerCapability) to query physical state,
giving us a backend-agnostic audit that works with any adapter.
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "core"))

from engine.lib.daemon_client import NexusDaemonClient
from engine.capabilities.adapters.tmux import TmuxAdapter


def main():
    print("--- NEXUS LIVE SYSTEM AUDIT ---")

    # 1. Semantic State (Nexus Daemon Registry)
    client = NexusDaemonClient()
    state = client.get_state()
    if state.get("status") != "ok":
        print(f"[!] Error fetching Daemon state: {state.get('message')}")
        return

    stacks = state.get("data", {}).get("stacks", {})
    print(f"[*] Registry: {len(stacks)} stacks tracked.")

    # 2. Physical State via TmuxAdapter (backend-agnostic)
    socket_label = os.environ.get("SOCKET_LABEL", "")
    mux = TmuxAdapter(socket_label=socket_label)

    current_session_raw = mux._run(["display-message", "-p", "#S"])
    if not current_session_raw:
        print("[!] No active tmux session detected.")
        return
    current_session = current_session_raw.strip()

    print(f"\n[*] PHYSICAL VIEW: Session '{current_session}'")

    # Get all windows in the session
    windows = mux.list_windows(current_session)

    for win_handle in windows:
        # Get window display name
        win_name = mux._run(["display-message", "-t", win_handle, "-p", "#{window_name}"])
        win_dims = mux.get_dimensions(win_handle)
        geo_str = f"{win_dims['width']}x{win_dims['height']}"

        print(f" ┣━ Workspace: [{win_name}] ({geo_str})")

        # list_panes returns List[PaneInfo]
        panes = mux.list_panes(win_handle)
        if not panes:
            print(" ┃   (no panes)")
            continue

        for p in panes:
            ident = p.stack_id or p.role or "UNIDENTIFIED"
            status = "OK" if p.stack_id else "ORPHAN"
            geo = f"{p.width}x{p.height}"
            print(
                f" ┃   ┗━ Pane .{p.index} (ID: {p.handle}) "
                f"({geo:8}) -> Identity: {ident:15} "
                f"[CMD: {p.command}] ({status})"
            )

    # 3. Semantic Drift (Registry vs Physical)
    print("\n[*] SEMANTIC DRIFT (Nexus Registry vs Reality)")

    all_panes = [
        p for win in windows
        for p in mux.list_panes(win)
    ]
    phys_ids = {p.stack_id for p in all_panes if p.stack_id}
    phys_roles = {p.role for p in all_panes if p.role}

    for eid in stacks.keys():
        if eid in phys_ids or eid in phys_roles:
            print(f" [OK] {eid:15} -> Verified. Physically active.")
        else:
            print(f" [!!] {eid:15} -> ZOMBIE. Registered in Daemon but MISSING PHYSICALLY.")

    print("\n--- END OF AUDIT ---")


if __name__ == "__main__":
    main()
