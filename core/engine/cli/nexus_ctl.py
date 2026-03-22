#!/usr/bin/env python3
"""nexus-ctl -- unified control interface for nexus-shell.

Supports two invocation styles:
  nexus-ctl menu open                      # subcommand dispatch (preferred)
  nexus-ctl "ROLE|editor"                  # legacy TYPE|PAYLOAD format
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Make core engine importable regardless of cwd
_HERE = Path(__file__).resolve().parent
_ENGINE_ROOT = _HERE.parent.parent  # core/
_PROJECT_ROOT = _ENGINE_ROOT.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_ENGINE_ROOT.parent))


def _pane_id():
    """Resolve the active tmux pane ID from environment."""
    return os.environ.get("TMUX_PANE", "%0")


def _json_out(result):
    """Print a dict as JSON to stdout."""
    print(json.dumps(result, indent=2))


def _handle_legacy(payload: str) -> int:
    """Handle legacy TYPE|PAYLOAD format from the old nexus-ctl.

    Delegates to the intent resolver if available, otherwise prints a
    JSON error.  Returns an exit code.
    """
    if "|" in payload:
        itype, data = payload.split("|", 1)
        itype = itype.strip().upper()
        data = data.strip()
    else:
        itype = "ACTION"
        data = payload.strip()

    nexus_home = os.environ.get("NEXUS_HOME", str(_PROJECT_ROOT))

    try:
        from engine.api.intent_resolver import IntentResolver
        resolver = IntentResolver()
        plan = resolver.resolve("run", itype, data, "push", "terminal")
    except Exception as e:
        print(json.dumps({"error": str(e), "type": itype, "payload": data}))
        return 1

    if not plan or (not plan.get("cmd") and plan.get("strategy") not in ("stack_switch",)):
        print(json.dumps({"error": "Empty plan returned", "type": itype, "payload": data}))
        return 1

    print(json.dumps(plan))
    return 0


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]

    # Legacy detection: if a single arg contains "|", treat as TYPE|PAYLOAD
    if len(args) == 1 and "|" in args[0]:
        return _handle_legacy(args[0])

    parser = argparse.ArgumentParser(
        prog="nexus-ctl",
        description="Nexus Shell control interface",
    )
    subparsers = parser.add_subparsers(dest="domain", help="Command domain")

    # ── menu ─────────────────────────────────────────────────────────────
    menu_parser = subparsers.add_parser("menu", help="Command Graph operations")
    menu_sub = menu_parser.add_subparsers(dest="action")
    menu_sub.add_parser("open", help="Open Command Graph landing page")
    sel_p = menu_sub.add_parser("select", help="Select a menu node")
    sel_p.add_argument("node_id", help="Node ID to select")
    sel_p.add_argument("--mode", default="new_tab", choices=["new_tab", "replace", "edit"])

    # ── capability ────────────────────────────────────────────────────────
    cap_parser = subparsers.add_parser("capability", help="Capability launcher")
    cap_sub = cap_parser.add_subparsers(dest="action")
    cap_sub.add_parser("open", help="Open capability launcher")
    cap_sel = cap_sub.add_parser("select", help="Launch a capability")
    cap_sel.add_argument("type", help="Capability type (e.g. EDITOR)")
    cap_sel.add_argument("--adapter", default="", help="Specific adapter name")
    cap_sel.add_argument("--mode", default="new_tab", choices=["new_tab", "replace"])

    # ── stack ─────────────────────────────────────────────────────────────
    stack_parser = subparsers.add_parser("stack", help="Tab stack operations")
    stack_sub = stack_parser.add_subparsers(dest="action")
    push_p = stack_sub.add_parser("push", help="Push new tab onto focused stack")
    push_p.add_argument("--type", default="terminal", dest="cap_type", help="Capability type")
    push_p.add_argument("--adapter", default="zsh", help="Adapter name")
    stack_sub.add_parser("pop", help="Pop active tab from focused stack")
    rotate_parser = stack_sub.add_parser("rotate", help="Rotate through tabs")
    rotate_parser.add_argument(
        "direction", type=int, choices=[-1, 1], help="Rotation direction"
    )

    # ── tabs ──────────────────────────────────────────────────────────────
    tabs_parser = subparsers.add_parser("tabs", help="Tab manager")
    tabs_sub = tabs_parser.add_subparsers(dest="action")
    tabs_sub.add_parser("list", help="List active tabs in focused stack")
    jump_p = tabs_sub.add_parser("jump", help="Jump to tab by index")
    jump_p.add_argument("index", type=int, help="Tab index")

    # ── pane ──────────────────────────────────────────────────────────────
    pane_parser = subparsers.add_parser("pane", help="Pane operations")
    pane_sub = pane_parser.add_subparsers(dest="action")
    pane_sub.add_parser("kill", help="Kill focused pane and all tabs")
    pane_sub.add_parser("split-v", help="Split pane vertically")
    pane_sub.add_parser("split-h", help="Split pane horizontally")

    # ── workspace ─────────────────────────────────────────────────────────
    ws_parser = subparsers.add_parser("workspace", help="Workspace operations")
    ws_sub = ws_parser.add_subparsers(dest="action")
    ws_sub.add_parser("save", help="Save workspace state")
    restore_p = ws_sub.add_parser("restore", help="Restore workspace")
    restore_p.add_argument("name", nargs="?", default="", help="Snapshot name")
    sc_p = ws_sub.add_parser("switch-composition", help="Switch composition")
    sc_p.add_argument("name", help="Composition name")

    # ── pack ──────────────────────────────────────────────────────────────
    pack_parser = subparsers.add_parser("pack", help="Pack management")
    pack_sub = pack_parser.add_subparsers(dest="action")
    pack_sub.add_parser("list", help="List available packs")
    pack_sub.add_parser("suggest", help="Detect and suggest packs")
    enable_p = pack_sub.add_parser("enable", help="Enable a pack")
    enable_p.add_argument("name", help="Pack name")
    disable_p = pack_sub.add_parser("disable", help="Disable a pack")
    disable_p.add_argument("name", help="Pack name")

    # ── profile ───────────────────────────────────────────────────────────
    prof_parser = subparsers.add_parser("profile", help="Profile management")
    prof_sub = prof_parser.add_subparsers(dest="action")
    prof_sub.add_parser("list", help="List available profiles")
    switch_p = prof_sub.add_parser("switch", help="Switch profile")
    switch_p.add_argument("name", help="Profile name")

    # ── config ────────────────────────────────────────────────────────────
    config_parser = subparsers.add_parser("config", help="Configuration")
    config_sub = config_parser.add_subparsers(dest="action")
    config_sub.add_parser("reload", help="Reload all config")
    theme_p = config_sub.add_parser("apply-theme", help="Apply theme")
    theme_p.add_argument("name", help="Theme name")
    get_p = config_sub.add_parser("get", help="Get config value")
    get_p.add_argument("key", help="Config key")

    # ── hud ───────────────────────────────────────────────────────────────
    hud_parser = subparsers.add_parser("hud", help="HUD status bar modules")
    hud_sub = hud_parser.add_subparsers(dest="action")
    hud_render_p = hud_sub.add_parser("render", help="Render HUD line for given modules")
    hud_render_p.add_argument("module_ids", nargs="*", default=[], help="Module IDs to render")
    hud_render_p.add_argument("--separator", default=" | ", help="Separator between modules")
    hud_sub.add_parser("list", help="List available built-in HUD resolvers")

    # ── bus ────────────────────────────────────────────────────────────────
    bus_parser = subparsers.add_parser("bus", help="Event bus")
    bus_sub = bus_parser.add_subparsers(dest="action")
    pub_p = bus_sub.add_parser("publish", help="Publish event")
    pub_p.add_argument("type", help="Event type")
    pub_p.add_argument("data", help="JSON data")
    sub_p = bus_sub.add_parser("subscribe", help="Subscribe to events")
    sub_p.add_argument("type", help="Event type pattern")
    bus_sub.add_parser("list", help="List active subscriptions")
    hist_p = bus_sub.add_parser("history", help="Show recent events")
    hist_p.add_argument("--limit", type=int, default=20, help="Max events")

    parsed = parser.parse_args(args)

    if not parsed.domain:
        parser.print_help()
        sys.exit(1)

    action = getattr(parsed, "action", None)
    if not action:
        # Print domain help if no action given
        parser.parse_args([parsed.domain, "--help"])
        return

    # ── dispatch ──────────────────────────────────────────────────────────
    dispatch = {
        "menu": _dispatch_menu,
        "capability": _dispatch_capability,
        "stack": _dispatch_stack,
        "tabs": _dispatch_tabs,
        "pane": _dispatch_pane,
        "workspace": _dispatch_workspace,
        "pack": _dispatch_pack,
        "profile": _dispatch_profile,
        "config": _dispatch_config,
        "hud": _dispatch_hud,
        "bus": _dispatch_bus,
    }

    handler = dispatch.get(parsed.domain)
    if handler is None:
        print(f"[nexus-ctl] unknown domain: {parsed.domain}", file=sys.stderr)
        sys.exit(1)

    result = handler(parsed)
    if result is not None:
        _json_out(result)
    return result


# ── Domain dispatchers ───────────────────────────────────────────────────


def _dispatch_menu(args):
    from engine.api.menu_handler import handle_open, handle_select

    if args.action == "open":
        return handle_open()
    elif args.action == "select":
        return handle_select(args.node_id, mode=args.mode)


def _dispatch_capability(args):
    from engine.api.capability_launcher import handle_open, handle_select

    if args.action == "open":
        return handle_open()
    elif args.action == "select":
        return handle_select(args.type, adapter_name=args.adapter, mode=args.mode)


def _dispatch_stack(args):
    from engine.api.stack_handler import handle_push, handle_pop, handle_rotate

    pane = _pane_id()
    if args.action == "push":
        result = handle_push(pane, capability_type=args.cap_type, adapter_name=args.adapter)
        # handle_push returns a Tab or sentinel — serialize it
        if hasattr(result, "id"):
            return {"action": "push", "pane_id": pane, "tab_id": result.id}
        return {"action": "push", "pane_id": pane, "status": "delegated"}
    elif args.action == "pop":
        result = handle_pop(pane)
        if isinstance(result, dict):
            return result
        if result and hasattr(result, "id"):
            return {"action": "pop", "pane_id": pane, "tab_id": result.id}
        return {"action": "pop", "pane_id": pane, "status": "empty"}
    elif args.action == "rotate":
        result = handle_rotate(pane, args.direction)
        if result and hasattr(result, "id"):
            return {"action": "rotate", "pane_id": pane, "active_tab": result.id}
        return {"action": "rotate", "pane_id": pane, "status": "no_rotation"}


def _dispatch_tabs(args):
    from engine.api.tab_manager import handle_list, handle_jump

    pane = _pane_id()
    if args.action == "list":
        return handle_list(pane)
    elif args.action == "jump":
        return handle_jump(pane, args.index)


def _dispatch_pane(args):
    from engine.api.pane_handler import handle_kill, handle_split

    pane = _pane_id()
    if args.action == "kill":
        return handle_kill(pane)
    elif args.action == "split-v":
        return handle_split(pane, "v")
    elif args.action == "split-h":
        return handle_split(pane, "h")


def _dispatch_workspace(args):
    from engine.api.workspace_handler import (
        handle_save,
        handle_restore,
        handle_switch_composition,
    )

    if args.action == "save":
        return handle_save()
    elif args.action == "restore":
        return handle_restore(getattr(args, "name", ""))
    elif args.action == "switch-composition":
        return handle_switch_composition(args.name)


def _dispatch_pack(args):
    from engine.packs.manager import PackManager

    # Resolve pack dirs from config cascade
    nexus_home = os.environ.get("NEXUS_HOME", os.path.join(
        os.path.dirname(__file__), "..", "..", "..",
    ))
    pack_dirs = [
        os.path.normpath(os.path.join(nexus_home, "core", "engine", "packs", "examples")),
    ]
    # Add workspace .nexus/packs if it exists
    ws_packs = os.path.join(os.getcwd(), ".nexus", "packs")
    if os.path.isdir(ws_packs):
        pack_dirs.append(ws_packs)

    mgr = PackManager(pack_dirs)

    if args.action == "list":
        return {
            "packs": [
                {"name": p.name, "version": p.version, "enabled": p.enabled,
                 "description": p.description}
                for p in mgr.available_packs
            ]
        }
    elif args.action == "suggest":
        suggestions = mgr.suggest(os.getcwd())
        return {
            "suggestions": [
                {"name": p.name, "markers": p.markers}
                for p in suggestions
            ]
        }
    elif args.action == "enable":
        ok = mgr.enable(args.name)
        return {"name": args.name, "enabled": ok}
    elif args.action == "disable":
        ok = mgr.disable(args.name)
        return {"name": args.name, "disabled": ok}


def _dispatch_profile(args):
    from engine.profiles.manager import ProfileManager

    nexus_home = os.environ.get("NEXUS_HOME", os.path.join(
        os.path.dirname(__file__), "..", "..", "..",
    ))
    profiles_dir = os.path.normpath(
        os.path.join(nexus_home, "core", "engine", "profiles", "examples")
    )
    mgr = ProfileManager(profiles_dir)

    if args.action == "list":
        return {
            "profiles": [
                {"name": p.name, "description": p.description,
                 "composition": p.composition, "theme": p.theme}
                for p in mgr.available_profiles
            ]
        }
    elif args.action == "switch":
        ok = mgr.switch(args.name)
        return {"name": args.name, "switched": ok}


def _dispatch_config(args):
    from engine.api.config_handler import handle_reload, handle_apply_theme, handle_get

    if args.action == "reload":
        global_dir = os.environ.get("NEXUS_CONFIG_DIR", os.path.expanduser("~/.config/nexus"))
        ws_dir = os.path.join(os.getcwd(), ".nexus")
        return handle_reload(global_dir=global_dir, workspace_dir=ws_dir)
    elif args.action == "apply-theme":
        config_dirs = [
            os.path.join(os.getcwd(), ".nexus"),
            os.environ.get("NEXUS_CONFIG_DIR", os.path.expanduser("~/.config/nexus")),
        ]
        # Also check built-in themes
        nexus_home = os.environ.get("NEXUS_HOME", os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
        ))
        config_dirs.append(os.path.normpath(
            os.path.join(nexus_home, "core", "engine", "config")
        ))
        return handle_apply_theme(args.name, config_dirs)
    elif args.action == "get":
        global_dir = os.environ.get("NEXUS_CONFIG_DIR", os.path.expanduser("~/.config/nexus"))
        ws_dir = os.path.join(os.getcwd(), ".nexus")
        return handle_get(args.key, global_dir=global_dir, workspace_dir=ws_dir)


def _dispatch_hud(args):
    from engine.hud.module import BUILTIN_RESOLVERS
    from engine.hud.renderer import render_hud_line

    if args.action == "render":
        line = render_hud_line(args.module_ids, separator=args.separator)
        # For tmux status-right, print raw string (not JSON)
        print(line)
        return None  # already printed
    elif args.action == "list":
        return {"resolvers": sorted(BUILTIN_RESOLVERS.keys())}


def _dispatch_bus(args):
    from engine.api.bus_handler import (
        handle_history,
        handle_list_subscribers,
        handle_publish,
        handle_subscribe,
    )

    if args.action == "publish":
        try:
            payload = json.loads(args.data)
        except json.JSONDecodeError:
            payload = {"raw": args.data}
        return handle_publish(args.type, "nexus-ctl", payload)
    elif args.action == "subscribe":
        return handle_subscribe(args.type)
    elif args.action == "list":
        return handle_list_subscribers()
    elif args.action == "history":
        return handle_history(limit=args.limit)


if __name__ == "__main__":
    sys.exit(main() or 0)
