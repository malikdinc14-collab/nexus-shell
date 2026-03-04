#!/usr/bin/env python3
"""
Nexus Menu Engine
=================
A clean, YAML-driven menu renderer that replaces the legacy Python pillar system.

It reads menu definitions from three sources (in override order):
  1. Project:  .nexus/lists/*.yaml
  2. Global:   ~/.config/nexus-shell/lists/*.yaml
  3. Built-in: $NEXUS_HOME/menus/*.yaml

Each YAML file defines a context (a named menu screen) with static items
and an optional generator command for dynamic content.

Output format (consumed by FZF via nexus-menu):
  LABEL<TAB>TYPE<TAB>PAYLOAD
"""

import os
import sys
import yaml
import json
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
NEXUS_HOME = Path(os.environ.get("NEXUS_HOME", Path(__file__).resolve().parents[4]))
GLOBAL_LISTS = Path(os.path.expanduser("~/.config/nexus-shell/lists"))
PROJECT_LISTS = Path(os.getcwd()) / ".nexus" / "lists"
BUILTIN_MENUS = NEXUS_HOME / "menus"
REGISTRY_FILE = Path(os.environ.get("NEXUS_REGISTRY",
    str(NEXUS_HOME / "config" / "registry.yaml")))


# ---------------------------------------------------------------------------
# Variable expansion
# ---------------------------------------------------------------------------
def expand(s):
    """Expand $VAR references in a string using environment + known paths."""
    if not isinstance(s, str):
        return s
    replacements = {
        "$NEXUS_HOME": str(NEXUS_HOME),
        "$LIBRARY_ROOT": os.environ.get("PX_LIB_DIR", str(Path.home() / ".parallax" / "content")),
        "$PROJECT_ROOT": os.getcwd(),
    }
    for var, val in replacements.items():
        s = s.replace(var, val)
    return os.path.expandvars(s)


# ---------------------------------------------------------------------------
# YAML Loading
# ---------------------------------------------------------------------------
def load_all_menus():
    """Load all YAML menu definitions into a dict keyed by context name."""
    menus = {}

    # Load in priority order (later overrides earlier)
    for directory in [BUILTIN_MENUS, GLOBAL_LISTS, PROJECT_LISTS]:
        if not directory.exists():
            continue
        for f in sorted(directory.glob("*.yaml")):
            try:
                with open(f, "r") as fh:
                    data = yaml.safe_load(fh)
                if not data:
                    continue
                # Each file can define a context, or defaults to filename stem
                ctx = data.get("context", f.stem)
                menus[ctx] = data
            except Exception:
                pass

    return menus


# ---------------------------------------------------------------------------
# Built-in: Workspaces (from registry)
# ---------------------------------------------------------------------------
def render_workspaces():
    """Read the workspace registry and render project entries."""
    items = []
    items.append(fmt("✨ Register This Workspace", "ACTION",
                     f"echo 'path: {os.getcwd()}' >> {REGISTRY_FILE} && echo 'Registered!'"))

    if REGISTRY_FILE.exists():
        try:
            with open(REGISTRY_FILE, "r") as f:
                data = yaml.safe_load(f)
            projects = data.get("projects", []) if isinstance(data, dict) else []
            for p in projects:
                path = p.get("path", p) if isinstance(p, dict) else str(p)
                name = p.get("name", os.path.basename(path)) if isinstance(p, dict) else os.path.basename(path)
                items.append(fmt(f"📁 {name}", "PLACE", path))
        except Exception:
            items.append(fmt("⚠️ Error reading registry", "DISABLED", "NONE"))
    else:
        items.append(fmt("💡 No workspaces registered yet", "DISABLED", "NONE"))

    return items


# ---------------------------------------------------------------------------
# Built-in: Tools (from modules/ directory)
# ---------------------------------------------------------------------------
def render_tools():
    """Discover installed tool modules from the modules/ directory."""
    items = []
    modules_dir = NEXUS_HOME / "modules"
    if not modules_dir.exists():
        return [fmt("No modules found", "DISABLED", "NONE")]

    for d in sorted(modules_dir.iterdir()):
        if d.is_dir() and d.name != "menu" and not d.name.startswith("."):
            manifest = d / "manifest.json"
            if manifest.exists():
                try:
                    meta = json.loads(manifest.read_text())
                    label = meta.get("name", d.name)
                    cmd = meta.get("command", d.name)
                except Exception:
                    label = d.name
                    cmd = d.name
            else:
                label = d.name.title()
                cmd = d.name
            items.append(fmt(f"🔧 {label}", "ACTION", cmd))

    return items


# ---------------------------------------------------------------------------
# Built-in: Compositions (from compositions/ directory)
# ---------------------------------------------------------------------------
def render_compositions():
    """List available layout compositions."""
    items = []
    comp_dir = NEXUS_HOME / "compositions"
    if not comp_dir.exists():
        return [fmt("No compositions found", "DISABLED", "NONE")]

    for f in sorted(comp_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            name = data.get("name", f.stem)
            desc = data.get("description", "")
        except Exception:
            name = f.stem
            desc = ""
        items.append(fmt(f"🪟 {name}", "ACTION", f"nxs-switch-layout {f.stem}"))

    return items


# ---------------------------------------------------------------------------
# Render a YAML menu context
# ---------------------------------------------------------------------------
def render_yaml_menu(menu_data):
    """Render a YAML menu definition into output lines."""
    items = []

    # Static items
    for item in menu_data.get("items", []):
        if item.get("separator"):
            items.append(fmt("──────────────────────────────", "SEPARATOR", "NONE"))
            continue

        label = item.get("label", "Unknown")
        e_type = item.get("type", "ACTION")
        payload = expand(item.get("payload", "NONE"))

        items.append(fmt(label, e_type, payload))

    # Generator (optional dynamic items)
    gen = menu_data.get("generator")
    if gen:
        gen_cmd = expand(gen.get("command", "")) if isinstance(gen, dict) else expand(gen)
        gen_type = gen.get("type", "ACTION") if isinstance(gen, dict) else "ACTION"
        gen_prefix = gen.get("label_prefix", "") if isinstance(gen, dict) else ""

        try:
            result = subprocess.check_output(gen_cmd, shell=True, stderr=subprocess.DEVNULL, timeout=5).decode().strip()
            for line in result.split("\n"):
                line = line.strip()
                if line:
                    items.append(fmt(f"{gen_prefix}{line}", gen_type, line))
        except Exception:
            pass

    return items


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------
def fmt(label, e_type, payload):
    """Format a single menu item as a tab-delimited string."""
    return f"{label:<40}\t{e_type}\t{payload}"


# ---------------------------------------------------------------------------
# Main entry point (called by px-engine / nexus-menu)
# ---------------------------------------------------------------------------
def main():
    context = "home"
    for i, arg in enumerate(sys.argv):
        if arg == "--context" and i + 1 < len(sys.argv):
            context = sys.argv[i + 1].lower()

    # Built-in contexts
    if context == "home":
        print(fmt("🔧 Tools", "PLANE", "tools"))
        print(fmt("🪟 Compositions", "PLANE", "compositions"))
        print(fmt("📁 Workspaces", "PLANE", "workspaces"))
        print(fmt("📋 Lists", "PLANE", "lists"))
        return

    if context == "workspaces":
        for line in render_workspaces():
            print(line)
        return

    if context == "tools":
        for line in render_tools():
            print(line)
        return

    if context == "compositions":
        for line in render_compositions():
            print(line)
        return

    if context == "lists":
        # Show all available user-defined lists as folders
        for directory in [BUILTIN_MENUS, GLOBAL_LISTS, PROJECT_LISTS]:
            if not directory.exists():
                continue
            scope = "Built-in" if directory == BUILTIN_MENUS else ("Global" if directory == GLOBAL_LISTS else "Project")
            for f in sorted(directory.glob("*.yaml")):
                try:
                    with open(f, "r") as fh:
                        data = yaml.safe_load(fh)
                    title = data.get("title", f.stem) if data else f.stem
                except Exception:
                    title = f.stem
                ctx_name = data.get("context", f.stem) if data else f.stem
                print(fmt(f"📋 {title} [{scope}]", "PLANE", ctx_name))

        if not any(d.exists() for d in [BUILTIN_MENUS, GLOBAL_LISTS, PROJECT_LISTS]):
            print(fmt("💡 No lists found. Add YAML files to .nexus/lists/", "DISABLED", "NONE"))
        return

    # Dynamic YAML contexts
    menus = load_all_menus()
    if context in menus:
        for line in render_yaml_menu(menus[context]):
            print(line)
        return

    # Fallback
    print(fmt(f"Unknown context: {context}", "DISABLED", "NONE"))


if __name__ == "__main__":
    main()
