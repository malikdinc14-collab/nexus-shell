#!/usr/bin/env python3
"""
Nexus Trace Logger
Captures execution flow for debugging and replay.
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

TRACE_DIR = Path(f"/tmp/nexus_{os.getlogin()}/trace")
SESSION_FILE = TRACE_DIR / "active_session"
TRACE_FILE = None
VERBOSITY = "normal"  # minimal, normal, verbose

VERBOSITY_LEVELS = {"minimal": 1, "normal": 2, "verbose": 3}


def get_verbosity_level():
    return VERBOSITY_LEVELS.get(os.environ.get("NXS_TRACE_VERBOSITY", VERBOSITY), 2)


def is_tracing():
    return TRACE_FILE is not None and SESSION_FILE.exists()


def get_trace_path():
    if SESSION_FILE.exists():
        return Path(SESSION_FILE.read_text().strip())
    return None


def start_trace(verbosity="normal"):
    global TRACE_FILE, VERBOSITY

    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    old_sessions = sorted(TRACE_DIR.glob("session_*.log"))
    for old in old_sessions[:-0]:
        old.unlink()
        snapshot_dir = TRACE_DIR / "snapshots" / old.stem.replace("session_", "")
        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_path = TRACE_DIR / f"session_{timestamp}.log"
    trace_path.write_text("")

    SESSION_FILE.write_text(str(trace_path))
    TRACE_FILE = open(trace_path, "a")
    VERBOSITY = verbosity

    _emit("SESSION_START", verbosity=verbosity)

    return trace_path


def stop_trace():
    global TRACE_FILE

    if TRACE_FILE:
        _emit("SESSION_END")
        TRACE_FILE.close()
        TRACE_FILE = None

    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def _emit(event_type, **data):
    if not TRACE_FILE:
        return

    entry = {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "type": event_type,
        **data,
    }

    TRACE_FILE.write(json.dumps(entry) + "\n")
    TRACE_FILE.flush()


def emit(event_type, min_level=2, **data):
    if not is_tracing():
        return
    if get_verbosity_level() < min_level:
        return
    _emit(event_type, **data)


def emit_state_snapshot(label=""):
    if not is_tracing():
        return

    import subprocess

    try:
        panes_raw = (
            subprocess.check_output(
                [
                    "tmux",
                    "list-panes",
                    "-a",
                    "-F",
                    "#{pane_id}|#{window_name}|#{pane_current_command}|#{@nexus_role}|#{@nexus_tab_name}",
                ],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except:
        panes_raw = ""

    panes = []
    for line in panes_raw.split("\n"):
        if not line:
            continue
        parts = line.split("|")
        panes.append(
            {
                "id": parts[0] if len(parts) > 0 else None,
                "window": parts[1] if len(parts) > 1 else None,
                "command": parts[2] if len(parts) > 2 else None,
                "role": parts[3] if len(parts) > 3 else None,
                "tab_name": parts[4] if len(parts) > 4 else None,
            }
        )

    stack_path = TRACE_DIR.parent / "stacks.json"
    stack_state = {}
    if stack_path.exists():
        try:
            stack_state = json.loads(stack_path.read_text())
        except:
            pass

    try:
        focused = (
            subprocess.check_output(["tmux", "display-message", "-p", "#{pane_id}"])
            .decode()
            .strip()
        )
    except:
        focused = None

    _emit(
        "STATE_SNAPSHOT", label=label, focused=focused, panes=panes, stack=stack_state
    )


def emit_action_start(verb, item_type, payload, caller_pane=None):
    if not is_tracing():
        return

    if caller_pane is None:
        import subprocess

        try:
            caller_pane = (
                subprocess.check_output(["tmux", "display-message", "-p", "#{pane_id}"])
                .decode()
                .strip()
            )
        except:
            caller_pane = None

    _emit(
        "ACTION_START",
        verb=verb,
        type=item_type,
        payload=payload,
        caller_pane=caller_pane,
    )


def emit_action_end(success=True, error=None):
    if not is_tracing():
        return
    _emit("ACTION_END", success=success, error=error)


def emit_resolve_visible(focused_id, tabs, result, reason):
    emit(
        "RESOLVE_VISIBLE",
        min_level=2,
        focused_id=focused_id,
        tabs=[{"id": t.get("id"), "name": t.get("name")} for t in tabs],
        result=result,
        reason=reason,
    )


def emit_resolve_role(input_role, focused_id, role_on_focused, output):
    emit(
        "RESOLVE_ROLE",
        min_level=2,
        input=input_role,
        focused_id=focused_id,
        role_on_focused=role_on_focused,
        output=output,
    )


def emit_stack_op(op, role, **details):
    emit(f"STACK_{op.upper()}", min_level=1, role=role, **details)


def emit_tmux_cmd(args, result, duration_ms=None):
    emit("TMUX_CMD", min_level=3, args=args, result=result, duration_ms=duration_ms)


def emit_swap(source, target):
    emit("SWAP_EXEC", min_level=2, source=source, target=target)


def emit_warning(message, context=None):
    emit("WARNING", min_level=1, message=message, context=context or {})


def replay(log_path, step=None, verbosity_filter=None):
    path = Path(log_path)
    if not path.exists():
        print(f"Error: Log file not found: {log_path}")
        return

    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except:
                    pass

    if step is not None:
        actions = [e for e in entries if e.get("type") == "ACTION_START"]
        if step < 1 or step > len(actions):
            print(f"Invalid step. Available: 1-{len(actions)}")
            return

        target = actions[step - 1]
        start_ts = target["ts"]
        end_idx = None
        for i, e in enumerate(entries):
            if e["ts"] > start_ts and e.get("type") == "ACTION_END":
                end_idx = i
                break

        if end_idx:
            entries = entries[entries.index(target) : end_idx + 1]
        else:
            entries = entries[entries.index(target) :]

    for entry in entries:
        if verbosity_filter:
            min_level = VERBOSITY_LEVELS.get(verbosity_filter, 2)
            event_level = 1
            if entry["type"] in ("TMUX_CMD",):
                event_level = 3
            elif entry["type"] in ("RESOLVE_VISIBLE", "RESOLVE_ROLE", "SWAP_EXEC"):
                event_level = 2
            if event_level > min_level:
                continue

        print(json.dumps(entry, indent=2))


def status():
    trace_path = get_trace_path()
    if trace_path and trace_path.exists():
        print(f"Tracing: ON")
        print(f"Log: {trace_path}")
        print(f"Verbosity: {os.environ.get('NXS_TRACE_VERBOSITY', 'normal')}")

        with open(trace_path) as f:
            lines = [l for l in f if l.strip()]
        print(f"Entries: {len(lines)}")

        actions = [json.loads(l) for l in lines if '"type": "ACTION_START"' in l]
        print(f"Actions recorded: {len(actions)}")
    else:
        print("Tracing: OFF")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: trace.py <command> [args]")
        print("Commands: start, stop, status, snapshot, replay <file>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "start":
        v = sys.argv[2] if len(sys.argv) > 2 else "normal"
        path = start_trace(v)
        print(f"Trace started: {path}")
        emit_state_snapshot("initial")
    elif cmd == "stop":
        emit_state_snapshot("final")
        stop_trace()
        print("Trace stopped")
    elif cmd == "status":
        status()
    elif cmd == "snapshot":
        if not is_tracing():
            print("Error: Tracing not active")
        else:
            label = sys.argv[2] if len(sys.argv) > 2 else ""
            emit_state_snapshot(label)
            print(f"Snapshot captured: {label}")
    elif cmd == "replay":
        if len(sys.argv) < 3:
            print(
                "Usage: trace.py replay <file> [--step N] [--verbosity minimal|normal|verbose]"
            )
            sys.exit(1)

        log_file = sys.argv[2]
        step = None
        verbosity = None

        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--step" and i + 1 < len(sys.argv):
                step = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--verbosity" and i + 1 < len(sys.argv):
                verbosity = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        replay(log_file, step, verbosity)
