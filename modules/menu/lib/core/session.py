#!/usr/bin/env python3
"""
Parallax Core Session (The Kernel)
==================================

This module (`lib.core.session`) is the heart of the Parallax system.
It acts as the **"Session Kernel"**, responsible for:

1.  **State Management**: Tracking the current Project, user scope, and active context.
2.  **Configuration Layering**: Merging Global Config (~/.parallax/dashboard.json) with Project Config.
3.  **Event Loop**: Processing UI events (Keybinds, Navigation) from the FZF frontend.
4.  **Plugin Dispatch**: Delegating content rendering to the 7 Pillars (Library, Brains, Places, etc.).

Architecture:
-------------
- **Frontend**: FZF (in `bin/parallax`). It sends events here via CLI args.
- **Kernel**: This file. It decides *what* to show next.
- **Pillars**: Specialized modules in `lib/core/pillars/` that generate the actual lists.
- **Wizard**: A subsystem (`lib/core/wizard.py`) that handles interactive parameter collection.

Usage:
------
Called exclusively by the `bin/parallax` driver or the `bin/px-engine` shim.
"""

import os
import sys
import json
import glob
import time
import datetime
import re
import subprocess
from pathlib import Path

# Add project root to sys.path
# Resolve relative to this file to support both dev and installed mode
CORE_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CORE_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Paths
BIN_DIR = PROJECT_ROOT / "bin"
LIB_EXEC_DIR = PROJECT_ROOT / "lib" / "exec"

HOME = Path.home()

# Isolate Paths (Tiered Environment Architecture)
# Use environment variables injected by Nexus Launcher, or fallback to default ~/.parallax
PARALLAX_HOME = Path(os.environ.get("PX_LIB_DIR", HOME / ".parallax"))
GLOBAL_CONFIG = Path(os.environ.get("PX_CONFIG_DIR", HOME / ".config" / "nexus-shell")) / "settings.yaml"
# Ensure we use isolated state for session files if provided
PX_STATE_DIR = Path(os.environ.get("PX_STATE_DIR", PARALLAX_HOME))
LIBRARY_ROOT = PARALLAX_HOME / "content"
# Import Pillars
from lib.core.pillars import (
    library,
    projects,
    places,
    brains,
    user_lists
)

PILLARS = {
    "library": library,
    "projects": projects,
    "places": places,
    "brains": brains,
    "user_lists": user_lists
}

from lib.core.wizard import WizardManager


def load_configs():
    """Loads and merges Project and Global configurations.

    Resolution Order:
    1. Registry lookup (STEALTH mode) - ~/.parallax/registry.json
    2. .parallax/ in CWD (PROJECT mode)
    3. Global ~/.parallax/ (GLOBAL mode)
    """
    # 1. Start with Empty Baseline
    merged = {"title": "Parallax", "settings": {}, "sections": [], "entities": []}

    # 2. Check Stealth Registry (Keep for backward compat)
    registry_path = PARALLAX_HOME / "registry.json"
    cwd = os.path.realpath(os.getcwd())
    stealth_config = None

    if registry_path.exists():
        try:
            with open(registry_path, "r") as f:
                registry = json.load(f)
            normalized_registry = {os.path.realpath(k): v for k, v in registry.items()}
            check_path = cwd
            while check_path != "/":
                if check_path in normalized_registry:
                    stealth_config = normalized_registry[check_path]
                    break
                check_path = str(Path(check_path).parent)
        except:
            pass

    # 3. Determine scope and load overlay config (The New Model)
    scope = "GLOBAL"
    target = None

    if stealth_config:
        scope = "STEALTH"
        dashboard_path = stealth_config.get("dashboard", "")
        if dashboard_path:
            target = Path(os.path.expanduser(dashboard_path))
    else:
        # Check for local .nexus.yaml (V2) or .parallax/dashboard.json (V1)
        proj_path_v2 = Path(cwd) / ".nexus.yaml"
        proj_path_v1 = Path(cwd) / ".parallax/dashboard.json"
        
        env_path = os.environ.get("PX_DASHBOARD_FILE")
        
        if env_path:
            target = Path(env_path)
        elif proj_path_v2.exists():
            target = proj_path_v2
            scope = "PROJECT"
        elif proj_path_v1.exists():
            target = proj_path_v1
            scope = "PROJECT"

    # 4. Load Global (Base Layer - settings.yaml)
    if GLOBAL_CONFIG.exists():
        try:
            import yaml
            with open(GLOBAL_CONFIG, "r") as f:
                g_cfg = yaml.safe_load(f)
                if g_cfg:
                    # Map new schema to old
                    if "parallax" in g_cfg:
                        merged["settings"]["pillars"] = g_cfg["parallax"].get("pillars", [])
        except:
            pass

    # 5. Load overlay config if exists
    if target and target.exists():
        try:
            if target.name.endswith(".yaml") or target.name.endswith(".yml"):
                import yaml
                with open(target, "r") as f:
                    p_cfg = yaml.safe_load(f)
            else:
                with open(target, "r") as f:
                    p_cfg = json.load(f)
                    
            if p_cfg:
                if "title" in p_cfg:
                    merged["title"] = p_cfg["title"]
                elif "project" in p_cfg:
                    merged["title"] = p_cfg["project"]
                    
                if "parallax" in p_cfg:
                    if "pillars" in p_cfg["parallax"]:
                        merged["settings"]["pillars"] = p_cfg["parallax"]["pillars"]
                        
                # Backwards compat for old schema
                if "settings" in p_cfg:
                    merged["settings"].update(p_cfg["settings"])
                if "sections" in p_cfg:
                    merged["sections"] = p_cfg["sections"] + [
                        s for s in merged["sections"] if s.get("global")
                    ]
                if "entities" in p_cfg:
                    merged["entities"] = p_cfg["entities"]
        except Exception as e:
            with open("/tmp/px-debug.log", "a") as dbg:
                dbg.write(f"Config Load Error: {e}\\n")

    if stealth_config:
        merged["settings"]["stealth_library"] = os.path.expanduser(
            stealth_config.get("library", "")
        )

    merged["settings"]["scope"] = scope
    return merged

def render_item(item):
    """Standardized Delimited Output for the Resident Driver."""
    label = item.get("label", "Unknown")
    e_type = item.get("type", "ACTION")
    payload = ""

    if e_type == "ACTION":
        payload = item.get("path", item.get("action", "NONE"))
    elif "action" in item:
        payload = item.get("path", item["action"])
    elif "place" in item:
        payload = os.path.expanduser(item["place"])
        e_type = "PLACE"
    elif "agent" in item:
        payload = item["agent"]
        e_type = "AGENT"
    elif item.get("type") == "PLANE":
        e_type = "PLANE"
        payload = item.get("payload", "entities")
    elif item.get("type") == "FOLDER":
        e_type = "FOLDER"
        payload = item.get("payload", "")
    elif item.get("type") == "CONTEXT":
        e_type = "CONTEXT"
        payload = item.get("payload", item.get("context", item.get("path", "")))
    elif item.get("type") == "SURFACE":
        e_type = "SURFACE"
        payload = item.get("payload", "")
    elif item.get("type") == "DOC":
        e_type = "DOC"
        payload = item.get("path", item.get("payload", ""))
    elif item.get("type") == "SEPARATOR":
        e_type = "SEPARATOR"
        payload = "NONE"
    elif item.get("type") == "SETTING":
        e_type = "SETTING"
        payload = item.get("action", "")
    elif item.get("type") == "PROMPT_VAL":
        e_type = "PROMPT_VAL"
        payload = item.get("payload", "")
    elif item.get("type") == "PROMPT_INPUT":
        e_type = "PROMPT_INPUT"
        payload = item.get("payload", "")
    else:
        # Catch-all for types that just use payload
        payload = item.get("payload", "NONE")

    return f"{label:<30}\t{e_type}\t{payload}"


def main():
    """
     The Kernel Entry Point (Event Loop).

    This function processes a single "tick" of the Parallax interaction loop.
    It is stateless in execution but stateful in data (relying on /tmp/px-* files).

    Flow:
    1.  **Context Resolution**: Determines where we are (e.g., "actions:git").
    2.  **Configuration**: Loads merged config.
    3.  **Mode Switch**:
        - `--settings`: dumps shell variables.
        - `--ui-event`: handles user interaction (Enter, Esc, Keybinds).
        - Default: Renders the list of items for the current context (Plugin Dispatch).
    """
    # DEBUG
    with open("/tmp/px-debug.log", "a") as dbg:
        import datetime

        dbg.write(f"\\n--- CALL: {datetime.datetime.now()} ---\\n")
        dbg.write(f"ARGS: {sys.argv}\\n")
        dbg.write(f"ENV: PX_SESSION_ID={os.environ.get('PX_SESSION_ID')}\\n")

    context = "entities"
    passed_context = False
    for i, arg in enumerate(sys.argv):
        if arg == "--context" and i + 1 < len(sys.argv):
            context = sys.argv[i + 1].lower()
            passed_context = True

    def get_session_id():
        sid = os.environ.get("PX_SESSION_ID")
        if sid:
            return sid
        ctx_path = os.environ.get("PX_CTX_FILE", "")
        if ctx_path:
            # Extract PID from /tmp/px-ctx-PID.log
            import re

            match = re.search(r"-(\d+)\.log", ctx_path)
            if match:
                return match.group(1)
        return str(os.getpid())

    session_id = get_session_id()
    wizard = WizardManager(session_id, PARALLAX_HOME, BIN_DIR)

    # Auto-load context from environment if not passed args
    if not passed_context:
        ctx_file = os.environ.get("PX_CTX_FILE")
        if ctx_file and os.path.exists(ctx_file):
            try:
                # Use read_text to get content (e.g. "docs" or "docs:subfolder")
                f_ctx = Path(ctx_file).read_text().strip()
                if f_ctx:
                    context = f_ctx
            except:
                pass

    config = load_configs()
    import subprocess

    # 0. Output Mode: Settings
    if "--settings" in sys.argv:
        settings = config.get("settings", {})
        binds = settings.get("keybinds", {})
        for k, v in binds.items():
            print(f"PX_KEY_{k.upper()}='{v}'")
        print(f"PX_SCOPE='{settings.get('scope', 'GLOBAL')}'")
        print(f"PX_PROJECT_NAME='{config.get('title', 'Parallax')}'")
        print(f"PX_KEY_SAVE_SURFACE='{binds.get('save_surface', 'ctrl-w')}'")
        print(f"PX_KEY_INTEL='{binds.get('intel', 'ctrl-i')}'")
        # Tool Configuration
        print(f"PX_TOOL_VIEWER='{settings.get('viewer', 'cat')}'")
        print(
            f"PX_TOOL_EDITOR='{settings.get('editor', os.environ.get('EDITOR', 'vi'))}'"
        )
        return

    # 1. Output Mode: UI Events (The "Display Brain")
    if "--ui-event" in sys.argv:
        # Resolve active context from state if not provided via arg
        ctx_file = os.environ.get("PX_CTX_FILE")
        if context == "entities" and ctx_file and os.path.exists(ctx_file):
            try:
                with open(ctx_file, "r") as f:
                    context = f.read().strip().lower()
            except:
                pass

        event = sys.argv[sys.argv.index("--ui-event") + 1]
        scope = config.get("settings", {}).get("scope", "GLOBAL")

        def run_styler(ctx):
            legend_file = os.environ.get(
                "PX_SHOW_LEGEND_FILE", f"/tmp/px-legend-{session_id}.log"
            )
            show_legend = "true"
            if os.path.exists(legend_file):
                show_legend = Path(legend_file).read_text().strip()

        if event == "legend_toggle":
            ctx_file = os.environ.get("PX_CTX_FILE", f"/tmp/px-ctx-{session_id}.log")
            ctx = (
                Path(ctx_file).read_text().strip()
                if Path(ctx_file).exists()
                else "entities"
            )
            header_lines = build_context(config, ctx.split(":")[0] if ":" in ctx else ctx)
            final_header = "\n".join(header_lines)
            import re
            safe_header = re.sub(r"([()|\"\'])", r"\\\1", final_header)
            print(f"reload(px-engine --context {ctx})+change-header({safe_header})")
            return

        if event == "esc":
            ctx_file = os.environ.get("PX_CTX_FILE", f"/tmp/px-ctx-{session_id}.log")
            ctx = (
                Path(ctx_file).read_text().strip()
                if Path(ctx_file).exists()
                else "entities"
            )

            # Special Case: If in a prompt, return to the stored prompt return context
            if ctx.startswith("prompt-"):
                return_ctx_file = f"/tmp/px-prompt-return-{session_id}.log"
                if os.path.exists(return_ctx_file):
                    parent_ctx = Path(return_ctx_file).read_text().strip()
                    # Clean up
                    os.remove(return_ctx_file)

                    header_lines = build_context(config, parent_ctx.split(":")[0] if ":" in parent_ctx else parent_ctx)
                    final_header = "\n".join(header_lines)
                    import re
                    safe_header = re.sub(r"([()|\"\'])", r"\\\1", final_header)
                    print(
                        f"execute-silent(echo {parent_ctx} > {ctx_file})+reload('{BIN_DIR}/px-engine' --context {parent_ctx})+change-header({safe_header})+clear-query"
                    )
                    return

            # At top level? Exit.
            if ctx == "entities":
                print("abort")
                return

            # Determine parent context and child label
            if ":" in ctx:
                # Nested folder: "actions:git/subdir" -> parent="actions:git", child="subdir"
                # Or: "actions:git" -> parent="actions", child="git"
                parts = ctx.rsplit("/", 1)
                if len(parts) == 2:
                    parent_ctx = parts[0]
                    child_label = parts[1]
                else:
                    # Top-level folder: "actions:git" -> parent="actions", child="git"
                    parent_ctx = ctx.split(":")[0]
                    child_label = ctx.split(":")[1]
            else:
                # Simple plane: go back to entities
                parent_ctx = "entities"
                child_label = ctx.title()

            # Find position in parent context
            pos_file = os.environ.get("PX_POS_FILE", "/tmp/px-pos.log")
            saved_pos_file = f"/tmp/px-pos-{session_id}-{parent_ctx}.log"

            idx = 1
            if os.path.exists(saved_pos_file):
                try:
                    idx = int(Path(saved_pos_file).read_text().strip())
                except:
                    idx = 1
            else:
                # Fallback to hardcoded logic for entities (safety)
                if parent_ctx == "entities":
                    master_index = [
                        "History",
                        "Library",
                        "Agents",
                        "Actions",
                        "Places",
                        "Surfaces",
                        "Docs",
                        "Prompts",
                        "Context",
                        "System",
                    ]
                    for i, m in enumerate(master_index):
                        if child_label.lower() == m.lower():
                            idx = i + 1
                            break

            # Write target position for the result event
            with open(pos_file, "w") as f:
                f.write(str(idx))

            header = run_styler(
                parent_ctx.split(":")[0] if ":" in parent_ctx else parent_ctx
            )
            print(
                f"execute-silent(echo {parent_ctx} > {ctx_file})+reload(px-engine --context {parent_ctx})+change-header({header})+clear-query"
            )
            return

        if event == "enter":
            # Payload is {} from FZF
            raw_selection = sys.argv[-1]
            ctx_file = os.environ.get("PX_CTX_FILE", f"/tmp/px-ctx-{session_id}.log")
            ctx = (
                Path(ctx_file).read_text().strip()
                if Path(ctx_file).exists()
                else "entities"
            )

            # 1. Sanitize Selection (Strip FZF artifacts)
            raw_selection = raw_selection.strip().strip("'").strip('"')

            # Handle empty selection (e.g., user types answer and hits Enter, filtering out matches)
            if not raw_selection:
                if ctx.startswith("prompt-"):
                    query = os.environ.get("FZF_QUERY", "")
                    print(wizard.process_query(ctx, query))
                    return
                else:
                    # Not in a prompt, ignore empty enter
                    return

            # 2. Parse Parts
            parts = [p.strip() for p in raw_selection.split("\t")]

            if len(parts) < 3:
                # Log invalid selection
                with open("/tmp/px-debug.log", "a") as f:
                    f.write(f"INVALID SELECTION: {raw_selection}\\n")
                return

            label, e_type, payload = (
                parts[0],
                parts[1],
                "\t".join(parts[2:]).strip().strip("'").strip('"'),
            )

            # Log Parsed Decision
            with open("/tmp/px-debug.log", "a") as f:
                f.write(f"PARSED: [{e_type}] -> Payload: {payload}\\n")

            ctx_file = os.environ.get("PX_CTX_FILE", f"/tmp/px-ctx-{session_id}.log")

            if e_type == "PLANE":
                header_lines = build_context(config, payload)
                final_header = "\\n".join(header_lines)
                import re
                safe_header = re.sub(r"([()|\"\\'])", r"\\\\\\1", final_header)
                print(
                    f"execute-silent(echo {payload} > {ctx_file})+reload(px-engine --context {payload})+change-header({safe_header})+clear-query"
                )
            elif e_type == "FOLDER":
                # Navigate into folder (e.g., actions:git)
                parent_plane = payload.split(":")[0]
                header_lines = build_context(config, parent_plane)
                final_header = "\\n".join(header_lines)
                import re
                safe_header = re.sub(r"([()|\"\\'])", r"\\\\\\1", final_header)
                print(
                    f"execute-silent(echo {payload} > {ctx_file})+reload(px-engine --context {payload})+change-header({safe_header})+clear-query"
                )
            elif e_type == "PROMPT_VAL" or e_type == "PROMPT_INPUT":
                # Delegate to Wizard Manager inline parsing
                print(wizard.process_input(payload, label))
            elif e_type == "SETTING":
                # Settings usually want to reload the UI or restart
                print(f"reload(px-engine --context settings)")
            else:
                # ---------------------------------------------------------
                # NEW ROUTER ARCHITECTURE
                # ---------------------------------------------------------
                # Any execution type (ACTION, PLACE, NOTE, MODEL, AGENT) 
                # is no longer handled internally. We drop out of FZF and 
                # let the stdout be caught by the nexus-router.
                
                # Check if it requires a wizard parameter collection first
                if e_type == "ACTION":
                    params = wizard.init_wizard(payload, context)
                    if params:
                        p = params[0]
                        desc, var = p["desc"], p["var"]
                        import re
                        safe_desc = re.sub(r"([()|\"\\'])", r"\\\\\\1", desc)
                        header = f"PARALLAX │ INPUT │ {safe_desc} ({var.upper()})"
                        cmd = f"execute-silent(echo 'prompt-0' > {ctx_file})+reload('{BIN_DIR}/px-engine' --context 'prompt-0')+change-header({header})+change-prompt(Input > )+clear-query"
                        print(cmd)
                        return

                # Print to STDOUT: The menu wrapper script parses this.
                print(f"{e_type}|{payload}")
        elif event == "TOGGLE_DASHBOARD":
            # Toggle between normal dashboard and custom dashboard
            try:
                # Get the current dashboard mode
                state_dir = os.path.expanduser("~/.parallax/state")
                mode_file = os.path.join(state_dir, ".dashboard_mode")

                # Create state directory if it doesn't exist
                os.makedirs(state_dir, exist_ok=True)

                current_mode = "normal"
                if os.path.exists(mode_file):
                    with open(mode_file, "r") as f:
                        current_mode = f.read().strip()

                # Toggle the mode
                new_mode = "custom" if current_mode == "normal" else "normal"
                with open(mode_file, "w") as f:
                    f.write(new_mode)

                # Determine which dashboard to switch to
                dashboard_type = (
                    "custom-dashboard" if new_mode == "custom" else "dashboard"
                )

                # Reload with the appropriate dashboard
                print(f"reload(px-engine --context {dashboard_type})")
            except Exception as e:
                # Fallback to custom dashboard if there's an error
                print("reload(px-engine --context custom-dashboard)")
            return
        return

    output = []

    # ---------------------------------------------------------
    # DYNAMIC DISPATCH (PLUGIN ARCHITECTURE)
    # ---------------------------------------------------------

    # 1. Master Index (Kernel Level)
    if context.startswith("prompt-"):
        idx = int(context.split("-")[1])
        output = wizard.render_prompt(idx)
    elif context == "entities":
        scope = config.get("settings", {}).get("scope", "GLOBAL")

        # Project Dashboard (when inside a registered workspace)
        if scope in ["PROJECT", "STEALTH"]:
            project_name = config.get("title", "Project")
            # Show custom entities from project config, or default project menu
            if config.get("entities"):
                output.extend(config["entities"])
            else:
                output.append(
                    {
                        "label": f"📁 {project_name}",
                        "type": "FOLDER",
                        "payload": "project:home",
                    }
                )
                output.append(
                    {
                        "label": "🤖 Project Agents",
                        "type": "FOLDER",
                        "payload": "project:agents",
                    }
                )
                output.append(
                    {"label": "📚 Library", "type": "PLANE", "payload": "library"}
                )
                output.append(
                    {"label": "🧠 Brains", "type": "PLANE", "payload": "brains"}
                )
                output.append(
                    {"label": "✅ Workflow", "type": "PLANE", "payload": "workflow"}
                )
                output.append(
                    {
                        "label": "⚙️  Settings",
                        "type": "FOLDER",
                        "payload": "project:settings",
                    }
                )
                output.append(
                    {"label": "🚀 Projects", "type": "PLANE", "payload": "projects"}
                )
                output.append(
                    {
                        "label": "🔙 Global Dashboard",
                        "type": "PLANE",
                        "payload": "global",
                    }
                )
        else:
            # Global Dashboard
            output.append(
                {"label": "📊 Nexus Dashboard", "type": "PLANE", "payload": "nexus"}
            )
            output.append(
                {"label": "🚀 Projects", "type": "PLANE", "payload": "projects"}
            )
            output.append(
                {"label": "📚 Library", "type": "PLANE", "payload": "library"}
            )
            output.append({"label": "🧠 Brains", "type": "PLANE", "payload": "brains"})
            output.append(
                {"label": "✅ Workflow", "type": "PLANE", "payload": "workflow"}
            )
            output.append(
                {"label": "------------------------------", "type": "SEPARATOR"}
            )
            output.append(
                {
                    "label": "🖥️  Workspace (Alt+O)",
                    "type": "ACTION",
                    "path": "execute(tmux select-window -t :0)",
                }
            )
            output.append(
                {
                    "label": "📋 Planning (Alt+W)",
                    "type": "ACTION",
                    "path": "execute(tmux select-window -t :1)",
                }
            )
            output.append(
                {
                    "label": "📊 Monitor (Alt+M)",
                    "type": "ACTION",
                    "path": "execute(tmux select-window -t :2)",
                }
            )
            output.append(
                {
                    "label": "🐚 Shells (Alt+S)",
                    "type": "ACTION",
                    "path": "execute(tmux select-window -t :3)",
                }
            )
            output.append(
                {
                    "label": "🪟 Open New Tab (Spawn)",
                    "type": "FOLDER",
                    "payload": "system:spawn",
                }
            )
            output.append(
                {"label": "------------------------------", "type": "SEPARATOR"}
            )
            output.append({"label": "🏙️  Places", "type": "PLANE", "payload": "places"})

            output.append({"label": "⚙️  System", "type": "PLANE", "payload": "system"})

    # Inline handlers for simple contexts without full plugins
    elif context == "surfaces":
        # Future: Show saved tmux layouts and surfaces
        output.append(
            {
                "label": "🚧 Surfaces (Coming Soon)",
                "type": "DISABLED",
                "payload": "NONE",
            }
        )
        output.append(
            {
                "label": "💡 Save current layout with 'px-surface save NAME'",
                "type": "SEPARATOR",
                "payload": "NONE",
            }
        )

    elif context == "contexts":
        # Scan for staged context files
        ctx_dir = PARALLAX_HOME / "contexts"
        if ctx_dir.exists():
            for f in sorted(ctx_dir.glob("*.yaml")):
                output.append({"label": f"📄 {f.stem}", "type": "DOC", "path": str(f)})
        if not output:
            output.append(
                {
                    "label": "No staged contexts found",
                    "type": "SEPARATOR",
                    "payload": "NONE",
                }
            )

    # Project-specific handlers
    elif context == "project:home":
        # Show project sections from dashboard.json
        for section in config.get("sections", []):
            output.append(
                {
                    "label": f"📂 {section.get('name', 'Section')}",
                    "type": "FOLDER",
                    "payload": f"section:{section.get('name', '')}",
                }
            )
        if not output:
            output.append(
                {"label": "💡 Add sections to your dashboard.json", "type": "DISABLED"}
            )

    elif context == "project:agents":
        # Scan for project-local agent configs
        cwd = os.getcwd()
        agents_dirs = [
            os.path.join(cwd, ".parallax", "agents"),
            os.path.join(cwd, "library", "agents"),
        ]
        for agents_dir in agents_dirs:
            if os.path.exists(agents_dir):
                for agent in sorted(os.listdir(agents_dir)):
                    agent_path = os.path.join(agents_dir, agent)
                    if os.path.isdir(agent_path):
                        output.append(
                            {
                                "label": f"🤖 {agent}",
                                "type": "AGENT",
                                "payload": agent_path,
                            }
                        )
        if not output:
            output.append({"label": "No project agents found", "type": "DISABLED"})
            output.append(
                {
                    "label": "✨ Create Agent",
                    "type": "ACTION",
                    "path": f"{BIN_DIR}/../content/actions/factory/create-persona.sh",
                }
            )

    elif context == "project:settings":
        cwd = os.getcwd()
        output.append(
            {
                "label": "📝 Edit Dashboard Config",
                "type": "ACTION",
                "path": f"${{EDITOR:-vi}} {cwd}/.parallax/dashboard.json",
            }
        )
        output.append(
            {
                "label": "📂 Open .parallax Folder",
                "type": "PLACE",
                "payload": f"{cwd}/.parallax",
            }
        )

    elif context == "global":
        # Force global dashboard view
        output.append({"label": "🚀 Projects", "type": "PLANE", "payload": "projects"})
        output.append({"label": "📚 Library", "type": "PLANE", "payload": "library"})
        output.append({"label": "🧠 Brains", "type": "PLANE", "payload": "brains"})
        output.append({"label": "🏙️  Places", "type": "PLANE", "payload": "places"})
        output.append({"label": "⚙️  System", "type": "PLANE", "payload": "system"})

    # 2. Plugin Dispatch
    else:
        paths_map = {
            "BIN_DIR": str(BIN_DIR),
            "LIBRARY_ROOT": str(LIBRARY_ROOT),
            "GLOBAL_CONFIG": str(GLOBAL_CONFIG),
            "LOCAL_LIBRARY": str(Path(os.getcwd()) / ".parallax" / "library")
            if (Path(os.getcwd()) / ".parallax").exists()
            else None,
            "LOCAL_ACTIONS": str(Path(os.getcwd()) / ".parallax" / "actions")
            if (Path(os.getcwd()) / ".parallax").exists()
            else None,
        }

        # Order matters only if contexts overlap (they shouldn't)
        # We check imported plugins
        plugins = []
        if "projects" in globals():
            plugins.append(projects)
        if "library" in globals():
            plugins.append(library)
        if "places" in globals():
            plugins.append(places)
        if "brains" in globals():
            plugins.append(brains)
        if "ghosts" in globals():
            plugins.append(ghosts)
        if "control" in globals():
            plugins.append(control)
        if "history" in globals():
            plugins.append(history)
        if "workflow" in globals():
            plugins.append(workflow)
        if "nexus" in globals():
            res = nexus.render(context, config, paths_map)
            if res is not None:
                output.extend(res)
                consumed = True

        consumed = False
        for plugin in plugins:
            try:
                result = plugin.render(context, config, paths_map)
                if result is not None:
                    output.extend(result)
                    consumed = True
                    break
            except Exception as e:
                # Fail gracefully for plugins
                output.append(
                    {
                        "label": f"[KERNEL ERROR] Plugin {plugin} failed: {e}",
                        "type": "DISABLED",
                    }
                )

        # 3. Fallbacks
        if not consumed:
            # Check for section: prefix
            if context.startswith("section:"):
                target_section = context.split(":", 1)[1]
                for section in config.get("sections", []):
                    if section.get("name", "").lower() == target_section.lower():
                        output.extend(section.get("items", []))
                        consumed = True
                        break

            if not consumed:
                # Standard Dashboard Section View (Config Fallthrough)
                for section in config.get("sections", []):
                    # Map context name to dashboard key (e.g. 'agents' -> 'agent')
                    key_map = {
                        "agents": "agent",
                        "actions": "action",
                        "places": "place",
                        "docs": "doc",
                        "agents": "agent",
                        "contexts": "context",
                    }
                    target_key = key_map.get(context)
                    if target_key:
                        output.extend(
                            [it for it in section.get("items", []) if target_key in it]
                        )
                    elif context == "library":
                        output.extend(section.get("items", []))
                    else:
                        # Generic dump for unknown contexts if configured
                        pass

    # 7. Inspection and Source Resolution (Internal Utility)
    if "--inspect" in sys.argv or "--source" in sys.argv:
        target_payload = sys.argv[-1]
        if not target_payload or not target_payload.strip():
            return
        for item in output:
            line = render_item(item)
            if target_payload in line:
                if "--source" in sys.argv:
                    if item.get("path"):
                        print(item["path"])
                    elif item.get("context"):
                        print(item["context"])
                    elif item.get("place"):
                        print(item["place"])
                else:
                    print(json.dumps(item, indent=2))
                return
        return

    # 4. Standard Render Loop
    for item in output:
        print(render_item(item))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback

        with open("/tmp/px-crash.log", "w") as f:
            f.write(traceback.format_exc())
        sys.exit(1)
