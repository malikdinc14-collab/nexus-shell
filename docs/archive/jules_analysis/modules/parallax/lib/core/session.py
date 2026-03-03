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
PARALLAX_HOME = HOME / ".parallax"
GLOBAL_CONFIG = PARALLAX_HOME / "dashboard.json"
LIBRARY_ROOT = PARALLAX_HOME / "content"

# Import Pillars
from lib.core.pillars import (
    library,
    places,
    brains,
    ghosts,
    control,
    history,
    projects,
    workflow,
    nexus,
)
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

    # 2. Load Global (Base Layer)
    if GLOBAL_CONFIG.exists():
        with open(GLOBAL_CONFIG, "r") as f:
            try:
                g_cfg = json.load(f)
                merged.update(g_cfg)
            except:
                pass

    # 3. Check Stealth Registry
    registry_path = PARALLAX_HOME / "registry.json"
    cwd = os.path.realpath(os.getcwd())  # Resolve symlinks (e.g., /tmp -> /private/tmp)
    stealth_config = None

    if registry_path.exists():
        try:
            with open(registry_path, "r") as f:
                registry = json.load(f)
            # Normalize registry keys as well
            normalized_registry = {os.path.realpath(k): v for k, v in registry.items()}
            # Check if current path or any parent is registered
            check_path = cwd
            while check_path != "/":
                if check_path in normalized_registry:
                    stealth_config = normalized_registry[check_path]
                    break
                check_path = str(Path(check_path).parent)
        except:
            pass

    # 4. Determine scope and load overlay config
    scope = "GLOBAL"
    target = None

    if stealth_config:
        # STEALTH mode: use registered config
        scope = "STEALTH"
        dashboard_path = stealth_config.get("dashboard", "")
        if dashboard_path:
            target = Path(os.path.expanduser(dashboard_path))
    else:
        # Check for local .parallax/
        proj_path = Path(cwd) / ".parallax/dashboard.json"
        env_path = os.environ.get("PX_DASHBOARD_FILE")
        target = Path(env_path) if env_path else proj_path
        if target.exists():
            scope = "PROJECT"

    # 5. Load overlay config if exists
    if target and target.exists():
        with open(target, "r") as f:
            try:
                p_cfg = json.load(f)
                if "settings" in p_cfg:
                    merged["settings"].update(p_cfg["settings"])
                if "sections" in p_cfg:
                    merged["sections"] = p_cfg["sections"] + [
                        s for s in merged["sections"] if s.get("global")
                    ]
                if "title" in p_cfg:
                    merged["title"] = p_cfg["title"]
                if "entities" in p_cfg:
                    merged["entities"] = p_cfg["entities"]
            except:
                pass

    # Store stealth config for library scanning
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

            os.environ["PX_SHOW_LEGEND"] = show_legend
            os.environ["PX_SESSION_ID"] = session_id
            active_ctx_name_file = f"/tmp/px-active-context-{session_id}.log"
            active_ctx = ""
            if os.path.exists(active_ctx_name_file):
                active_ctx = Path(active_ctx_name_file).read_text().strip()

            styler_path = str(PARALLAX_HOME / "lib" / "exec" / "px-ui-styler")
            cmd = [styler_path, "resident", ctx, scope]
            try:
                # Need to escape parens for FZF change-header()
                # Need to escape parens for FZF change-header()
                out = (
                    subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                    .decode()
                    .strip()
                )
                lines = out.split("\n")

                # Pulse Check: Show active LLM status with color
                provider = "DISCONNECTED"
                p_color = "\x1b[1;31m"  # Red (actual escape char)
                reset = "\x1b[0m"
                session_path = os.path.expanduser("~/.parallax/session.json")
                if os.path.exists(session_path):
                    with open(session_path) as f:
                        s_data = json.load(f)
                        provider = s_data.get("llm_provider", "DEFAULT").upper()
                        if provider != "DISCONNECTED":
                            p_color = "\x1b[1;32m"  # Green

                header_line = lines[0]
                if active_ctx:
                    header_line = f"{header_line} │ {active_ctx.upper()}"

                header_line = f"{header_line} │ 🧠 {p_color}{provider}{reset}"
                lines[0] = header_line
                # Try using actual newlines - FZF may handle them in change-header()
                final_header = "\n".join(lines)
                # ESCAPE FOR FZF ACTION: parens, pipes, quotes
                import re

                # We need to escape: ) ( | " '
                # In FZF action string context, escaping is tricky.
                # Usually backslash works.
                safe_header = re.sub(r"([()|\"\'])", r"\\\1", final_header)
                return safe_header
            except Exception as e:
                # Log exception for debugging
                with open("/tmp/px-styler-error.log", "a") as f:
                    f.write(f"ERROR in run_styler: {e}\n")
                return f"PARALLAX │ {ctx.upper()} │ ERROR"

        if event == "legend_toggle":
            ctx_file = os.environ.get("PX_CTX_FILE", f"/tmp/px-ctx-{session_id}.log")
            ctx = (
                Path(ctx_file).read_text().strip()
                if Path(ctx_file).exists()
                else "entities"
            )
            header = run_styler(ctx.split(":")[0] if ":" in ctx else ctx)
            print(f"reload(px-engine --context {ctx})+change-header({header})")
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

                    header = run_styler(
                        parent_ctx.split(":")[0] if ":" in parent_ctx else parent_ctx
                    )
                    print(
                        f"execute-silent(echo {parent_ctx} > {ctx_file})+reload('{BIN_DIR}/px-engine' --context {parent_ctx})+change-header({header})+clear-query"
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
                header = run_styler(payload)
                print(
                    f"execute-silent(echo {payload} > {ctx_file})+reload(px-engine --context {payload})+change-header({header})+clear-query"
                )
            elif e_type == "FOLDER":
                # Navigate into folder (e.g., actions:git)
                header = run_styler(
                    payload.split(":")[0]
                )  # Use parent plane for header
                print(
                    f"execute-silent(echo {payload} > {ctx_file})+reload(px-engine --context {payload})+change-header({header})+clear-query"
                )
            elif e_type == "CONTEXT":
                # Activate Context: load YAML and export env vars (Zero-dependency parser)
                env_file = os.environ.get("PX_ENV_FILE", f"/tmp/px-env-{session_id}.sh")
                active_ctx_name_file = f"/tmp/px-active-context-{session_id}.log"
                try:
                    env_data = {}
                    with open(payload, "r") as f:
                        in_env_block = False
                        for line in f:
                            raw_line = line
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue

                            # Detect env: block
                            if line.rstrip(":") == "env":
                                in_env_block = True
                                continue

                            if in_env_block:
                                # In YAML, indented lines after 'env:' are the values
                                # raw_line[0] works if there's any leading whitespace
                                if raw_line[0].isspace():
                                    if ":" in line:
                                        k, v = line.split(":", 1)
                                        # Clean up key and value
                                        env_data[k.strip()] = (
                                            v.strip().strip('"').strip("'")
                                        )
                                else:
                                    # Dedented line means block ended
                                    in_env_block = False

                    # Ensure env_file is absolute and normalized
                    env_file = os.path.realpath(env_file)
                    with open(env_file, "w") as f:
                        for k, v in env_data.items():
                            # Escape single quotes in value for zsh safety
                            safe_v = v.replace("'", "'\\''")
                            f.write(f"export {k}='{safe_v}'\\n")

                    # Store context name for styler
                    with open(active_ctx_name_file, "w") as f:
                        f.write(label)
                except Exception as e:
                    pass

                header = run_styler("contexts")
                # FZF Feedback: change-header then execute-silent sleep to let UI breathe
                print(
                    f"change-header( ⚡ ACTIVATED: {label} )+execute-silent(sleep 0.5)+reload(px-engine --context contexts)+change-header({header})+clear-query"
                )
            elif e_type == "ACTION":
                # Check for active linked shells
                link_dir = os.path.expanduser("~/.parallax/links")
                is_linked = False
                if os.path.exists(link_dir):
                    for lk in glob.glob(f"{link_dir}/shell-*.link"):
                        try:
                            l_target_pid = Path(lk).read_text().strip()
                            # Check if this link points to our current Parallax session
                            if l_target_pid == session_id:
                                is_linked = True
                                break
                        except:
                            pass

                env_source = '[[ -f "$PX_ENV_FILE" ]] && source "$PX_ENV_FILE";'

                # Log Action Trigger
                with open("/tmp/px-debug.log", "a") as f:
                    f.write(f"ACTION TRIGGER: {payload}\\n")

                # Delegate Action Init to Wizard
                params = wizard.init_wizard(payload, context)

                if params:
                    p = params[0]
                    desc = p["desc"]
                    var = p["var"]
                    next_ctx = "prompt-0"

                    # Zero Pollution: Show question in Header
                    import re

                    # Escape chars that break FZF action strings: ( ) | ' "
                    safe_desc = re.sub(r"([()|\"\'])", r"\\\1", desc)
                    header = f"PARALLAX │ INPUT │ {safe_desc} ({var.upper()})"
                    ctx_file = os.environ.get(
                        "PX_CTX_FILE", f"/tmp/px-ctx-{session_id}.log"
                    )
                    # No need to send to stage here manually, wizard.init_wizard already did it
                    cmd = f"execute-silent(echo '{next_ctx}' > {ctx_file})+reload('{BIN_DIR}/px-engine' --context '{next_ctx}')+change-header({header})+change-prompt(Input > )+clear-query"
                    print(cmd)
                else:
                    # Final Execution
                    params_file = f"/tmp/px-collected-params-{session_id}.sh"
                    params_source = f"[[ -f {params_file} ]] && source {params_file};"

                    if os.environ.get("PX_TMUX_NATIVE"):
                        # Native: Send to Stage (PRIORITY OVER LINK)
                        # We use px-exec wrapper for clean output
                        cmd = f'px-exec {session_id} "{payload}"'
                        cmd_safe = cmd.replace('"', '\\"')

                        styler_ctx = (
                            context.split(":")[0] if ":" in context else context
                        )
                        header = run_styler(styler_ctx)
                        print(
                            f'change-header( ⚡ SENT TO STAGE )+execute-silent(tmux send-keys -t 0 "{cmd_safe}" Enter)+change-header({header})'
                        )

                    elif is_linked:
                        signal_file = f"/tmp/px-signal-{session_id}.sh"
                        spy_cmd = f"px-spy EXEC 'Remote Action: {payload}'"
                        # Add a timestamp comment to ensure file change is unique
                        raw_cmd = f"{env_source} {params_source} {spy_cmd} && eval {payload} # {time.time()}"
                        # Structured signal with metadata for px-link
                        remote_cmd = f"LABEL:{label}|CMD:{raw_cmd}"
                        with open(signal_file, "w") as f:
                            f.write(f"{remote_cmd}\\n")
                        # Stay in current context
                        styler_ctx = (
                            context.split(":")[0] if ":" in context else context
                        )
                        print(
                            f"change-header( ⚡ SENT TO LINKED SHELL: {label} )+execute-silent(sleep 0.5)+reload(px-engine --context {context})+change-header({run_styler(styler_ctx)})"
                        )
                    else:
                        styler_ctx = (
                            context.split(":")[0] if ":" in context else context
                        )
                        header = run_styler(styler_ctx)
                        print(
                            f'change-header( ⚡ WORKING: {payload} )+execute({env_source} {params_source} px-spy EXEC "Action: {payload}" && eval {payload} && echo ">>> Press Enter..." && read)+change-header({header})'
                        )
            elif e_type == "AGENT":
                env_source = '[[ -f "$PX_ENV_FILE" ]] && source "$PX_ENV_FILE";'
                # Surface logic currently not supported in flat ENTER event
                # Surface would need to be encoded in payload
                print(
                    f'execute({env_source} px-spy AGENT "Invoke: {payload}" && px-agent chat {payload})'
                )
            elif e_type == "PROMPT":
                # Edit Prompt then Sync
                print(
                    f'execute(px-spy INTEL "Edit Prompt: {label}" && ${{EDITOR:-vi}} {payload} && px-prompt-sync {payload} && echo ">>> Press Enter..." && read)'
                )
            elif e_type == "SURFACE":
                # Materialize Tmux Layout
                print(
                    f"change-header( 🔳 MATERIALIZING SURFACE: {label} )+execute-silent(px-surface apply {payload})+execute-silent(sleep 0.5)+change-header({run_styler(context)})"
                )
            elif e_type == "PLACE":
                # Check for active linked shells
                link_dir = os.path.expanduser("~/.parallax/links")
                is_linked = False
                if os.path.exists(link_dir):
                    # Local imports removed

                    for lk in glob.glob(f"{link_dir}/*.link"):
                        try:
                            if Path(lk).read_text().strip() == session_id:
                                is_linked = True
                                break
                        except:
                            pass

                env_source = '[[ -f "$PX_ENV_FILE" ]] && source "$PX_ENV_FILE";'
                signal_file = os.environ.get(
                    "PX_SIGNAL_FILE", f"/tmp/px-signal-{session_id}.sh"
                )
                # Write signal for linked shells
                try:
                    with open(signal_file, "w") as f:
                        f.write(f"SILENT:cd {payload} # {time.time()}\\n")
                except:
                    pass

                # Place Navigation Priority:
                # 1. Native Mode (Direct send-keys)
                # 2. Linked Shell (Signal file)
                # 3. Standard (Inline execution)

                if os.environ.get("PX_TMUX_NATIVE"):
                    # Native: cd in Stage
                    # SMART NAV: Check for environment activation
                    nav_cmd = (
                        f'cd "{payload}" && '
                        'if [[ -f ".venv/bin/activate" ]]; then source .venv/bin/activate; '
                        'elif [[ -f "venv/bin/activate" ]]; then source venv/bin/activate; '
                        'elif [[ -f ".envrc" ]] && command -v direnv &>/dev/null; then direnv allow; fi'
                    )

                    cmd = f"px-spy NAV 'Place: {payload}'; {nav_cmd}"
                    cmd_safe = cmd.replace('"', '\\\\"')
                    print(
                        f'change-header( ⚡ NAVIGATING )+execute-silent(tmux send-keys -t 0 "{cmd_safe}" Enter)+change-header({run_styler("places")})'
                    )
                elif is_linked:
                    # Silent navigation if linked
                    signal_file = os.environ.get(
                        "PX_SIGNAL_FILE", f"/tmp/px-signal-{session_id}.sh"
                    )
                    try:
                        with open(signal_file, "w") as f:
                            # Linked shells might need their own smart hook in px-link,
                            # but sending a basic cd is safer for remote control for now.
                            f.write(f"SILENT:cd {payload} # {time.time()}\\n")
                    except:
                        pass
                    print(
                        f"change-header( ✈️ SYNCING NAV: {payload} )+execute-silent(sleep 0.5)+change-header({run_styler('places')})"
                    )
                else:
                    # Standard Mode (Foregroud)
                    nav_cmd = (
                        f"cd {payload} && "
                        'if [[ -f ".venv/bin/activate" ]]; then source .venv/bin/activate; '
                        'elif [[ -f "venv/bin/activate" ]]; then source venv/bin/activate; fi && zsh'
                    )
                    print(
                        f'change-header( ✈️ NAVIGATING: {payload} )+execute({env_source} px-spy NAV "Place: {payload}" && {nav_cmd})'
                    )
            elif e_type == "PROMPT_VAL" or e_type == "PROMPT_INPUT":
                # Delegate to Wizard Manager
                print(wizard.process_input(payload, label))
            elif e_type == "SETTING":
                parts = payload.split(":")
                if len(parts) >= 3:
                    key = parts[1]
                    curr = parts[2]
                    new_val = ""

                    if key == "PX_LAYOUT_STYLE":
                        new_val = "default" if curr == "reverse" else "reverse"
                    elif key == "PX_VERBOSE":
                        new_val = "false" if curr == "true" else "true"
                    elif key == "PX_SHOW_LEGEND":
                        new_val = "false" if curr == "true" else "true"
                    elif key == "PX_HUD_PATH_STYLE":
                        new_val = "full" if curr == "short" else "short"

                    # 1. Update Persistent Config
                    cfg = os.path.expanduser("~/.parallax/config")
                    lines = []
                    if os.path.exists(cfg):
                        with open(cfg, "r") as f:
                            lines = f.readlines()

                    found = False
                    new_lines = []
                    for line in lines:
                        if line.startswith(f"export {key}="):
                            new_lines.append(f'export {key}="{new_val}"\\n')
                            found = True
                        else:
                            new_lines.append(line)
                    if not found:
                        new_lines.append(f'export {key}="{new_val}"\\n')

                    with open(cfg, "w") as f:
                        f.writelines(new_lines)

                    # 2. Update Immediate State (Files)
                    if key == "PX_VERBOSE":
                        p = os.environ.get("PX_VERBOSE_FILE")
                        if p:
                            Path(p).write_text(new_val)
                    elif key == "PX_SHOW_LEGEND":
                        p = os.environ.get("PX_SHOW_LEGEND_FILE")
                        if p:
                            Path(p).write_text(new_val)

                    if key == "PX_LAYOUT_STYLE":
                        restart_flag = f"/tmp/px-restart-{os.environ.get('PX_SESSION_ID', str(os.getpid()))}.flag"
                        with open(restart_flag, "w") as f:
                            f.write("1")
                        print(
                            f"change-header( ⚡ RESTARTING... )+execute-silent(sleep 0.1)+abort"
                        )
                    else:
                        print(
                            f"reload(px-engine --context settings)+change-header( ⚙️ UPDATED {key} )"
                        )

            return
        elif event == "TOGGLE_DASHBOARD":
            # Toggle between normal dashboard and custom dashboard
            import subprocess

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
