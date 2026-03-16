# modules/menu/lib/providers/model_server.py
import os
import json
import requests
from lib.core.menu_engine import fmt

def provide(subfolder=""):
    """Fetches active models from model-server via health/diag endpoint."""
    # Defualt srv port
    srv_port = os.environ.get("SRV_PORT", "8000")
    url = f"http://localhost:{srv_port}/health" # or a dedicated diag endpoint
    
    items = []
    
    try:
        # We'll try to get the list from the server
        # For now, let's assume there's a /models endpoint or similar
        # If the server is down, we report it.
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            # Mocking some active models for now if the server doesn't provide them yet
            # In a real scenario, srv would return the registry.
            active_models = data.get("active_models", ["llama3.1", "qwen2.5-coder"])
            
            for m in active_models:
                items.append(fmt(f"💻 {m}", "ACTION", f"nxs-agent-switch-model '{m}'", 
                                 status="online", color="green"))
        else:
            items.append(fmt("Model Server: Limited", "WARNING", "NONE", status="warning"))
    except Exception:
        # Fallback to offline state
        items.append(fmt("Model Server: Offline", "DISABLED", "NONE", 
                         status="offline", description="Start srv-cluster first"))
        
    return items
