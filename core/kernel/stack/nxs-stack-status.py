#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

USER_TMP = Path(f"/tmp/nexus_{os.getlogin()}")
STACK_STATE = USER_TMP / "stacks.json"
DEBUG_MODE_FILE = USER_TMP / "debug_pane_ids"

# State Handshake
sys.path.append(str(Path(__file__).resolve().parent.parent / "state"))
try:
    from state_engine import NexusStateEngine
except ImportError:
    NexusStateEngine = None

def get_engine():
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    if NexusStateEngine:
        return NexusStateEngine(project_root)
    return None

def load_state():
    engine = get_engine()
    if engine:
        return engine.get("ui.stacks") or {}
    return {}


def get_slot(pane_id):
    try:
        import subprocess

        out = (
            subprocess.check_output(
                ["tmux", "display-message", "-p", "-t", pane_id, "#{@nexus_slot}"]
            )
            .decode()
            .strip()
        )
        return out if out and out != "null" else None
    except:
        return None


def get_role(pane_id):
    try:
        import subprocess

        out = (
            subprocess.check_output(
                ["tmux", "display-message", "-p", "-t", pane_id, "#{@nexus_role}"]
            )
            .decode()
            .strip()
        )
        return out if out and out != "null" else None
    except:
        return None


def get_nvim_tabs(pane_id):
    """Query Neovim for its tab list if it is running in this pane."""
    try:
        import subprocess

        focused_role = (
            subprocess.check_output(
                ["tmux", "display-message", "-p", "-t", pane_id, "#{@nexus_role}"]
            )
            .decode()
            .strip()
        )
        current_cmd = (
            subprocess.check_output(
                [
                    "tmux",
                    "display-message",
                    "-p",
                    "-t",
                    pane_id,
                    "#{pane_current_command}",
                ]
            )
            .decode()
            .strip()
        )

        is_editor = focused_role == "editor" or "nvim" in current_cmd
        if not is_editor:
            return None

        nvim_pipe = os.environ.get("NVIM_PIPE")
        if not nvim_pipe or not os.path.exists(nvim_pipe):
            return None

        cmd = [
            "nvim",
            "--server",
            nvim_pipe,
            "--remote-expr",
            "json_encode({'current': tabpagenr(), 'tabs': map(gettabinfo(), 'bufname(tabpagebuflist(v:val.tabnr)[0])')})",
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return json.loads(out)
    except:
        return None


def main():
    if len(sys.argv) < 2:
        return

    pane_id = sys.argv[1]

    # Debug mode: show pane ID prominently
    if is_debug_mode():
        role = get_role(pane_id)
        slot = get_slot(pane_id)
        # Hide raw %id if we have a slot, unless NEXUS_DEBUG_RAW_IDS is set
        if slot and os.environ.get("NEXUS_DEBUG_RAW_IDS") != "true":
            id_label = f"#{slot}"
        else:
            id_label = f"[{pane_id}]"

        if role and role != "null" and role != pane_id and not role.startswith("slot_"):
            label = f"{id_label} ({role})"
        else:
            label = id_label
        print(f"#[fg=yellow,bold]{label}#[default]")
        return

    # 1. Check for Neovim First (Hybrid Mode)
    nv_data = get_nvim_tabs(pane_id)
    if nv_data:
        output = []
        for i, name in enumerate(nv_data["tabs"]):
            idx = i + 1
            display_name = os.path.basename(name) if name else "[No Name]"
            if idx == nv_data["current"]:
                output.append(f"#[fg=cyan,bold][ {display_name} ]")
            else:
                output.append(f"#[fg=white,dim] {display_name} ")
        print(" ".join(output))
        return

    # 2. Fallback to Nexus Stack
    role = get_role(pane_id)
    slot = get_slot(pane_id)
    
    # Hide raw %id if we have a slot, unless NEXUS_DEBUG_RAW_IDS is set
    if slot and os.environ.get("NEXUS_DEBUG_RAW_IDS") != "true":
        id_label = f"#{slot}"
    else:
        id_label = f"[{pane_id}]"

    # The visual identity is either the role or the pane_id
    # Rule: If we have a semantic role, use it. Otherwise, use the stable ID label.
    visual_id = role if role and role != "null" else pane_id
    
    state = load_state()
    
    # Check if this role/pane has a stack
    stack = state.get(visual_id)
    if not stack or not stack.get("tabs"):
        # Just show the ID/Role
        if role and role != "null" and role != pane_id and not role.startswith("slot_"):
            print(f"#[fg=yellow,bold]{id_label}#[default] #[fg=cyan,bold]({role})")
        else:
            print(f"#[fg=yellow,bold]{id_label}#[default]")
        return

    tabs = stack["tabs"]
    active_idx = stack["active_index"]

    output = []
    # Prefix with stable slot ID if it's not already the primary thing
    if slot and visual_id != f"slot_{slot}" and visual_id != role:
         output.append(f"#[fg=yellow,bold]#{slot}#[default]")

    for i, tab in enumerate(tabs):
        name = tab["name"]
        if i == active_idx:
            output.append(f"#[fg=cyan,bold][ {name} ]")
        else:
            output.append(f"#[fg=white,dim] {name} ")

    print(" ".join(output))


if __name__ == "__main__":
    main()
