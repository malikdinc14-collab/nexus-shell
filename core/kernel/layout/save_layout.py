#!/usr/bin/env python3
"""
save_layout.py (Momentum Edition) — "Freezes the Moment"
Captures the hierarchical structure, proportional geometry, and process state
of a tmux session to allow adaptive restoration.
"""

import sys
import subprocess
import json
import os
import re
from pathlib import Path

def run_tmux(args):
    cmd = ["tmux"]
    sl = os.environ.get("SOCKET_LABEL")
    if sl:
        cmd += ["-L", sl]
    try:
        return subprocess.check_output(cmd + args, stderr=subprocess.DEVNULL).decode().strip()
    except Exception as e:
        print(f"Tmux Error: {args} -> {e}", file=sys.stderr)
        return ""

# Add core/engine/state to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent / "engine" / "state"))
try:
    from state_engine import NexusStateEngine
except ImportError:
    print("FATAL: Invariant Violated. NexusStateEngine not found in core/engine/state", file=sys.stderr)
    sys.exit(102)

if NexusStateEngine is None:
    print("FATAL: Invariant Violated. NexusStateEngine is None after import.", file=sys.stderr)
    sys.exit(103)

def get_leaf_process(pid):
    """Recursively find the deepest child process to identify the running tool."""
    try:
        children = subprocess.check_output(
            ["pgrep", "-P", str(pid)],
            stderr=subprocess.DEVNULL
        ).decode().strip().split("\n")

        if children and children[0]:
            return get_leaf_process(children[0])
    except Exception:
        pass
    return pid

def get_pane_command(pid):
    """Detect the foreground process in a pane."""
    try:
        leaf_pid = get_leaf_process(pid)
        cmd = subprocess.check_output(
            ["ps", "-p", str(leaf_pid), "-o", "command="],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        if not cmd:
            return "/bin/zsh -i"

        # Triage known tools to save logical variables
        # This keeps the IDE "Stateful" across different setups
        if any(x in cmd for x in ["fzf", "nexus-menu", "px-engine"]):
            return "$PARALLAX_CMD"
        if "nvim" in cmd or "vim" in cmd:
            return "$EDITOR_CMD"
        if any(x in cmd for x in ["yazi", "ranger", "lf"]):
            return "$NEXUS_FILES"
        
        # If it's a generic shell, just return zsh

        # Fallback: Capture the full command line to preserve arguments/state
        if cmd.strip().split()[0].split("/")[-1] in ["zsh", "bash", "sh"]:
            return "/bin/zsh -i"
            
        return cmd.replace("\n", " ").strip()
    except Exception:
        return "/bin/zsh -i"

def capture_moment(session_id, window_idx):
    """Freezes the current window state: structure + process map."""
    try:
        # 1. Get total window dimensions (for proportional math)
        win_info = run_tmux(["list-windows", "-t", session_id, "-F", "#{window_index}|#{window_width}|#{window_height}|#{window_layout}"]).split("\n")

        target_line = None
        for line in win_info:
            if line.startswith(f"{window_idx}|"):
                target_line = line
                break
        
        if not target_line: return None
        
        _, win_w, win_h, layout_str = target_line.split("|")
        win_w, win_h = int(win_w), int(win_h)

        # 2. Get detailed pane metadata in order
        fmt = "#{pane_index}|#{pane_title}|#{pane_pid}|#{pane_width}|#{pane_height}|#{pane_left}|#{pane_top}|#{@nexus_stack_id}|#{@nexus_role}|#{pane_current_path}"
        pane_info = run_tmux(["list-panes", "-t", f"{session_id}:{window_idx}", "-F", fmt]).split("\n")

        panes = []
        win_root = None
        for i, line in enumerate(pane_info):
            if not line.strip(): continue
            parts = line.split("|")
            if len(parts) < 10: continue
            idx, title, pid, w, h, l, t, sid, role, cwd = parts
            
            # Use the first pane's CWD as the window's root Context
            if i == 0: win_root = cwd

            panes.append({
                "index": int(idx),
                "id": sid if sid and sid != "null" else role,
                "role": role,
                "title": title,
                "command": get_pane_command(pid),
                "cwd": cwd,
                "geom": {
                    "w_pct": round(int(w) / win_w, 4),
                    "h_pct": round(int(h) / win_h, 4),
                    "l_pct": round(int(l) / win_w, 4),
                    "t_pct": round(int(t) / win_h, 4)
                }
            })

        # 3. Create a 'Moment' object
        moment = {
            "window_idx": window_idx,
            "project_root": win_root or os.getcwd(),
            "timestamp": subprocess.check_output(["date", "+%s"]).decode().strip(),
            "dimensions": {"w": win_w, "h": win_h},
            "layout_string": layout_str,
            "panes": panes
        }
        
        return moment

    except Exception as e:
        print(f"Moment Capture Error: {e}", file=sys.stderr)
        return None

def export_composition(moment, name, project_root):
    """Saves a captured moment as a named composition blueprint."""
    comp_dir = Path(project_root) / ".nexus" / "compositions"
    comp_dir.mkdir(parents=True, exist_ok=True)
    
    comp_path = comp_dir / f"{name}.json"
    
    # Transform 'Moment' back to 'Composition' format
    composition = {
        "name": name,
        "description": f"Exported from live session on {moment['timestamp']}",
        "layout": {
            "type": "momentum_snapshot", # Custom type for momentum-based restores
            "panes": moment["panes"]
        }
    }
    
    with open(comp_path, "w") as f:
        json.dump(composition, f, indent=4)
    
    return comp_path

def main():
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    
    # Resolve session
    try:
        session_id = run_tmux(["display-message", "-p", "#{session_id}"])
        if not session_id: sys.exit(1)
    except:
        sys.exit(1)

    # Momentum Flags
    # AXIOM: Only save the CURRENT window by default to prevent "Window Bloat"
    save_all = "--all" in sys.argv
    export_name = None
    
    if "--export" in sys.argv:
        try:
            idx = sys.argv.index("--export")
            export_name = sys.argv[idx + 1]
        except IndexError:
            pass

    # Invariant Verification (Axiom P-01)
    if "--root" in sys.argv:
        try:
            root_idx = sys.argv.index("--root")
            project_root = sys.argv[root_idx + 1]
            os.environ["PROJECT_ROOT"] = project_root
        except IndexError:
            pass

    if not project_root or not os.path.exists(project_root):
        print(f"FATAL: Invariant violated. PROJECT_ROOT invalid: {project_root}", file=sys.stderr)
        sys.exit(101)

    engine = NexusStateEngine(project_root) if NexusStateEngine else None
    
    windows_to_save = []
    if save_all:
        windows_to_save = run_tmux(["list-windows", "-t", session_id, "-F", "#{window_index}"]).split("\n")
    elif export_name:
        current_win = run_tmux(["display-message", "-p", "#{window_index}"])
        windows_to_save = [current_win]
    else:
        try:
            win_arg_idx = sys.argv.index("--window")
            windows_to_save = [sys.argv[win_arg_idx + 1]]
        except:
            current_win = run_tmux(["display-message", "-p", "#{window_index}"])
            windows_to_save = [current_win]

    captured_count = 0
    for w_idx in windows_to_save:
        if not w_idx.strip(): continue
        moment = capture_moment(session_id, w_idx.strip())
        if not moment: continue

        # Normal State Engine Save
        if engine:
            engine.set(f"session.windows.{w_idx}", moment)
            for pane in moment.get("panes", []):
                sid = pane.get("id")
                cmd = pane.get("command")
                if sid and sid != "null" and cmd:
                    engine.set(f"ui.slots.{sid}.tool", cmd)
            captured_count += 1

        # Export if requested
    if export_name:
            path = export_composition(moment, export_name, project_root)
            run_tmux(["display-message", f"Exported layout to {path.name}"])

    if captured_count > 0 and not export_name:
        run_tmux(["display-message", f"Momentum: Frozen {captured_count} window(s) in State Engine"])
        if engine:
            print(f"Axiom-D: Successfully saved {captured_count} windows to {engine.active_file}")
        else:
            print(f"Axiom-D: Captured {captured_count} windows but State Engine was unavailable.")
    else:
        print(f"Axiom-D: Failed to capture any windows (count={captured_count})")

if __name__ == "__main__":
    main()
