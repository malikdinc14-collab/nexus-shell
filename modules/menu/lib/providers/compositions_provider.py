# modules/menu/lib/providers/compositions_provider.py
import json
from lib.core.menu_engine import fmt, NEXUS_HOME, PROJECT_NEXUS

def provide(subfolder=""):
    """Lists saved window compositions (layouts)."""
    items = []
    for scope, comp_dir in [("Global", NEXUS_HOME / "compositions"),
                             ("Project", PROJECT_NEXUS / "compositions")]:
        if not comp_dir.exists():
            continue
        for f in sorted(comp_dir.glob("*.json")):
            try:
                name = json.loads(f.read_text()).get("name", f.stem)
            except Exception:
                name = f.stem
            cmd_arg = str(f) if scope == "Project" else f.stem
            items.append(fmt(f"🪟 {name} [{scope}]", "ACTION",
                f"nxs-switch-layout '{cmd_arg}'"))
    return items or [fmt("No compositions found", "DISABLED", "NONE")]
