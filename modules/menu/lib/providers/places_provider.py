# modules/menu/lib/providers/places_provider.py
import os
import yaml
from pathlib import Path
from lib.core.menu_engine import fmt, expand, PROJECT_NEXUS

def provide(subfolder=""):
    """Lists bookmarks/places from .nexus/places.yaml."""
    items = []
    places_file = PROJECT_NEXUS / "places.yaml"
    if places_file.exists():
        try:
            data = yaml.safe_load(places_file.read_text())
            for p in data.get("places", []):
                label = p.get("label", "Unknown")
                path = expand(p.get("path", "."))
                items.append(fmt(f"📍 {label}", "PLACE", path))
        except Exception:
            pass
    if not items:
        items.append(fmt("💡 No places configured (.nexus/places.yaml)", "DISABLED", "NONE"))
    return items
