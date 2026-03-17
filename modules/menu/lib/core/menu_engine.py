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

def render_tool_selector(role: str) -> list:
    """List available tools for a role so the user can 'Set Default'."""
    catalog_path = NEXUS_HOME / "core" / "api" / "tool_catalog.yaml"
    items = []
    
    tools = []
    if catalog_path.exists():
        try:
            catalog = yaml.safe_load(catalog_path.read_text()) or {}
            tools = catalog.get(role, [])
        except:
            pass
            
    if not tools:
        # Fallback to current only
        from module_registry import resolve_role
        current = resolve_role(role)
        tools = [{"label": f"Current: {current}", "cmd": current}]

    for t in tools:
        # payload format for SET_DEFAULT: role|command
        payload = f"{role}|{t['cmd']}"
        items.append(fmt(t["label"], "SET_DEFAULT", payload, icon="🛠️", description=f"Set as default {role}"))
    
    if items:
        first = json.loads(items[0])
        first["_root"] = {"name": f"Select Default {role.capitalize()}", "layout": "list"}
        items[0] = json.dumps(first)
        
    return items

# ── Dynamic Source Kernel ──────────────────────────────────────────────────

def load_lists_config() -> dict:
    """Merge lists.yaml across layers (Global -> Profile -> Workspace)."""
    locations = [
        NEXUS_HOME / "config" / "lists.yaml",
        USER_CONFIG / "lists.yaml",
    ]
    if ACTIVE_PROFILE:
        locations.append(USER_CONFIG / "profiles" / ACTIVE_PROFILE / "lists.yaml")
    locations.append(PROJECT_ROOT / ".nexus" / "lists.yaml")

    config = {}
    for loc in locations:
        if loc.exists():
            try:
                data = yaml.safe_load(loc.read_text()) or {}
                for key, val in data.items():
                    if key not in config or val.get("policy") == "override":
                        config[key] = val
                    else:
                        # Aggregate sources
                        existing_sources = config[key].get("sources", [])
                        new_sources = val.get("sources", [])
                        config[key]["sources"] = existing_sources + new_sources
            except Exception as e:
                # Axiom: Noise on config error
                print(f"DEBUG: Error loading {loc}: {e}", file=sys.stderr)
    return config

def resolve_sources(context: str, config: dict) -> list:
    """Resolve a context into a list of normalized source dictionaries."""
    if context in config:
        return config[context].get("sources", [])
    
    # Tiered Fallback: models:local:ssd -> models:local -> models
    parts = context.split(":")
    for i in range(len(parts) - 1, 0, -1):
        parent_context = ":".join(parts[:i])
        if parent_context in config:
            return config[parent_context].get("sources", [])

    # Fallback to legacy directory-based discovery
    layers = get_list_layers(context)
    return [{"type": "directory", "path": str(l)} for l in layers]

def get_items(context: str) -> list:
    """The Primary Discovery Dispatcher (V4)."""
    if context == "home":
        return render_home()

    if context.startswith("set_default:"):
        role = context.partition(":")[2]
        return render_tool_selector(role)

    config = load_lists_config()
    sources = resolve_sources(context, config)
    
    # Metadata for the list itself (layout, name)
    list_meta = config.get(context, {})
    
    items = []
    seen_labels = set()

    for src in sources:
        s_type = src.get("type", "directory")
        s_path = expand(src.get("path", ""))
        if not s_path: continue
        
        path_obj = Path(s_path)
        if s_type == "directory" and path_obj.exists() and path_obj.is_dir():
            # Load directory items
            # Merge logic for directory items
            meta_file = path_obj / "_list.yaml"
            dir_meta = {}
            if meta_file.exists():
                try: dir_meta = yaml.safe_load(meta_file.read_text()) or {}
                except: pass
            
            for f in sorted(path_obj.iterdir()):
                if f.name.startswith(("_", ".")): continue
                
                label = f.stem
                e_type = "ACTION"
                icon = list_meta.get("icon", dir_meta.get("icon", "📄"))
                
                if f.suffix == ".md":
                    e_type = "NOTE"
                    icon = "📝"
                elif f.suffix == ".sh":
                    if os.access(f, os.X_OK):
                        # Script Provider logic (Fail-Fast)
                        try:
                            env = os.environ.copy()
                            env["NEXUS_HOME"] = str(NEXUS_HOME)
                            env["PROJECT_ROOT"] = str(PROJECT_ROOT)
                            output = subprocess.check_output([str(f), context], 
                                                           stderr=subprocess.PIPE, 
                                                           env=env,
                                                           timeout=5).decode().strip()
                            if output:
                                lines = output.splitlines()
                                for line in lines:
                                    line = line.strip()
                                    if not line: continue
                                    # Axiom: Deterministic Protocol
                                    if line.startswith("{"):
                                        try:
                                            pi = json.loads(line)
                                            if isinstance(pi, dict):
                                                pi["source_path"] = str(f)
                                                items.append(json.dumps(pi))
                                            else:
                                                items.append(fmt(str(pi), "ACTION", str(pi), source_path=str(f)))
                                        except json.JSONDecodeError:
                                            items.append(fmt(f"Malformed JSON: {line[:30]}...", "ERROR", "NONE", source_path=str(f)))
                                    else:
                                        # Non-JSON: Try TSV parsing
                                        parts = line.split("\t")
                                        if len(parts) >= 3:
                                            items.append(fmt(parts[0], parts[1], parts[2], source_path=str(f)))
                                        else:
                                            items.append(fmt(line, "ACTION", line, source_path=str(f)))
                            continue
                        except Exception as e:
                            items.append(fmt(f"Error in {f.name}: {str(e)}", "ERROR", "NONE", source_path=str(f)))
                            continue
                    icon = "🏗️"
                
                items.append(fmt(label, e_type, str(f), icon=icon, source_path=str(f)))

        elif s_type == "yaml" and path_obj.exists():
            try:
                data = yaml.safe_load(path_obj.read_text()) or {}
                for item in data.get("items", []):
                    item["source_path"] = str(path_obj)
                    items.append(json.dumps(item))
            except Exception as e:
                items.append(fmt(f"Error in {path_obj.name}: {str(e)}", "ERROR", "NONE", source_path=str(path_obj)))

        elif s_type == "script" and path_obj.exists():
            if os.access(path_obj, os.X_OK):
                try:
                    env = os.environ.copy()
                    env["NEXUS_HOME"] = str(NEXUS_HOME)
                    env["PROJECT_ROOT"] = str(PROJECT_ROOT)
                    output = subprocess.check_output([str(path_obj), context], 
                                                   stderr=subprocess.PIPE, 
                                                   env=env,
                                                   timeout=5).decode().strip()
                    if output:
                        for line in output.splitlines():
                            line = line.strip()
                            if not line: continue
                            
                            # Axiom: Deterministic Protocol
                            if line.startswith("{"):
                                try:
                                    pi = json.loads(line)
                                    if isinstance(pi, dict):
                                        pi["source_path"] = str(path_obj)
                                        items.append(json.dumps(pi))
                                    else:
                                        items.append(fmt(str(pi), "ACTION", str(pi), source_path=str(path_obj)))
                                except json.JSONDecodeError:
                                    items.append(fmt(f"Malformed JSON: {line[:30]}...", "ERROR", "NONE", source_path=str(path_obj)))
                            else:
                                # Non-JSON: Try TSV parsing
                                parts = line.split("\t")
                                if len(parts) >= 3:
                                    items.append(fmt(parts[0], parts[1], parts[2], source_path=str(path_obj)))
                                else:
                                    items.append(fmt(line, "ACTION", line, source_path=str(path_obj)))
                except Exception as e:
                    items.append(fmt(f"Error in {path_obj.name}: {str(e)}", "ERROR", "NONE", source_path=str(path_obj)))
            else:
                items.append(fmt(f"Script not executable: {path_obj.name}", "ERROR", "NONE", source_path=str(path_obj)))

    # Add Root Metadata to first item for TUI
    if items:
        try:
            first = json.loads(items[0])
            first["_root"] = {
                "layout": list_meta.get("layout", "list"),
                "name": list_meta.get("name", context.capitalize()),
                "icon": list_meta.get("icon", "📦")
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
