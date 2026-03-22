#!/usr/bin/env python3
"""Verify all nexus-shell engine modules are importable."""

import importlib
import sys
import os
import time

# Ensure core/ is on the import path
NEXUS_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CORE_DIR = os.path.join(NEXUS_HOME, "core")
sys.path.insert(0, CORE_DIR)

MODULES = [
    # stacks
    "engine.stacks.stack",
    "engine.stacks.reservoir",
    "engine.stacks.manager",
    "engine.stacks.tabbar",
    "engine.stacks.tmux_events",
    # graph
    "engine.graph.node",
    "engine.graph.loader",
    "engine.graph.resolver",
    "engine.graph.live_sources",
    # packs
    "engine.packs.pack",
    "engine.packs.detector",
    "engine.packs.manager",
    # profiles
    "engine.profiles.manager",
    # config
    "engine.config.keymap_loader",
    "engine.config.theme_engine",
    "engine.config.cascade",
    # compositions
    "engine.compositions.schema",
    # connectors
    "engine.connectors.engine",
    # bus
    "engine.bus.typed_events",
    "engine.bus.enhanced_bus",
    # momentum
    "engine.momentum.stack_persistence",
    "engine.momentum.deferred_restore",
    "engine.momentum.geometry",
    "engine.momentum.session",
    # renderers
    "engine.renderers.router",
    "engine.renderers.loader",
    # hud
    "engine.hud.tab_status",
    # api
    "engine.api.menu_handler",
    "engine.api.capability_launcher",
    "engine.api.stack_handler",
    "engine.api.pane_handler",
    "engine.api.tab_manager",
    "engine.api.workspace_handler",
    "engine.api.config_handler",
    "engine.api.bus_handler",
    # cli
    "engine.cli.nexus_ctl",
]


def check_module(module_name: str) -> tuple:
    """Attempt to import a module. Returns (module_name, success, elapsed_ms, error)."""
    start = time.monotonic()
    try:
        importlib.import_module(module_name)
        elapsed = (time.monotonic() - start) * 1000
        return (module_name, True, elapsed, None)
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        return (module_name, False, elapsed, str(exc))


def main():
    print("=" * 64)
    print(" T093: Nexus-Shell Engine Module Import Check")
    print("=" * 64)
    print(f" NEXUS_HOME: {NEXUS_HOME}")
    print(f" Core path:  {CORE_DIR}")
    print(f" Python:     {sys.executable} ({sys.version.split()[0]})")
    print()

    results = []
    for mod in MODULES:
        results.append(check_module(mod))

    # Print results table
    name_width = max(len(r[0]) for r in results)
    header = f"{'Module':<{name_width}}  {'Status':>6}  {'Time':>8}  Error"
    print(header)
    print("-" * len(header) + "-" * 20)

    passed = 0
    failed = 0
    for name, ok, ms, err in results:
        status = " PASS" if ok else " FAIL"
        time_str = f"{ms:6.1f}ms"
        err_str = "" if ok else f"  {err}"
        print(f"{name:<{name_width}}  {status:>6}  {time_str:>8}{err_str}")
        if ok:
            passed += 1
        else:
            failed += 1

    print()
    print("=" * 64)
    print(f" Results: {passed} passed, {failed} failed (of {len(results)} modules)")
    print("=" * 64)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
