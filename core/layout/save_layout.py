#!/usr/bin/env python3
"""
save_layout.py — Captures the current tmux session state using tmux's
native layout serialization format. No parsing, no coordinate math.

Saves:
  1. The raw #{window_layout} string (replayed verbatim via select-layout)
  2. An ordered list of pane titles + their running commands

Output: .nexus/session_state.json
"""

import sys
import subprocess
import json
import os
from pathlib import Path


def get_leaf_process(pid):
    """Recursively find the deepest child process."""
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

def get_pane_command(pane_pid):
    """Detect the foreground process by finding the leaf descendant."""
    try:
        leaf_pid = get_leaf_process(pane_pid)
        if str(leaf_pid) != str(pane_pid):
            cmd = subprocess.check_output(
                ["ps", "-p", str(leaf_pid), "-o", "command="],
                stderr=subprocess.DEVNULL
            ).decode().strip()

            if cmd:
                # If the leaf is fzf or nexus-menu, they are still in the menu
                if "fzf" in cmd or "nexus-menu" in cmd or "px-engine" in cmd:
                    return "$PARALLAX_CMD"
                if "nvim" in cmd or "vim" in cmd:
                    return "$EDITOR_CMD"
                if "yazi" in cmd or "ranger" in cmd or "lf" in cmd:
                    return "YAZI_CONFIG_HOME=\"$NEXUS_HOME/config/yazi\" $NEXUS_FILES '$PROJECT_ROOT'"
                if "opencode" in cmd or "aider" in cmd or "gptme" in cmd:
                    return "$NEXUS_CHAT"
                if "zsh" in cmd or "bash" in cmd:
                    return "/bin/zsh -i"
                
                base_cmd = cmd.split()[0].split("/")[-1]
                if base_cmd in ["node", "python", "python3", "bash", "sh"]:
                    return cmd
                
                return base_cmd
    except Exception:
        pass
    return "/bin/zsh -i"


def save_window_state(session_id, window_idx, branch_name):
    # 1. Capture the raw layout string for this specific window
    try:
        layout_string = subprocess.check_output(
            ["tmux", "list-windows", "-t", session_id, "-F", "#{window_index}|#{window_layout}"],
            stderr=subprocess.DEVNULL
        ).decode().strip().split("\n")
        
        # Find the specific window layout
        target_layout = None
        for line in layout_string:
            if line.startswith(f"{window_idx}|"):
                target_layout = line.split("|", 1)[1]
                break
        
        if not target_layout:
             return
    except Exception as e:
        print(f"Error getting layout for window {window_idx}: {e}", file=sys.stderr)
        return

    # 2. Capture pane order, titles, and running processes for this window
    try:
        pane_lines = subprocess.check_output(
            ["tmux", "list-panes", "-t", f"{session_id}:{window_idx}",
             "-F", "#{pane_index}|#{pane_title}|#{pane_pid}"],
            stderr=subprocess.DEVNULL
        ).decode().strip().split("\n")
    except Exception as e:
        print(f"Error listing panes for window {window_idx}: {e}", file=sys.stderr)
        return

    panes = []
    for line in pane_lines:
        parts = line.split("|")
        if len(parts) >= 3:
            idx, title, pid = parts[0], parts[1], parts[2]
            cmd = get_pane_command(pid)
            panes.append({
                "index": int(idx),
                "title": title if title else f"pane_{idx}",
                "command": cmd,
            })

    # Sort by index to preserve order
    panes.sort(key=lambda p: p["index"])

    # 3. Build the state object
    state = {
        "layout_string": target_layout,
        "pane_count": len(panes),
        "panes": [{"title": p["title"], "command": p["command"]} for p in panes],
    }

    # 4. Write to project-local .nexus/branches/<branch>/window_<idx>.json
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    
    # Clean branch name just in case
    safe_branch = branch_name.replace("/", "_")
    save_dir = Path(project_root) / ".nexus" / "branches" / safe_branch
    save_dir.mkdir(parents=True, exist_ok=True)
    
    save_file = save_dir / f"window_{window_idx}.json"

    with open(save_file, "w") as f:
        json.dump(state, f, indent=4)

    return save_file

def main():
    save_all = "--all" in sys.argv
    
    # 1. Resolve session ID
    session_id = None
    try:
        session_id = subprocess.check_output(
            ["tmux", "display-message", "-p", "#{session_name}"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        pass

    if not session_id:
        print("Error: No tmux session found.", file=sys.stderr)
        sys.exit(1)

    # 2. Detect Git Branch Context
    branch = ""
    if "--branch" in sys.argv:
        try:
            branch_idx = sys.argv.index("--branch")
            branch = sys.argv[branch_idx + 1]
        except IndexError:
            pass

    if not branch:
        try:
            project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
            branch = subprocess.check_output(
                ["git", "-C", project_root, "branch", "--show-current"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            branch = ""
        
    if not branch:
        branch = "main"

    # 3. Dispatch saves
    if save_all:
        try:
            windows = subprocess.check_output(
                ["tmux", "list-windows", "-t", session_id, "-F", "#{window_index}"],
                stderr=subprocess.DEVNULL
            ).decode().strip().split("\n")
            
            for w in windows:
                if w.strip():
                    save_window_state(session_id, w.strip(), branch)
                    
            subprocess.run(["tmux", "display-message", f"Saved {len(windows)} windows to branch: {branch}"], stderr=subprocess.DEVNULL)
        except Exception as e:
             pass
    else:
        try:
            current_window = subprocess.check_output(
                ["tmux", "display-message", "-p", "#{window_index}"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            
            save_file = save_window_state(session_id, current_window, branch)
            if save_file:
                 subprocess.run(["tmux", "display-message", f"Saved window {current_window} → branches/{branch}"], stderr=subprocess.DEVNULL)
        except Exception:
             pass

if __name__ == "__main__":
    main()
