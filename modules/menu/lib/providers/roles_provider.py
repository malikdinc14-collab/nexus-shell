# modules/menu/lib/providers/roles_provider.py
import os
from pathlib import Path
from lib.core.menu_engine import fmt, NEXUS_HOME

def provide(subfolder=""):
    """Browse agency-agents roles for loading as system prompt."""
    items = []
    agency_agents_root = NEXUS_HOME.parent / "external_repos" / "agency-agents"
    if not agency_agents_root.exists():
        # Try env var
        agency_agents_root = Path(os.environ.get("AGENCY_AGENTS_DIR", ""))

    if agency_agents_root.exists():
        # Handle subfolder drill-down
        target_dir = agency_agents_root / subfolder if subfolder else agency_agents_root
        
        if not target_dir.exists():
            return [fmt(f"Dir not found: {subfolder}", "ERROR", "NONE")]

        for cat_dir in sorted(target_dir.iterdir()):
            if cat_dir.is_dir() and not cat_dir.name.startswith("."):
                rel_path = f"{subfolder}/{cat_dir.name}" if subfolder else cat_dir.name
                items.append(fmt(f"📁 {cat_dir.name}/", "FOLDER", f"roles/{rel_path}"))
            elif cat_dir.suffix == ".md":
                label = f"{subfolder}/{cat_dir.stem}" if subfolder else cat_dir.stem
                items.append(fmt(f"🎭 {cat_dir.stem}", "ACTION", f"nxs-agent-set-role '{cat_dir}'"))

    return items or [fmt("No roles found (agency-agents not found)", "DISABLED", "NONE")]
