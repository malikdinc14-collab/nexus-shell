"""
Station — the Python boot module for Nexus Shell.

Replaces the inline Python snippets and complex logic from bin/nxs.
Called as: python3 -m engine.station [project_root] [options]

Returns JSON with session info for the bash shim to attach.
"""

import argparse
import getpass
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

NEXUS_HOME = os.environ.get("NEXUS_HOME", "")
USER = getpass.getuser()


def _resolve_project(args) -> dict:
    """Resolve project root, name, session ID, and composition from CLI args.

    Handles: bare directory, .nexus-workspace manifest, named composition.
    """
    project_root = os.getcwd()
    session_id = None
    composition = os.environ.get("NEXUS_COMPOSITION", "__saved_session__")
    workspace_manifest = None
    profile = None

    # Positional args: project dir, workspace manifest, or composition name
    for arg in args.positional:
        if arg.endswith(".nexus-workspace") and os.path.isfile(arg):
            workspace_manifest = os.path.abspath(arg)
        elif os.path.isdir(arg):
            project_root = os.path.abspath(arg)
        elif composition == "__saved_session__":
            composition = arg

    # Explicit flags override
    if args.composition:
        composition = args.composition
    if args.profile:
        profile = args.profile

    # Workspace manifest resolution
    if workspace_manifest:
        try:
            with open(workspace_manifest) as f:
                manifest = json.load(f)
            primary = manifest.get("primary_root", "")
            roots = manifest.get("roots", {})
            if primary in roots:
                root = roots[primary]
            elif primary and not primary.startswith("/"):
                root = os.path.join(os.path.dirname(workspace_manifest), primary)
            else:
                root = primary
            project_root = os.path.abspath(os.path.expanduser(root))
            session_id = manifest.get("workspace_id", "nexus-workspace")
        except Exception:
            pass

    # Normalize
    project_root = os.path.realpath(project_root)
    project_name = session_id or os.path.basename(project_root)
    session_id = session_id or f"nexus_{project_name}"
    if not session_id.startswith("nexus_"):
        session_id = f"nexus_{project_name}"
    socket_label = f"nexus_{project_name}"

    return {
        "project_root": project_root,
        "project_name": project_name,
        "session_id": session_id,
        "socket_label": socket_label,
        "composition": composition,
        "profile": profile,
        "workspace_manifest": workspace_manifest,
    }


def _detect_shell() -> str:
    """Find the user's preferred shell."""
    for shell in ("zsh", "bash"):
        path = shutil.which(shell)
        if path:
            return path
    return "/bin/sh"


def _has_saved_session(project_root: str) -> bool:
    """Check if a saved session exists via the state engine."""
    try:
        sys.path.insert(0, os.path.join(NEXUS_HOME, "core/engine/state"))
        from state_engine import NexusStateEngine
        engine = NexusStateEngine(project_root)
        windows = engine.get("session.windows")
        return bool(windows)
    except Exception:
        return False


def _saved_window_indices(project_root: str) -> list:
    """Get sorted list of saved window indices."""
    try:
        sys.path.insert(0, os.path.join(NEXUS_HOME, "core/engine/state"))
        from state_engine import NexusStateEngine
        engine = NexusStateEngine(project_root)
        windows = engine.get("session.windows")
        if windows:
            return sorted(windows.keys(), key=int)
    except Exception:
        pass
    return []


def _tmux(args: list, socket_label: str) -> Optional[str]:
    """Run a tmux command with the given socket label."""
    cmd = ["tmux", "-L", socket_label] + args
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        return result.stdout.decode("utf-8", errors="replace").strip()
    except subprocess.CalledProcessError:
        return None


def _session_exists(session_id: str, socket_label: str) -> bool:
    """Check if a tmux session already exists."""
    return _tmux(["has-session", "-t", session_id], socket_label) is not None


def _resolve_tmux_conf() -> str:
    """Find the tmux config file."""
    user_conf = os.path.expanduser("~/.config/nexus-shell/config/tmux/nexus.conf")
    if os.path.isfile(user_conf):
        return user_conf
    return os.path.join(NEXUS_HOME, "config/tmux/nexus.conf")


def boot(argv: list = None) -> dict:
    """Execute the full station boot sequence.

    Returns a dict with session info for the bash shim to use for attach.
    """
    parser = argparse.ArgumentParser(description="Nexus Station Boot")
    parser.add_argument("positional", nargs="*", default=[])
    parser.add_argument("--composition", "-c", "--layout", "-l", default=None)
    parser.add_argument("--profile", "-p", default=None)
    args = parser.parse_args(argv)

    ctx = _resolve_project(args)
    project_root = ctx["project_root"]
    project_name = ctx["project_name"]
    session_id = ctx["session_id"]
    socket_label = ctx["socket_label"]
    composition = ctx["composition"]

    # Export environment for downstream scripts
    os.environ.update({
        "PROJECT_ROOT": project_root,
        "PROJECT_NAME": project_name,
        "NEXUS_PROJECT": project_name,
        "SESSION_ID": session_id,
        "SOCKET_LABEL": socket_label,
        "YAZI_CONFIG_HOME": os.path.join(NEXUS_HOME, "config/yazi"),
    })
    if ctx["workspace_manifest"]:
        os.environ["WORKSPACE_MANIFEST"] = ctx["workspace_manifest"]

    # Resolve composition
    if composition in ("__saved_session__", "last"):
        if _has_saved_session(project_root):
            composition = "__saved_session__"
        else:
            print("    [*] No saved session found. Defaulting to vscodelike.",
              file=sys.stderr)
            composition = "vscodelike"

    shell = _detect_shell()
    os.environ["NEXUS_SHELL"] = shell
    tmux_conf = _resolve_tmux_conf()

    print(f"\033[1;36m[*] INITIALIZING STATION: {project_name}\033[0m",
          file=sys.stderr)
    print(f"    Layout: {composition}", file=sys.stderr)
    print(f"    Session: {session_id}", file=sys.stderr)

    # Ensure daemon is running
    daemon_client = os.path.join(NEXUS_HOME, "core/engine/lib/daemon_client.py")
    subprocess.run([sys.executable, daemon_client, "ensure"],
                   check=True, stdout=subprocess.DEVNULL)

    # Create or reuse tmux session
    exists = _session_exists(session_id, socket_label)

    if exists:
        # Find or create workspace window
        windows = _tmux(
            ["list-windows", "-t", session_id, "-F", "#{window_name}"],
            socket_label,
        )
        window_list = windows.split("\n") if windows else []

        if "workspace_0" in window_list:
            window_idx = 0
        else:
            used = _tmux(
                ["list-windows", "-t", session_id, "-F", "#{window_index}"],
                socket_label,
            )
            used_set = set(used.split("\n")) if used else set()
            window_idx = next(i for i in range(10) if str(i) not in used_set)
            _tmux(
                ["new-window", "-d", "-t", session_id, "-k",
                 "-t", str(window_idx), "-n", f"workspace_{window_idx}",
                 "-c", project_root, shell],
                socket_label,
            )
    else:
        window_idx = 0
        cols = os.environ.get("COLUMNS", "80")
        lines = os.environ.get("LINES", "24")
        try:
            import struct, fcntl, termios
            data = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ,
                               b'\x00' * 8)
            rows, col = struct.unpack('HHHH', data)[:2]
            cols, lines = str(col), str(rows)
        except Exception:
            pass

        result = _tmux(
            ["-f", tmux_conf, "new-session", "-d", "-s", session_id,
             "-n", "workspace_0", "-c", project_root,
             "-x", cols, "-y", lines, shell],
            socket_label,
        )
        if result is None:
            print("\033[1;31m[!] CRITICAL: Failed to create tmux session\033[0m",
                  file=sys.stderr)
            return {"status": "error"}

        # Recreate saved windows for multi-window restore
        if composition == "__saved_session__":
            for w_idx in _saved_window_indices(project_root):
                if w_idx != "0":
                    _tmux(
                        ["new-window", "-d", "-t", f"{session_id}:{w_idx}",
                         "-n", f"workspace_{w_idx}", "-c", project_root, shell],
                        socket_label,
                    )

    # Propagate SOCKET_LABEL into tmux env
    _tmux(["set-environment", "-g", "SOCKET_LABEL", socket_label], socket_label)

    # Window-specific setup
    os.environ["WINDOW_IDX"] = str(window_idx)
    window_suffix = f"_w{window_idx}"
    os.environ["NEXUS_WINDOW_SUFFIX"] = window_suffix
    nvim_pipe = f"/tmp/nexus_{USER}/pipes/nvim_{project_name}{window_suffix}.pipe"
    os.makedirs(os.path.dirname(nvim_pipe), exist_ok=True)
    os.environ["NVIM_PIPE"] = nvim_pipe

    # State directory
    state_dir = f"/tmp/nexus_{USER}/{project_name}/parallax"
    os.makedirs(state_dir, exist_ok=True)
    os.environ["PX_STATE_DIR"] = state_dir

    # Station manager init
    station_mgr = os.path.join(NEXUS_HOME, "core/engine/api/station_manager.sh")
    if os.path.isfile(station_mgr):
        subprocess.run([station_mgr, project_name, "init"],
                       env=os.environ, capture_output=True)

    # HUD window
    hud_exists = _tmux(
        ["has-session", "-t", f"{session_id}:HUD"], socket_label,
    )
    if hud_exists is None:
        hud_renderer = os.path.join(NEXUS_HOME, "core/ui/hud/renderer.sh")
        _tmux(
            ["new-window", "-d", "-t", f"{session_id}:10", "-n", "HUD",
             "-c", project_root, hud_renderer],
            socket_label,
        )

    # Clean and recreate pipes
    pipes_dir = f"/tmp/nexus_{USER}/{project_name}/pipes"
    if os.path.isdir(pipes_dir):
        shutil.rmtree(pipes_dir, ignore_errors=True)
    os.makedirs(pipes_dir, exist_ok=True)

    # Build layout via daemon
    print(f"[*] Constructing Workspace: {composition} in Slot {window_idx}...",
          file=sys.stderr)
    subprocess.run(
        [sys.executable, daemon_client, "boot_layout",
         json.dumps({
             "name": composition,
             "window": f"{session_id}:{window_idx}",
             "project_root": project_root,
             "socket_label": socket_label,
         })],
        check=True, stdout=subprocess.DEVNULL,
    )

    # Create client session
    client_session = f"{session_id}_client_{os.getpid()}"
    _tmux(["new-session", "-d", "-t", session_id, "-s", client_session],
          socket_label)

    # Select workspace window
    _tmux(["select-window", "-t", f"{client_session}:{window_idx}"], socket_label)

    print("\033[1;32m[*] Station Solidified.\033[0m", file=sys.stderr)

    return {
        "status": "ok",
        "session_id": session_id,
        "client_session": client_session,
        "socket_label": socket_label,
        "window_idx": window_idx,
        "project_root": project_root,
    }


if __name__ == "__main__":
    result = boot()
    # Output JSON for the bash shim to parse
    print(json.dumps(result))
