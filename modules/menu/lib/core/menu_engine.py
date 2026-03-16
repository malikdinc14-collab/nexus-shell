#!/usr/bin/env python3
"""
Nexus Menu Engine
=================
YAML-driven, cascading-discovery menu renderer.

Discovery order (later overrides earlier within same context name):
  1. Global:  $NEXUS_HOME/global/<pillar>/
  2. Profile: $NEXUS_HOME/config/profiles/<active_profile>/ (if set)
  3. Project: $PROJECT_ROOT/.nexus/<pillar>/

Output format (consumed by fzf via nexus-menu):
  LABEL<TAB>TYPE<TAB>PAYLOAD
"""

import os
import sys
import yaml
import json
import subprocess
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
NEXUS_HOME    = Path(os.environ.get("NEXUS_HOME", Path(__file__).resolve().parents[4]))
PROJECT_ROOT  = Path(os.environ.get("PROJECT_ROOT", os.getcwd()))
ACTIVE_PROFILE= os.environ.get("NEXUS_PROFILE", "")

# Layers (Cascading Lists)
BUILTIN_LISTS  = NEXUS_HOME / "modules" / "menu" / "lists"
SYSTEM_LISTS   = NEXUS_HOME / "core" / "lists" # New System Layer
USER_CONFIG    = Path(os.path.expanduser("~/.nexus"))
USER_LISTS     = USER_CONFIG / "lists"
PROFILE_LISTS  = USER_CONFIG / "profiles" / ACTIVE_PROFILE / "lists" if ACTIVE_PROFILE else None
PROJECT_LISTS  = PROJECT_ROOT / ".nexus" / "lists"

# ── Output format ─────────────────────────────────────────────────────────────
def fmt(label, e_type, payload, **kwargs):
    """Output metadata-rich JSON for the UI."""
    data = {
        "label": label.strip(),
        "type": e_type,
        "payload": payload,
    }
    data.update(kwargs)
    return json.dumps(data)

# ── Variable expansion ────────────────────────────────────────────────────────
def expand(s):
    if not isinstance(s, str):
        return s
    return os.path.expandvars(s.replace(
        "$NEXUS_HOME", str(NEXUS_HOME)).replace(
        "$PROJECT_ROOT", str(PROJECT_ROOT)))

# ── Discovery Kernel ──────────────────────────────────────────────────────────

def get_list_layers(context: str) -> list[Path]:
    """Return valid directory paths for a context across all layers."""
    # Special handling for explicit layer browsing
    if context.startswith("system:"):
        return [SYSTEM_LISTS / context.replace("system:", "")]
    if context.startswith("global:"):
        return [BUILTIN_LISTS / context.replace("global:", "")]
    if context.startswith("profile:") and PROFILE_LISTS:
        return [PROFILE_LISTS / context.replace("profile:", "")]
    if context.startswith("workspace:"):
        return [PROJECT_LISTS / context.replace("workspace:", "")]
    if context.startswith("user:"):
        return [USER_LISTS / context.replace("user:", "")]

    layers = [SYSTEM_LISTS / context, BUILTIN_LISTS / context, USER_LISTS / context]
    if PROFILE_LISTS:
        layers.append(PROFILE_LISTS / context)
    layers.append(PROJECT_LISTS / context)
    return [l for l in layers if l.exists() and l.is_dir()]

def load_metadata(layers: list[Path]) -> dict:
    """Merge _list.yaml metadata and _shadow exclusion lists across layers."""
    meta = {"_hide": set()}
    for layer in layers:
        # Load Manifest
        m_file = layer / "_list.yaml"
        if m_file.exists():
            try:
                data = yaml.safe_load(m_file.read_text()) or {}
                meta.update(data)
            except:
                pass
        
        # Load Shadow (exclusion list)
        s_file = layer / "_shadow"
        if s_file.exists():
            try:
                for line in s_file.read_text().splitlines():
                    name = line.strip()
                    if name:
                        meta["_hide"].add(name)
            except:
                pass
    return meta

def render_home() -> list:
    """Home is the entry point, merged across layers (Builtin -> Global -> Profile -> Project)."""
    # 1. Identify all home.yaml files
    home_files = [
        NEXUS_HOME / "modules" / "menu" / "config" / "home.yaml",
        USER_CONFIG / "home.yaml",
    ]
    if ACTIVE_PROFILE:
        home_files.append(USER_CONFIG / "profiles" / ACTIVE_PROFILE / "home.yaml")
    home_files.append(PROJECT_ROOT / ".nexus" / "home.yaml")

    with open("/tmp/nexus_menu_debug.log", "a") as f:
        f.write(f"\n[Engine] Home Search: {len(home_files)} locations\n")
        f.write(f"[Engine] Project Root: {PROJECT_ROOT}\n")

    # 2. Pick the Highest Priority home.yaml (Ownership wins for layout)
    winning_hf = None
    for hf in reversed(home_files):
        if hf.exists():
            winning_hf = hf
            break
            
    if not winning_hf:
        with open("/tmp/nexus_menu_debug.log", "a") as f:
            f.write("[Engine] ERROR: No home.yaml found anywhere!\n")
        return [fmt("Error: No home.yaml found", "ERROR", "NONE")]

    with open("/tmp/nexus_menu_debug.log", "a") as f:
        f.write(f"[Engine] Loading: {winning_hf}\n")

    try:
        data = yaml.safe_load(winning_hf.read_text()) or {}
        items = []
        for item in data.get("items", []):
            if item.get("separator"):
                items.append(fmt("──────────────────────────────", "SEPARATOR", "NONE"))
                continue
            
            label = item.get("label", "Unknown")
            e_type = item.get("type", "PLANE")
            payload = expand(item.get("payload", "NONE"))
            
            meta = {k: v for k, v in item.items() if k not in ("label", "type", "payload", "separator")}
            items.append(fmt(label, e_type, payload, **meta))
        
        root_meta = {
            "layout": data.get("layout", "list"),
            "name": data.get("name", "Nexus Hub"),
            "icon": data.get("icon", "🏠"),
            "source": str(winning_hf) # Metadata for the UI identifying the active layer
        }
        if items:
            first = json.loads(items[0])
            first["_root"] = root_meta
            items[0] = json.dumps(first)
        return items
    except Exception as e:
        return [fmt(f"Error loading {winning_hf.name}: {e}", "ERROR", "NONE")]

def get_items(context: str) -> list:
    """The Primary Discovery Dispatcher."""
    if context == "home":
        return render_home()

    # Split context for drill-down (e.g., "notes/personal" or "workspace:notes")
    if ":" in context:
        layer_prefix, _, path_rest = context.partition(":")
        subpath = path_rest
        # If it's just "workspace:", list all root folders in that layer
        if not subpath:
            layer_root = None
            if layer_prefix == "global": layer_root = BUILTIN_LISTS
            if layer_prefix == "profile": layer_root = PROFILE_LISTS
            if layer_prefix == "workspace": layer_root = PROJECT_LISTS
            if layer_prefix == "user": layer_root = USER_LISTS
            
            if layer_root and layer_root.exists():
                items = []
                for f in sorted(layer_root.iterdir()):
                    if f.is_dir() and not f.name.startswith(("_", ".")):
                        items.append(fmt(f.name.capitalize(), "PLANE", f"{layer_prefix}:{f.name}"))
                
                if items:
                    first = json.loads(items[0])
                    # Title based on layer
                    titles = {"global": "Global Lists", "profile": "Personal Profile", "workspace": "Project Workspace"}
                    first["_root"] = {"name": titles.get(layer_prefix, layer_prefix.capitalize()), "layout": "list"}
                    items[0] = json.dumps(first)
                return items
    else:
        parts = context.split("/")
        subpath = "/".join(parts[1:]) if len(parts) > 1 else ""

    layers = get_list_layers(context)
    if not layers and not subpath:
        return [fmt(f"List not found: {context}", "ERROR", "NONE")]

    # Load Metadata (Icons, Layout hints)
    meta = load_metadata(layers)
    items = []
    
    # 1. Discover Children (Folders & Files)
    seen = {}
    shadowed = meta.get("_hide", set())
    for layer in layers:
        for f in sorted(layer.iterdir()):
            if f.name.startswith(("_", ".")): continue # Ignore metadata/hidden
            if f.name in shadowed: continue # Explicit shadow
            
            rel_name = f.name
            if f.is_dir():
                seen[rel_name] = fmt(f"📁 {f.name}/", "FOLDER", f"{context}/{f.name}")
            else:
                # File handling based on extensions
                icon = meta.get("icon", "📄")
                e_type = "ACTION"
                
                if f.suffix == ".md":
                    e_type = "NOTE"
                    icon = meta.get("icon_note", "📝")
                elif f.suffix == ".sh":
                    # Provider Check: If executable, run it
                    if os.access(f, os.X_OK):
                        try:
                            # Run provider and capture its lines
                            env = os.environ.copy()
                            env["NEXUS_HOME"] = str(NEXUS_HOME)
                            env["PROJECT_ROOT"] = str(PROJECT_ROOT)
                            output = subprocess.check_output([str(f)], stderr=subprocess.DEVNULL, env=env).decode().strip()
                            if output:
                                # A provider can return multiple JSON objects or a single list
                                try:
                                    parsed = json.loads(output)
                                    if isinstance(parsed, list):
                                        for p_item in parsed:
                                            seen[f"{f.name}_{json.dumps(p_item)}"] = json.dumps(p_item)
                                    else:
                                        seen[f.name] = output
                                except json.JSONDecodeError:
                                    # Fallback to line by line JSON
                                    for line in output.split("\n"):
                                        seen[f"{f.name}_{line}"] = line
                            continue # Skip adding the script itself
                        except:
                            pass
                    icon = meta.get("icon_script", "🏗️")
                
                seen[rel_name] = fmt(f"{icon} {f.stem}", e_type, str(f))

    items = list(seen.values())

    # 2. Add Root Metadata to first item for TUI
    if items:
        try:
            first = json.loads(items[0])
            first["_root"] = {
                "layout": meta.get("layout", "list"),
                "name": meta.get("name", context.capitalize()),
                "icon": meta.get("icon", "📦")
            }
            items[0] = json.dumps(first)
        except:
            pass

    return items or [fmt(f"Empty: {context}", "DISABLED", "NONE")]

def main():
    context = "home"
    for i, arg in enumerate(sys.argv):
        if arg == "--context" and i + 1 < len(sys.argv):
            context = sys.argv[i + 1].lower()
    
    # Simple CLI fallback if no args
    if len(sys.argv) == 2 and not sys.argv[1].startswith("-"):
        context = sys.argv[1]

    for line in get_items(context):
        print(line)

if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(0)
