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
import threading
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
NEXUS_HOME    = Path(os.environ.get("NEXUS_HOME", Path(__file__).resolve().parents[4]))
PROJECT_ROOT  = Path(os.environ.get("PROJECT_ROOT", os.getcwd()))
ACTIVE_PROFILE= os.environ.get("NEXUS_PROFILE", "")

# ── Axiom: Environmental Invariants (Negative Space) ──────────────────────────
def validate_invariants():
    pass  # Warnings logged to debug file only, not stderr

# Add core to sys.path for library access
sys.path.append(str(NEXUS_HOME / "core"))
validate_invariants()

# Layers (Cascading Lists)
BUILTIN_LISTS  = NEXUS_HOME / "modules" / "menu" / "lists"
SYSTEM_LISTS   = NEXUS_HOME / "core" / "engine" / "lists" # New System Layer
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
        try:
            from module_registry import resolve_role
            current = resolve_role(role)
        except ImportError:
            current = role
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

def render_global_tabs() -> list:
    """List all stacks in the session for cross-stack navigation."""
    from engine.lib.daemon_client import NexusDaemonClient
    cl = NexusDaemonClient()
    res = cl.get_state()
    
    if res.get("status") != "ok":
        return [fmt("Daemon unavailable", "ERROR", "NONE")]
    
    # Axiom: Transition to UUID Registry navigation
    state = res.get("data", {})
    registry = state.get("stacks", {})
    items = []
    
    for sid, stack_data in registry.items():
        role = stack_data.get("role")
        tabs = stack_data.get("tabs", [])
        active_idx = stack_data.get("active_index", 0)
        active_tab_name = tabs[active_idx]["name"] if tabs else "Empty"
        
        # Priority label: Role if exists, else shorthand SID
        header = role if role else f"Stack: {sid[:8]}"
        description = f"Active: {active_tab_name} ({len(tabs)} tabs)"
        
        # Payload points to a drill-down context for this specific stack (identity-first)
        payload = f"system:stacks:{role if role else sid}"
        items.append(fmt(header, "FOLDER", payload, icon="🗂️", description=description))
    
    if items:
        first = json.loads(items[0])
        first["_root"] = {"name": "Global Registry (Stacks)", "layout": "list", "icon": "🗂️"}
        items[0] = json.dumps(first)
        
    return items or [fmt("No active stacks", "INFO", "NONE")]

def render_modules() -> list:
    """List all available modules (capabilities) from the registry."""
    from engine.capabilities.registry import CapabilityRegistry
    
    profile_path = Path(os.path.expanduser("~/.nexus/profile.yaml"))
    reg = CapabilityRegistry(profile_path)
    
    items = []
    
    # Core Capabilities
    roles = [
        ("AI Chat", "chat", "💬"),
        ("Editor", "editor", "📝"),
        ("Explorer", "explorer", "📁"),
        ("Terminal", "terminal", "🖥️")
    ]
    
    for label, role, icon in roles:
        cmd = reg.get_tool_for_role(role)
        # Payload for identity-first stack push
        payload = f"$NEXUS_HOME/core/kernel/stack/stack push {role} '{cmd}' '{label}'"
        items.append(fmt(label, "ACTION", payload, icon=icon, description=f"Module: {role} via {cmd}"))

    if items:
        first = json.loads(items[0])
        first["_root"] = {"name": "Modules (Capabilities)", "layout": "list", "icon": "🛠️"}
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
            except:
                pass
    return config
def get_adapter():
    """Resolve the picker adapter from the Capability Registry."""
    sys.path.append(str(NEXUS_HOME))
    from core.engine.capabilities.registry import REGISTRY
    from core.engine.capabilities.base import CapabilityType
    
    profile_path = Path(os.path.expanduser("~/.nexus/profile.yaml"))
    provider = "fzf"
    
    if profile_path.exists():
        try:
            with open(profile_path) as f:
                data = yaml.safe_load(f) or {}
                provider = data.get("preferences", {}).get("menu_provider", "textual")
        except:
            pass
            
    # Try to get the specific requested one
    capabilities = REGISTRY.list_all(CapabilityType.MENU)
    for cap in capabilities:
        if cap.capability_id == provider and cap.is_available():
            return cap
            
    # Fallback to the best available
    return REGISTRY.get_best(CapabilityType.MENU)

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

    if context == "system:tabs:global":
        return render_global_tabs()
    
    if context == "system:modules:all":
        return render_modules()

    if context.startswith("set_default:"):
        role = context.partition(":")[2]
        return render_tool_selector(role)

    if context.startswith("system:stacks:"):
        identity = context.replace("system:stacks:", "")
        try:
            from engine.lib.daemon_client import NexusDaemonClient
            cl = NexusDaemonClient()
            res = cl.get_state()
            if res.get("status") == "ok":
                state = res.get("data", {})
                registry = state.get("stacks", {})
                
                # Resolve identity to SID
                sid, stack = None, None
                if identity in registry:
                    sid, stack = identity, registry[identity]
                else:
                    for s, d in registry.items():
                        if d.get("role") == identity:
                            sid, stack = s, d; break
                
                if stack:
                    items = []
                    active_idx = stack.get("active_index", 0)
                    for i, tab in enumerate(stack["tabs"]):
                        marker = " ●" if i == active_idx else ""
                        label = f"[{i}] {tab['name']}{marker}"
                        payload = f"{identity}|{i}"
                        items.append(fmt(label, "STACK_TAB", payload, icon="🗂️"))
                    return items
            return [fmt("No tabs in this stack", "INFO", "NONE")]
        except:
            return [fmt("Daemon unavailable", "ERROR", "NONE")]

    if context == "local_stack":
        # Resolve identity of the focused pane to show its specific cards
        try:
            # Call stack tool to resolve role/id
            stack_bin = NEXUS_HOME / "core" / "kernel" / "stack" / "stack"
            role = subprocess.check_output([str(stack_bin), "resolve", "local"]).decode().strip()
            return get_items(f"system:stacks:{role}")
        except:
            return [fmt("Error resolving local stack", "ERROR", "NONE")]

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
    initial_context = "home"
    is_interactive = False
    exit_on_select = False

    for i, arg in enumerate(sys.argv):
        if arg == "--context" and i + 1 < len(sys.argv):
            initial_context = sys.argv[i + 1]
        if arg == "--pick":
            is_interactive = True
        if arg == "--exit-on-select":
            exit_on_select = True

    if len(sys.argv) == 2 and not sys.argv[1].startswith("-"):
        initial_context = sys.argv[1]

    if not is_interactive:
        items = get_items(initial_context)
        for line in items:
            print(line)
        return

    # Interactive Loop — Esc returns to home, never exits
    adapter = get_adapter()

    # ── Negative Space: Assert adapter invariants ──
    assert adapter is not None, \
        f"[INVARIANT] Menu adapter resolved to None. " \
        f"Profile: {Path(os.path.expanduser('~/.nexus/profile.yaml'))}, " \
        f"NEXUS_HOME: {NEXUS_HOME}, " \
        f"Available adapters: check CapabilityRegistry"

    import shutil
    if hasattr(adapter, 'capability_id') and adapter.capability_id == 'gum':
        assert shutil.which("gum") is not None, \
            f"[INVARIANT] Adapter is 'gum' but gum binary not found in PATH. " \
            f"PATH: {os.environ.get('PATH', 'unset')}"

    context = initial_context
    history = []  # stack for back-navigation

    while True:
        items = get_items(context)

        # ── Negative Space: Assert items resolved ──
        assert items is not None and len(items) > 0, \
            f"[INVARIANT] get_items('{context}') returned empty. " \
            f"Layers checked: {get_list_layers(context) if context != 'home' else 'home.yaml cascade'}"

        selected_json_str = adapter.pick(context, items)

        if not selected_json_str:
            # Esc pressed — go back or return to home
            if history:
                context = history.pop()
            else:
                context = "home"
            continue

        selected = json.loads(selected_json_str)
        e_type = selected.get("type")
        payload = selected.get("payload")

        if e_type in ("FOLDER", "PLANE"):
            history.append(context)
            context = payload
        elif e_type == "STACK_TAB":
            # Tab switcher: switch to selected tab, then kill menu pane.
            # Must use respawn-pane to prevent the push wrapper's
            # "stack switch identity 0" from undoing the user's selection.
            role, idx = payload.split("|", 1)
            sys.path.insert(0, str(NEXUS_HOME / "core"))
            from engine.actions.resolver import AdapterResolver
            mux = AdapterResolver.multiplexer()
            pane_id = mux.get_focused_pane_id()
            stack_bin = str(NEXUS_HOME / "core" / "kernel" / "stack" / "stack")
            # respawn-pane kills our process tree (wrapper included),
            # runs switch (ghost_swap moves menu to reservoir), then kills menu pane
            switch_and_cleanup = (
                f"{sys.executable} {stack_bin} switch {role} {idx}; "
                f"{sys.executable} -c \"from engine.actions.resolver import AdapterResolver; "
                f"AdapterResolver.multiplexer().kill_pane('{pane_id}')\""
            )
            mux.respawn_pane(pane_id, switch_and_cleanup)
            return
        elif exit_on_select:
            # New Tab mode: respawn this pane with the selected module.
            # Payload format: "$NEXUS_HOME/core/kernel/stack/stack push ROLE 'CMD' 'LABEL'"
            expanded = os.path.expandvars(payload) if payload else ""
            import shlex
            try:
                parts = shlex.split(expanded)
                if "push" in parts:
                    push_idx = parts.index("push")
                    module_cmd = parts[push_idx + 2] if len(parts) > push_idx + 2 else ""
                    module_label = parts[push_idx + 3] if len(parts) > push_idx + 3 else "Tab"
                else:
                    module_cmd = expanded
                    module_label = "Tab"
            except Exception:
                module_cmd = expanded
                module_label = "Tab"

            if module_cmd:
                sys.path.insert(0, str(NEXUS_HOME / "core"))
                from engine.actions.resolver import AdapterResolver
                mux = AdapterResolver.multiplexer()
                pane_id = mux.get_focused_pane_id()
                # Update tab name in daemon registry
                try:
                    sys.path.append(str(NEXUS_HOME / "core" / "engine" / "lib"))
                    from daemon_client import NexusDaemonClient
                    dc = NexusDaemonClient()
                    dc.send("stack_rename_tab", {"pane_id": pane_id, "name": module_label})
                except Exception:
                    pass
                # respawn-pane replaces our process with the module
                mux.respawn_pane(pane_id, module_cmd)
            return
        else:
            # Dispatch action, then return to current context
            dispatch_bin = NEXUS_HOME / "modules" / "menu" / "bin" / "action-dispatch"
            env = os.environ.copy()
            env["NXS_CALLER"] = "menu"
            try:
                subprocess.run(
                    [str(dispatch_bin), "run", e_type, payload],
                    env=env, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(0)
