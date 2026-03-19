#!/usr/bin/env python3
# core/engine/api/nexus_ctl.py
"""
Nexus Control CLI (nexus-ctl)
==============================
Unified entry point for all nexus intent dispatch.

Replaces the fragmented pattern of:
  python3 /full/path/intent_resolver.py TYPE|DATA 2>/dev/null | jq ...

Usage:
  nexus-ctl TYPE|PAYLOAD                              # legacy router.sh format (outputs JSON plan)
  nexus-ctl run TYPE PAYLOAD                          # new format (outputs JSON plan)
  nexus-ctl run TYPE PAYLOAD --intent replace         # intent hint
  nexus-ctl run TYPE PAYLOAD --caller menu            # caller hint
  nexus-ctl run TYPE PAYLOAD --execute                # execute the plan now (non-interactive)
  nexus-ctl --help
  nexus-ctl --version
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

# Make core engine importable regardless of cwd
_HERE = Path(__file__).resolve().parent
_ENGINE_ROOT = _HERE.parent.parent  # core/
_PROJECT_ROOT = _ENGINE_ROOT.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_ENGINE_ROOT.parent))

from intent_resolver import IntentResolver

__version__ = "1.0.0"


def parse_legacy(payload: str) -> tuple[str, str, str]:
    """Parse legacy TYPE|DATA format into (verb, item_type, data)."""
    if "|" in payload:
        itype, data = payload.split("|", 1)
        return "run", itype.strip().upper(), data.strip()
    return "run", "ACTION", payload.strip()


def execute_plan(plan_dict: dict, nexus_home: str) -> int:
    """
    Execute a resolved plan dict using the stack binary.
    Returns the exit code.
    """
    strategy = plan_dict.get("strategy", "stack_push")
    role     = plan_dict.get("role", "local")
    cmd      = plan_dict.get("cmd") or ""
    name     = plan_dict.get("name") or role
    target   = plan_dict.get("target", "")
    idx      = plan_dict.get("index", "0")

    stack_bin = Path(nexus_home) / "core/kernel/stack/stack"
    ctl_bin   = Path(nexus_home) / "core/kernel/bin/control"

    try:
        if strategy == "stack_switch":
            return subprocess.run([str(stack_bin), "switch", "local", str(idx)]).returncode

        elif strategy == "stack_replace":
            return subprocess.run([str(stack_bin), "replace", role, cmd, name]).returncode

        elif strategy == "stack_push":
            return subprocess.run([str(stack_bin), "push", role, cmd, name]).returncode

        elif strategy == "exec_local":
            return subprocess.run(cmd, shell=True).returncode

        elif strategy == "remote_control":
            return subprocess.run([str(ctl_bin), target, cmd]).returncode

        else:
            # Unknown strategy — fall back to stack_push
            return subprocess.run([str(stack_bin), "push", role, cmd, name]).returncode

    except FileNotFoundError as e:
        print(f"nexus-ctl: binary not found: {e}", file=sys.stderr)
        return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="nexus-ctl",
        description="Nexus unified intent dispatch CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nexus-ctl ROLE|editor
  nexus-ctl run ROLE editor
  nexus-ctl run NOTE /tmp/notes.md --intent replace --caller menu
  nexus-ctl run ACTION ":workspace dev" --execute
        """,
    )
    parser.add_argument("--version", action="version", version=f"nexus-ctl {__version__}")
    parser.add_argument("--execute", action="store_true",
                        help="Execute the plan (call stack binary). Default: print JSON plan.")
    parser.add_argument("--intent", default="push", choices=["push", "replace", "swap"],
                        help="Intent hint (default: push)")
    parser.add_argument("--caller", default="terminal", choices=["terminal", "menu"],
                        help="Caller context (default: terminal)")

    # Positional: either "TYPE|DATA" legacy or "run TYPE PAYLOAD"
    parser.add_argument("args", nargs="+", help="TYPE|PAYLOAD  OR  run TYPE PAYLOAD")

    opts = parser.parse_args(argv)
    nexus_home = os.environ.get("NEXUS_HOME", str(_PROJECT_ROOT))

    # --- Parse positional args ---
    if len(opts.args) == 1:
        # Legacy: nexus-ctl "ROLE|editor" or bare "ROLE|editor"
        verb, itype, payload = parse_legacy(opts.args[0])
    elif len(opts.args) == 3 and opts.args[0].lower() == "run":
        # New: nexus-ctl run ROLE editor
        verb, itype, payload = opts.args[0], opts.args[1].upper(), opts.args[2]
    elif len(opts.args) == 2:
        # Short new: nexus-ctl ROLE editor
        verb, itype, payload = "run", opts.args[0].upper(), opts.args[1]
    else:
        parser.print_help()
        return 1

    # --- Resolve ---
    try:
        resolver = IntentResolver()
        plan = resolver.resolve(verb, itype, payload, opts.intent, opts.caller)
    except Exception as e:
        print(json.dumps({"error": str(e), "type": itype, "payload": payload}))
        return 1

    if not plan or not plan.get("cmd") and plan.get("strategy") not in ("stack_switch",):
        print(json.dumps({"error": "Empty plan returned", "type": itype, "payload": payload}))
        return 1

    # --- Output or execute ---
    if opts.execute:
        return execute_plan(plan, nexus_home)
    else:
        print(json.dumps(plan))
        return 0


if __name__ == "__main__":
    sys.exit(main())
