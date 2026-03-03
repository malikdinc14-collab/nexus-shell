import os
import subprocess
import json

try:
    import psutil
except ImportError:
    psutil = None


def render(context, config, paths):
    """
    Renders the 'Nexus' pillar: System health and AI control.
    """
    output = []

    # 1. Main Nexus View
    if context == "nexus" or context == "section:nexus system":
        # A. Service Status
        output.append({"label": "📊 NEXUS CORE STATUS", "type": "SEPARATOR"})

        services = [
            ("Letta Backend", 8283),
            ("Nexus Gateway", 11436),
            ("Commander Node", 1234),
            ("Embedding Node", 11435),
        ]

        for name, port in services:
            status = "🔴"
            try:
                if (
                    subprocess.call(
                        ["lsof", "-i", f":{port}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    == 0
                ):
                    status = "🟢"
            except:
                pass
            output.append({"label": f"{status} {name}", "type": "DISABLED"})

        # B. Resource Monitor
        if psutil:
            output.append({"label": "🧠 RESOURCE MONITOR", "type": "SEPARATOR"})
            vm = psutil.virtual_memory()
            swap = psutil.swap_memory()

            ram_pct = vm.percent
            swap_used_gb = swap.used / (1024**3)
            swap_total_gb = swap.total / (1024**3)
            swap_pct = swap.percent

            # Swap Shield Alert (2GB limit from launcher)
            swap_shield_limit = 2.0
            swap_status = "🟢"
            if swap_used_gb > swap_shield_limit * 0.8:
                swap_status = "🟡"
            if swap_used_gb > swap_shield_limit * 0.95:
                swap_status = "🔴"

            output.append({"label": f"RAM Usage: {ram_pct}%", "type": "DISABLED"})
            output.append(
                {
                    "label": f"{swap_status} Swap Used: {swap_used_gb:.2f} GB / {swap_shield_limit} GB (Shield)",
                    "type": "DISABLED",
                }
            )
            output.append(
                {
                    "label": f"   Total Swap: {swap_total_gb:.2f} GB ({swap_pct}%)",
                    "type": "DISABLED",
                }
            )
        else:
            output.append(
                {"label": "🧠 RESOURCE MONITOR (psutil missing)", "type": "SEPARATOR"}
            )

        # C. Project Agent Detection
        output.append({"label": "📁 PROJECT CONTEXT", "type": "SEPARATOR"})
        cwd = os.getcwd()
        opencode_json = os.path.join(cwd, "opencode.json")
        project_name = os.path.basename(cwd)
        output.append({"label": f"Dir: {project_name}", "type": "DISABLED"})

        if os.path.exists(opencode_json):
            try:
                with open(opencode_json, "r") as f:
                    data = json.load(f)
                    agents = data.get("agent", {})
                    if agents:
                        output.append(
                            {"label": "🟢 PROJECT AGENTS DETECTED:", "type": "DISABLED"}
                        )
                        for agent_name in agents:
                            output.append(
                                {"label": f"  - {agent_name}", "type": "DISABLED"}
                            )
                    else:
                        output.append(
                            {
                                "label": "🟡 No agents in opencode.json",
                                "type": "DISABLED",
                            }
                        )
            except Exception as e:
                output.append(
                    {"label": "🔴 Error parsing opencode.json", "type": "DISABLED"}
                )
        else:
            output.append({"label": "⚪ No project agents found", "type": "DISABLED"})

        # D. Actions
        output.append({"label": "⚡ QUICK ACTIONS", "type": "SEPARATOR"})
        nexus_home = os.getenv("NEXUS_HOME", os.path.expanduser("~/.config/nexus-shell"))
        nexus_actions_dir = os.path.join(nexus_home, "modules/parallax/actions/nexus")

        if os.path.exists(nexus_actions_dir):
            output.append(
                {
                    "label": "🚀 Nexus Full Ignition",
                    "type": "ACTION",
                    "path": os.path.join(nexus_actions_dir, "nexus-up.sh"),
                }
            )
            output.append(
                {
                    "label": "🛑 Nexus Shutdown",
                    "type": "ACTION",
                    "path": os.path.join(nexus_actions_dir, "nexus-down.sh"),
                }
            )
            output.append(
                {
                    "label": "📁 Index Shell Project",
                    "type": "ACTION",
                    "path": os.path.join(nexus_actions_dir, "nexus-index-shell.sh"),
                }
            )
            output.append(
                {
                    "label": "🔬 Index LLM-Lab",
                    "type": "ACTION",
                    "path": os.path.join(nexus_actions_dir, "nexus-index-lab.sh"),
                }
            )

        return output

    return None
