#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

USER_TMP = Path(f"/tmp/nexus_{os.getlogin()}")
STACK_STATE = USER_TMP / "stacks.json"
DEBUG_MODE_FILE = USER_TMP / "debug_pane_ids"


def is_debug_mode():
    return DEBUG_MODE_FILE.exists()


def load_state():
    if not STACK_STATE.exists():
        return {}
    try:
        return json.loads(STACK_STATE.read_text())
    except:
        return {}


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
        # Avoid showing the ID twice if the role IS the ID
        role_label = ""
        if role and role != pane_id:
            role_label = f" ({role})"
        print(f"#[fg=yellow,bold][{pane_id}]{role_label}#[default]")
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
    role = get_role(pane_id) or pane_id
    state = load_state()
    if role not in state or not state[role]["tabs"]:
        print(f"#[fg=cyan,bold] {role} ")
        return

    stack = state[role]
    tabs = stack["tabs"]
    active_idx = stack["active_index"]

    output = []
    for i, tab in enumerate(tabs):
        name = tab["name"]
        if i == active_idx:
            output.append(f"#[fg=cyan,bold][ {name} ]")
        else:
            output.append(f"#[fg=white,dim] {name} ")

    print(" ".join(output))


if __name__ == "__main__":
    main()
