#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Axiom: Deterministic Discovery
MODEL_SERVER_DATA = Path("/Users/Shared/Projects/model-server/data")
NEXUS_HOME = Path(os.environ.get("NEXUS_HOME", "/Users/Shared/Projects/nexus-shell"))
FAVORITES_FILE = Path.home() / ".nexus" / "favorites" / "models.json"

def get_favorites():
    if FAVORITES_FILE.exists():
        try:
            with open(FAVORITES_FILE, "r") as f:
                return set(json.load(f))
        except:
            pass
    return set()

def fmt(label, e_type, payload, icon="🧠", description="", source_path="", meta=None):
    data = {
        "label": label,
        "type": e_type,
        "payload": payload,
        "icon": icon,
        "description": description,
        "source_path": source_path
    }
    if meta:
        data.update(meta)
    return json.dumps(data)

def resolve_locality(path, roots):
    for r in roots:
        if path.startswith(r):
            if "Archive" in r or "Volumes" in r:
                return "External Drive"
            return "Internal SSD"
    return "Unknown"

def main():
    context = sys.argv[1] if len(sys.argv) > 1 else "models"
    favorites = get_favorites()
    
    local_registry = MODEL_SERVER_DATA / "local.json"
    cloud_registry = MODEL_SERVER_DATA / "cloud.json"

    # --- 1. Root Models Menu ---
    if context == "models":
        print(fmt("Favorites", "FOLDER", "models:favs", icon="⭐", description="Pinned models"))
        print(fmt("Local Models", "FOLDER", "models:local", icon="🏛️", description="SSD & External"))
        print(fmt("Cloud Providers", "FOLDER", "models:cloud", icon="☁️", description="API models"))
        return

    # --- 2. Favorites ---
    if context == "models:favs":
        # Scan everything and yield if in favorites
        all_models = []
        if local_registry.exists():
            with open(local_registry, "r") as f:
                mod_data = json.load(f).get("models", {})
                for cat in mod_data.values():
                    for back in cat.values():
                        all_models.extend(back)
        if cloud_registry.exists():
            with open(cloud_registry, "r") as f:
                mod_data = json.load(f).get("models", {})
                for cat in mod_data.values():
                    for back in cat.values():
                        all_models.extend(back)
        
        found = False
        for m in all_models:
            m_id = m.get("id")
            if m_id in favorites:
                print(fmt(m.get("name", m_id), "MODEL", m_id, icon="⭐", description="Pinned", source_path=""))
                found = True
        
        if not found:
            print(fmt("No favorites yet", "DISABLED", "NONE", icon="🚫", description="Hit 'f' on any model to pin it"))
        return

    # --- 3. Local Models (By Locality) ---
    if context == "models:local":
        if local_registry.exists():
            with open(local_registry, "r") as f:
                data = json.load(f)
                roots = data.get("roots", [])
                
                print(fmt("Internal SSD", "FOLDER", "models:local:ssd", icon="💻"))
                print(fmt("External Drive", "FOLDER", "models:local:ext", icon="💾"))
        return

    if context.startswith("models:local:"):
        locality_type = context.split(":")[-1] # ssd or ext
        if local_registry.exists():
            with open(local_registry, "r") as f:
                data = json.load(f)
                roots = data.get("roots", [])
                models_dict = data.get("models", {})
                
                found = False
                for cat, backends in models_dict.items():
                    for backend, models in backends.items():
                        for m in models:
                            m_id = m.get("id")
                            m_path = m.get("path", "")
                            locality = resolve_locality(m_path, roots)
                            
                            is_target = False
                            if locality_type == "ssd" and locality == "Internal SSD": is_target = True
                            if locality_type == "ext" and locality == "External Drive": is_target = True
                            
                            if is_target:
                                icon = "⭐" if m_id in favorites else "🏛️"
                                print(fmt(m_id, "MODEL", m_id, icon=icon, description=backend, source_path=str(local_registry)))
                                found = True
                if not found:
                    print(fmt(f"No models found on {locality_type}", "DISABLED", "NONE"))
        return

    # --- 4. Cloud Providers ---
    if context == "models:cloud":
        if cloud_registry.exists():
            with open(cloud_registry, "r") as f:
                data = json.load(f)
                providers = set()
                for cat, backends in data.get("models", {}).items():
                    for provider in backends.keys():
                        providers.add(provider)
                
                for p in sorted(list(providers)):
                    print(fmt(p.capitalize(), "FOLDER", f"models:cloud:{p}", icon="☁️"))
        return

    if context.startswith("models:cloud:"):
        target_provider = context.split(":")[-1]
        if cloud_registry.exists():
            with open(cloud_registry, "r") as f:
                data = json.load(f)
                for cat, backends in data.get("models", {}).items():
                    if target_provider in backends:
                        for m in backends[target_provider]:
                            m_id = m.get("id")
                            icon = "⭐" if m_id in favorites else "☁️"
                            print(fmt(m.get("name", m_id), "MODEL", m_id, icon=icon, description=cat, source_path=str(cloud_registry)))
        return

if __name__ == "__main__":
    main()
