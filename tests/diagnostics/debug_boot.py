#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

# Axiom: Alignment first.
# This script runs the SAME logic as the Daemon's 'boot_layout' action.

NEXUS_HOME = Path("/Users/Shared/Projects/nexus-shell")
sys.path.append(str(NEXUS_HOME))
sys.path.append(str(NEXUS_HOME / "core"))

from engine.orchestration.workspace import WorkspaceOrchestrator

def debug_boot():
    print("[*] Diagnostic: Nexus Boot Orchestration")
    
    # 1. Resolve Environment
    project_root = Path(os.getcwd())
    socket_label = os.environ.get("SOCKET_LABEL")
    session_id = os.environ.get("SESSION_ID")
    composition = os.environ.get("COMPOSITION", "vscodelike")
    
    print(f"    - NEXUS_HOME: {NEXUS_HOME}")
    print(f"    - PROJECT_ROOT: {project_root}")
    print(f"    - SOCKET_LABEL: {socket_label}")
    print(f"    - SESSION_ID: {session_id}")
    print(f"    - COMPOSITION: {composition}")

    if not socket_label or not session_id:
        print("[!] ERROR: SOCKET_LABEL or SESSION_ID not set in environment.")
        print("    Try running this inside a 'nxs boot' flow or with manual env vars.")
        return

    # 2. Instantiate Orchestrator
    try:
        orch = WorkspaceOrchestrator(NEXUS_HOME, project_root, socket_label)
        print("[+] Orchestrator instantiated.")
    except Exception as e:
        print(f"[!] FAILED to instantiate Orchestrator: {e}")
        return

    # 3. Resolve Composition
    p = NEXUS_HOME / f"core/ui/compositions/{composition}.json"
    print(f"    - Checking composition at: {p}")
    if not p.exists():
        print(f"[!] ERROR: Composition file does not exist.")
        return
    print("[+] Composition file found.")

    # 4. Trigger Build
    target_window = f"{session_id}:0"
    print(f"[*] Triggering apply_composition for {target_window}...")
    try:
        orch.apply_composition(composition, target_window)
        print("[+] Orchestration cycle complete.")
    except Exception as e:
        print(f"[!] CRITICAL ERROR during orchestration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_boot()
