#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(PROJECT_ROOT / "core"))
sys.path.append(str(PROJECT_ROOT / "core/engine"))

from engine.lib.daemon_client import NexusDaemonClient

def run_tmux(args, socket_label=None):
    sl = socket_label or os.environ.get("SOCKET_LABEL")
    cmd = ["tmux"]
    if sl:
        if sl.startswith("/"): cmd += ["-S", sl]
        else: cmd += ["-L", sl]
    cmd += args
    try:
        res = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
        return res.strip()
    except:
        return None

def main():
    print("--- NEXUS LIVE SYSTEM AUDIT ---")
    client = NexusDaemonClient()
    
    # 1. Semantic State (Nexus Registry)
    state = client.get_state()
    if state.get("status") != "ok":
        print(f"[!] Error fetching Daemon state: {state.get('message')}")
        return
        
    stacks = state.get("data", {}).get("stacks", {})
    print(f"[*] Registry: {len(stacks)} stacks tracked.")

    # 2. Physical State (Tmux Windows & Panes)
    current_session = run_tmux(["display-message", "-p", "#S"])
    if not current_session:
        print("[!] No active tmux session detected.")
        return
    
    # Snapshot all panes in current session
    fmt = "#{window_id}|#{window_name}|#{window_width}x#{window_height}|#{pane_index}|#{pane_id}|#{pane_width}x#{pane_height}|#{@nexus_stack_id}|#{@nexus_role}|#{pane_current_command}"
    raw_panes = run_tmux(["list-panes", "-s", "-F", fmt])
    if not raw_panes:
        print("[!] Failed to list panes.")
        return

    windows = {}
    for line in raw_panes.splitlines():
        parts = line.split("|")
        if len(parts) < 9: continue
        wid, wname, wgeo, pidx, pid, pgeo, sid, role, pcmd = parts
        
        if wid not in windows:
            windows[wid] = {"name": wname, "geo": wgeo, "panes": []}
            
        windows[wid]["panes"].append({
            "idx": pidx, "id": pid, "geo": pgeo, 
            "sid": sid if sid and sid != "null" else None,
            "role": role if role and role != "null" else None,
            "cmd": pcmd
        })

    # 3. Tree View Output
    print(f"\n[*] PHYSICAL VIEW: Session '{current_session}'")
    for wid, w in windows.items():
        print(f" ┣━ Workspace: [{w['name']}] ({w['geo']})")
        for p in w["panes"]:
            ident = p["sid"] or p["role"] or "UNIDENTIFIED"
            status = "OK" if p["sid"] else "ORPHAN"
            # Show window-relative path: win_name.index
            print(f" ┃   ┗━ Pane .{p['idx']} (ID: {p['id']}) ({p['geo']:8}) -> Identity: {ident:15} [CMD: {p['cmd']}] ({status})")

    # 4. Semantic Drift (Registry vs Physical)
    print("\n[*] SEMANTIC DRIFT (Nexus Registry vs Reality)")
    expected_ids = list(stacks.keys())
    phys_ids = [p["sid"] for w in windows.values() for p in w["panes"] if p["sid"]]
    phys_roles = [p["role"] for w in windows.values() for p in w["panes"] if p["role"]]
    
    for eid in expected_ids:
        if eid in phys_ids or eid in phys_roles:
            print(f" [OK] {eid:15} -> Verified. Physically active.")
        else:
            print(f" [!!] {eid:15} -> ZOMBIE. Registered in Daemon but MISSING PHYSICALLY.")

    print("\n--- END OF AUDIT ---")

if __name__ == "__main__":
    main()
