import os
import subprocess


def render(context, config, paths):
    """
    Renders the 'System' pillar (formerly Control) and its sub-contexts.
    """
    output = []
    BIN_DIR = paths["BIN_DIR"]
    GLOBAL_CONFIG = paths["GLOBAL_CONFIG"]

    # 1. Main System View
    if context == "system":
        output.append(
            {"label": "📊 Nexus Dashboard", "type": "PLANE", "payload": "nexus"}
        )
        output.append(
            {"label": "🟢 Service Health", "type": "FOLDER", "payload": "audit"}
        )
        output.append({"label": "⚙️  Settings", "type": "FOLDER", "payload": "settings"})
        output.append(
            {"label": "🛠️  Configuration", "type": "FOLDER", "payload": "system:config"}
        )
        return output

    # 2. Previous control:ops is now merged into system
    elif context == "control" or context == "control:ops":
        # Redirect to new system pillar
        output.append(
            {"label": "🟢 Service Health", "type": "FOLDER", "payload": "audit"}
        )
        output.append({"label": "⚙️  Settings", "type": "FOLDER", "payload": "settings"})
        output.append(
            {"label": "🛠️  Configuration", "type": "FOLDER", "payload": "system:config"}
        )
        return output

    # 3. Audit (Service Health)
    elif context == "audit":
        # Check for active Parallax-managed processes
        try:
            # Check for MLX
            if (
                subprocess.call(
                    ["lsof", "-i", ":8080"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                == 0
            ):
                output.append(
                    {
                        "label": "🟢 MLX Server (Port 8080)",
                        "type": "ACTION",
                        "path": "true",
                    }
                )

            # Check for Ollama
            if (
                subprocess.call(
                    ["lsof", "-i", ":11434"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                == 0
            ):
                output.append(
                    {
                        "label": "🟢 Ollama Service (Port 11434)",
                        "type": "ACTION",
                        "path": "true",
                    }
                )

            # If nothing found
            if not output:
                output.append(
                    {"label": "⚪ No Active Services detected.", "type": "DISABLED"}
                )

        except Exception as e:
            output.append({"label": f"Audit Error: {e}", "type": "DISABLED"})

        return output

    # 4. Settings
    elif context == "settings":
        cfg_path = os.path.expanduser("~/.parallax/config")

        # Toggle Switches (State read from env)
        # Helper to get checkmark
        def get_state(key, default="false"):
            val = os.environ.get(key, default)
            return (
                ("✅", val)
                if val == "true" or val == "reverse" or val == "full"
                else ("⬜", val)
            )

        # 1. Layout Style (Default vs Reverse)
        st_layout, v_layout = get_state("PX_LAYOUT_STYLE", "default")
        label_layout = (
            "Logic: App-Like (Reverse)"
            if v_layout == "reverse"
            else "Logic: Terminal (Standard)"
        )
        output.append(
            {
                "label": f"{st_layout} {label_layout}",
                "type": "SETTING",
                "action": f"toggle:PX_LAYOUT_STYLE:{v_layout}",
            }
        )

        # 2. Path Style (Short vs Full)
        # Note: default is 'short', so check for 'full'
        v_path = os.environ.get("PX_HUD_PATH_STYLE", "short")
        st_path = "✅" if v_path == "full" else "⬜"
        label_path = (
            "View: Full Path" if v_path == "full" else "View: Short Path (Folder Only)"
        )
        output.append(
            {
                "label": f"{st_path} {label_path}",
                "type": "SETTING",
                "action": f"toggle:PX_HUD_PATH_STYLE:{v_path}",
            }
        )

        # 3. Verbosity
        st_verb, v_verb = get_state("PX_VERBOSE")
        output.append(
            {
                "label": f"{st_verb} Debug Mode (Verbose)",
                "type": "SETTING",
                "action": f"toggle:PX_VERBOSE:{v_verb}",
            }
        )

        # 4. Legend
        st_legend, v_legend = get_state(
            "PX_SHOW_LEGEND", "true"
        )  # Legend defaults to true
        output.append(
            {
                "label": f"{st_legend} Show Footer Legend",
                "type": "SETTING",
                "action": f"toggle:PX_SHOW_LEGEND:{v_legend}",
            }
        )

        output.append(
            {
                "label": "📝 Edit Local Config",
                "type": "ACTION",
                "path": f"${{EDITOR:-vi}} {cfg_path}",
            }
        )
        return output

    # 5. System Configuration
    elif context == "system:config":
        # ... existing logic ...
        return output

    # 6. Spawn Context
    elif context == "system:spawn":
        # Get project-specific windows if available
        windows = config.get("windows", [])
        if windows:
            for idx, w in enumerate(windows):
                name = w.get("name", f"View {idx}")
                output.append(
                    {
                        "label": f"🪟 New Tab: {name}",
                        "type": "ACTION",
                        "path": f"execute(modules/parallax/bin/px-window-spawn {idx} '{name}')",
                    }
                )
            output.append(
                {"label": "------------------------------", "type": "SEPARATOR"}
            )

        # Global Defaults
        output.append(
            {
                "label": "🖥️  New Tab: Primary Workspace",
                "type": "ACTION",
                "path": "execute(modules/parallax/bin/px-window-spawn 0 Workspace)",
            }
        )
        output.append(
            {
                "label": "📋 New Tab: Planning",
                "type": "ACTION",
                "path": "execute(modules/parallax/bin/px-window-spawn 1 Planning)",
            }
        )
        output.append(
            {
                "label": "📊 New Tab: Monitor",
                "type": "ACTION",
                "path": "execute(modules/parallax/bin/px-window-spawn 2 Monitor)",
            }
        )
        output.append(
            {
                "label": "🐚 New Tab: Shells",
                "type": "ACTION",
                "path": "execute(modules/parallax/bin/px-window-spawn 3 Shells)",
            }
        )
        return output

    return None
