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

# Add core/state to sys.path to import local engine
sys.path.append(str(Path(__file__).parent.parent / "state"))
try:
    from state_engine import NexusStateEngine
except ImportError:
    NexusStateEngine = None


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

def get_pane_command(pane_pid, title=None, index=None):
    """Detect the foreground process by finding the leaf descendant."""
    try:
        leaf_pid = get_leaf_process(pane_pid)
        if str(leaf_pid) != str(pane_pid):
            cmd = subprocess.check_output(
                ["ps", "-p", str(leaf_pid), "-o", "command="],
                stderr=subprocess.DEVNULL
            ).decode().strip()

            if cmd:
                # 1. Menu/System Triage
                if any(x in cmd for x in ["fzf", "nexus-menu", "px-engine"]):
                    return "$PARALLAX_CMD"
                
                # 2. Editor Triage
                if "nvim" in cmd or "vim" in cmd:
                    return "$EDITOR_CMD"
                
                # 3. File Browser Triage
                if any(x in cmd for x in ["yazi", "ranger", "lf"]):
                    return "YAZI_CONFIG_HOME=\"$NEXUS_HOME/config/yazi\" $NEXUS_FILES '$PROJECT_ROOT'"
                
                # 4. AI Chat Triage (The "Pi" fix)
                chat_tools = ["opencode", "aider", "gptme", "pi", "claude", "chatgpt"]
                if any(x in cmd.lower() for x in chat_tools):
                    # Intelligent Extraction:
                    # If it's 'node /path/to/pi', we want 'pi'
                    # If it's 'pi --args', we want 'pi'
                    for tool in chat_tools:
                        if tool in cmd.lower():
                            return tool
                    return "$NEXUS_CHAT"
                
                # 5. Shell Triage
                if "zsh" in cmd or "bash" in cmd:
                    return "/bin/zsh -i"
                
                # 6. Fallback to base command
                full_cmd_parts = cmd.split()
                base_cmd = full_cmd_parts[0].split("/")[-1]
                
                if base_cmd in ["node", "python", "python3", "bash", "sh"]:
                    # If it's an interpreter, try to get the script name
                    if len(full_cmd_parts) > 1:
                        script_name = full_cmd_parts[1].split("/")[-1].split(".")[0]
                        return script_name
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
             "-F", "#{pane_index}|#{pane_title}|#{pane_pid}|#{@nexus_role}"],
            stderr=subprocess.DEVNULL
        ).decode().strip().split("\n")
    except Exception as e:
        print(f"Error listing panes for window {window_idx}: {e}", file=sys.stderr)
        return

    panes = []
    # Initialize State Engine for sync
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    engine = NexusStateEngine(project_root) if NexusStateEngine else None

    for line in pane_lines:
        parts = line.split("|")
        if len(parts) >= 4:
            idx, title, pid, role = parts[0], parts[1], parts[2], parts[3]
            actual_cmd = get_pane_command(pid, title)
            
            # --- NEW ROLE-BASED LOGIC ---
            # If the pane has a known Nexus role, we save a logical variable
            # instead of the literal command. This ensures the State Engine
            # remains the source of truth for "What is currently active".
            
            saved_cmd = actual_cmd
            
            if role == "chat":
                saved_cmd = "$NEXUS_CHAT"
                if engine and not actual_cmd.startswith("$"):
                    engine.update_slot("chat", actual_cmd)
            elif role == "editor":
                saved_cmd = "$EDITOR_CMD"
                if engine and not actual_cmd.startswith("$") and "nvim" in actual_cmd:
                    engine.update_slot("editor", "nvim")
            elif role == "files":
                saved_cmd = "$NEXUS_FILES"
                if engine and not actual_cmd.startswith("$"):
                    engine.update_slot("files", actual_cmd)

            panes.append({
                "index": int(idx),
                "title": title if title else f"pane_{idx}",
                "command": saved_cmd,
            })

    # Sort by index to preserve order
    panes.sort(key=lambda p: p["index"])

    # 3. Build the state object
    state = {
        "layout_string": target_layout,
        "pane_count": len(panes),
        "panes": [{"title": p["title"], "command": p["command"]} for p in panes],
    }

    # 4. Push to State Engine (Centralized)
    if engine:
        # Instead of multiple files, we now store the active layout in the State Engine
        # under session.windows[idx]
        engine.set(f"session.windows.{window_idx}", state)
        # Also store the branch context
        engine.set("project.active_branch", branch_name)

    return True

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
