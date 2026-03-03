import os
import json
import socket

def get_workspaces():
    items = []
    
    # 1. Registry
    registry_path = os.path.expanduser("~/.parallax/registry.json")
    if os.path.exists(registry_path):
        try:
            with open(registry_path, 'r') as f:
                registry = json.load(f)
            for path, info in registry.items():
                name = os.path.basename(path)
                items.append(path)
        except: pass
        
    # 2. Local CWD
    cwd = os.getcwd()
    try:
        if os.path.exists(cwd):
           for d in os.listdir(cwd):
               full = os.path.join(cwd, d)
               if os.path.isdir(os.path.join(full, ".parallax")):
                   if full not in items:
                       items.append(full)
    except: pass
    
    # Print for FZF
    for i in items:
        print(i)

if __name__ == "__main__":
    get_workspaces()
