#!/usr/bin/env python3
import json
import sys
import os
import subprocess

def load_registry():
    nexus_home = os.getenv("NEXUS_HOME", os.path.expanduser("~/.config/nexus-shell"))
    registry_path = os.path.join(nexus_home, "core/engine/api/registry.json")
    try:
        with open(registry_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading registry: {e}", file=sys.stderr)
        sys.exit(1)

def check_dirty():
    """Check if nvim has unsaved changes. Returns False if nvim isn't running."""
    try:
        nexus_state = os.getenv("NEXUS_STATE", f"/tmp/nexus_{os.getlogin()}")
        session_name = subprocess.check_output(
            ["tmux", "display-message", "-p", "#S"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        project_name = session_name.replace("nexus_", "")
        pipe = os.path.join(nexus_state, f"pipes/nvim_{project_name}.pipe")
        
        if not os.path.exists(pipe):
            return False  # No nvim running, safe to quit
            
        res = subprocess.check_output(
            ["nvim", "--server", pipe, "--remote-expr", "v:lua.is_dirty()"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip()
        return res == "true"
    except Exception:
        return False  # Any failure = assume safe to quit

def save_all():
    """Best-effort save of all nvim buffers. Must never crash."""
    try:
        nexus_state = os.getenv("NEXUS_STATE", f"/tmp/nexus_{os.getlogin()}")
        session_name = subprocess.check_output(
            ["tmux", "display-message", "-p", "#S"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        project_name = session_name.replace("nexus_", "")
        pipe = os.path.join(nexus_state, f"pipes/nvim_{project_name}.pipe")
        
        if os.path.exists(pipe):
            # Send write all command
            subprocess.run(
                ["nvim", "--server", pipe, "--remote-send", ":wa<CR>"],
                stderr=subprocess.DEVNULL, timeout=2
            )
            # Give nvim a moment to flush to disk before session is torn down
            import time
            time.sleep(0.3)
    except Exception:
        pass  # Never block exit

def show_help(registry):
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                  NEXUS-SHELL COMMANDS                    ║")
    print("╠══════════════════════════════════════════════════════════╣")
    
    categories = {}
    for cmd in registry["commands"]:
        cat = cmd.get("category", "General")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(cmd)
        
    for cat in sorted(categories.keys()):
        print(f"║  {cat.upper():<56}║")
        for cmd in categories[cat]:
            name = cmd["names"][-1] # Primary name (usually the :cmd)
            desc = cmd.get("description", "")
            print(f"║    {name:<8} - {desc:<45}║")
        print("║                                                          ║")
        
    print("║  Press Enter to close                                    ║")
    print("╚══════════════════════════════════════════════════════════╝")

def main():
    if len(sys.argv) < 2:
        sys.exit(0)
        
    if sys.argv[1] == "--help-only":
        registry = load_registry()
        show_help(registry)
        sys.exit(0)
        
    query = sys.argv[1]
    args = sys.argv[2:]
    registry = load_registry()
    
    matched_cmd = None
    for cmd in registry["commands"]:
        if query in cmd["names"]:
            matched_cmd = cmd
            break
            
    if not matched_cmd:
        # Fallback to agent query handled by dispatch.sh
        sys.exit(127)
        
    # Handle Preflight
    preflight = matched_cmd.get("preflight")
    if preflight == "check_dirty":
        if check_dirty():
            subprocess.run(["tmux", "display-message", "Unsaved changes! Use :wq to save or :q! to force quit"])
            sys.exit(2)
    elif preflight == "save_all":
        save_all()
        
    # Handle Action
    action = matched_cmd["action"]
    
    if action == "internal:help":
        # We handle help via a popup in dispatch.sh for better UX, 
        # but the registry stores the metadata.
        sys.exit(100) # Magic exit code for help
        
    # Execute shell action
    # Expand environment variables in action
    expanded_action = os.path.expandvars(action)
    if matched_cmd.get("args") and args:
        expanded_action += " " + " ".join(args)
        
    res = subprocess.run(expanded_action, shell=True)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
