#!/usr/bin/env python3
import json
import sys
import os
import subprocess
import time

DEBUG = True

def log(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}", file=sys.stderr)

def tmux(args):
    # Try to find absolute path for tmux to be safe
    tmux_path = "/usr/local/bin/tmux"
    if not os.path.exists(tmux_path):
        tmux_path = "/opt/homebrew/bin/tmux"
    if not os.path.exists(tmux_path):
        tmux_path = "tmux" # Fallback to PATH
        
    cmd = [tmux_path] + args
    log(f"TMUX_EXEC: {' '.join(cmd)}")
    try:
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
        log(f"  -> OK: {result[:100]}")
        return result
    except subprocess.CalledProcessError as e:
        error_msg = e.output.decode()
        log(f"  -> TMUX_ERROR: {error_msg}")
        # Print to stdout so it gets captured by the layout log
        print(f"[!] TMUX FAILED: {' '.join(cmd)}\n    ERROR: {error_msg}", file=sys.stdout)
        return ""
    except Exception as e:
        log(f"  -> CRITICAL_ERROR: {str(e)}")
        return ""

def expand_vars(cmd, project_root):
    """Expand environment variables in command string"""
    import re
    
    # Use os.environ as base
    env = os.environ.copy()
    env["PROJECT_ROOT"] = project_root
    
    # Default fallbacks
    defaults = {
        "EDITOR_CMD": "nvim",
        "NEXUS_FILES": "yazi",
        "NEXUS_CHAT": "zsh",
        "PARALLAX_CMD": "true",
        "VIRTUAL_ROOT": project_root
    }
    
    for k, v in defaults.items():
        if k not in env:
            env[k] = v

    # Expand $VAR and ${VAR}
    def replace_var(match):
        var_name = match.group(1) or match.group(2)
        return env.get(var_name, f"${{{var_name}}}")

    # Pattern for $VAR or ${VAR}
    pattern = re.compile(r'\$(?:(\w+)|\{(\w+)\})')
    
    # Do expansion 3 times to handle nested vars (e.g. $NEXUS_CORE/$BOOT)
    for _ in range(3):
        new_cmd = pattern.sub(replace_var, cmd)
        if new_cmd == cmd:
            break
        cmd = new_cmd
        
    return cmd

def build(config, target_pane, project_root, wrapper):
    if "panes" not in config:
        # Leaf: Return the command to run
        cmd = config.get("command", "/bin/zsh -i")
        cmd = expand_vars(cmd, project_root)
        
        if config.get("id"):
            tmux(["select-pane", "-t", target_pane, "-T", str(config["id"])])
            
        return cmd

    ltype = config.get("type")
    panes = config.get("panes", [])
    # hsplit means panes are stacked horizontally (left to right) -> tmux split -h
    # vsplit means panes are stacked vertically (top to bottom) -> tmux split -v
    direction = "-h" if ltype == "hsplit" else "-v"
    
    # We recursively split the CURRENT pane. 
    # To achieve [A (30%), B, C], we split A from the main block, then B from the remaining, etc.
    # Current implementation uses -b (before) to split A "left/top" of current.
    
    remaining_pane = target_pane
    
    # Iterate through all but the last pane
    for i in range(len(panes) - 1):
        pane_cfg = panes[i]
        size = pane_cfg.get("size")
        size_arg = []
        if size:
            if isinstance(size, int) and size < 100: 
                size_arg = ["-p", str(size)]
            elif isinstance(size, str):
                size_arg = ["-l", str(size)]
            else:
                size_arg = ["-l", str(size)]

        # We split the NEW pane (which will hold pane_cfg) OUT of the remaining_pane.
        # -d: don't make new pane active (keep focus on remaining to split again)
        # -b: create to the left/top of current (standard read order)
        new_pane = tmux(["split-window", direction, "-b", "-d", "-t", remaining_pane, "-P", "-F", "#{pane_id}", "-c", project_root] + size_arg + ["/bin/zsh"])
        
        if not new_pane:
            log(f"Failed to split pane {i}")
            continue
            
        time.sleep(0.1)
        
        # Build the content of the NEW pane (which is the one we just split off)
        cmd = build(pane_cfg, new_pane, project_root, wrapper)
        if cmd:
            tmux(["send-keys", "-t", new_pane, f"{wrapper} {cmd}", "Enter"])
        
        # Set Role and Title
        role = pane_cfg.get("id")
        if role:
            tmux(["set-option", "-p", "-t", new_pane, "@nexus_role", str(role)])
            tmux(["select-pane", "-t", new_pane, "-T", str(role)])
            
    # The last pane is whatever is left of the original target_pane
    cmd = build(panes[-1], remaining_pane, project_root, wrapper)
    if cmd:
        tmux(["send-keys", "-t", remaining_pane, f"{wrapper} {cmd}", "Enter"])
        
    role = panes[-1].get("id")
    if role:
        tmux(["set-option", "-p", "-t", remaining_pane, "@nexus_role", str(role)])
        tmux(["select-pane", "-t", remaining_pane, "-T", str(role)])
    
    return None

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: processor.py <json_path> <target_pane> <project_root>", file=sys.stderr)
        sys.exit(1)
        
    json_path = sys.argv[1]
    target_pane = sys.argv[2]
    project_root = sys.argv[3]
    wrapper = os.environ.get("WRAPPER", "")
    
    if not wrapper:
        print("ERROR: WRAPPER environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    print(f"[processor] Loading {json_path}", file=sys.stderr)
    print(f"[processor] Target: {target_pane}, Root: {project_root}", file=sys.stderr)
    
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    build(data.get("layout", {}), target_pane, project_root, wrapper)
    print("[processor] Layout complete", file=sys.stderr)
