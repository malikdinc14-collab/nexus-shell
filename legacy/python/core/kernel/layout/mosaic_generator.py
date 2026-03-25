#!/usr/bin/env python3
# core/mosaic_generator.py
# Discovers open tabs/buffers and generates a dynamic Mosaic JSON layout.

import json
import os
import sys
import math
from pathlib import Path

_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

try:
    from engine.actions.resolver import AdapterResolver
    _EDITOR = AdapterResolver.editor()
except Exception:
    _EDITOR = None


def get_nvim_tabs(pipe):
    if not os.path.exists(pipe) or _EDITOR is None:
        return []
    expr = "JSON.stringify(map(gettabinfo(), {k, v -> {'id': v.tabnr, 'type': 'nvim', 'title': fnamemodify(bufname(v.windows[0]), ':t'), 'path': bufname(v.windows[0])}}))"
    res = _EDITOR.remote_expr(expr)
    try:
        return json.loads(res)
    except Exception:
        expr_buf = "JSON.stringify(map(filter(getbufinfo({'buflisted':1}), {k, v -> v.name != ''}), {k, v -> {'id': v.bufnr, 'type': 'nvim_buf', 'title': fnamemodify(v.name, ':t'), 'path': v.name}}))"
        res_buf = _EDITOR.remote_expr(expr_buf)
        try:
            return json.loads(res_buf)
        except Exception:
            return []

def get_shell_tabs():
    nexus_home = os.environ.get("NEXUS_HOME", "")
    res = run_command(f"{nexus_home}/core/terminal_tabs.sh list")
    tabs = []
    for line in res.split('\n'):
        if not line: continue
        # Example: term:1 (zsh) [pane_id]
        parts = line.split()
        if len(parts) >= 3:
            title = parts[0]
            pane_id = parts[-1].strip('[]')
            tabs.append({'id': pane_id, 'type': 'shell', 'title': title})
    return tabs

def create_layout(items):
    n = len(items)
    if n == 0: return {"command": "echo 'No open tabs'"}
    
    # Calculate grid dimensions (e.g., for 5 items, use 2 rows, 3 columns)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    
    nexus_home = os.environ.get("NEXUS_HOME", "")
    select_script = f"{nexus_home}/core/mosaic_select.sh"
    
    row_panes = []
    for r in range(rows):
        col_panes = []
        for c in range(cols):
            idx = r * cols + c
            if idx < n:
                item = items[idx]
                col_panes.append({
                    "id": f"mosaic_{item['type']}_{item['id']}",
                    "command": f"{select_script} {item['type']} {item['id']} '{item.get('title', 'Unknown')}'"
                })
        
        if col_panes:
            row_panes.append({
                "type": "hsplit",
                "panes": col_panes
            })
            
    return {
        "type": "vsplit",
        "panes": row_panes
    }

if __name__ == "__main__":
    project_name = os.environ.get("NEXUS_PROJECT", "")
    pipe = f"/tmp/nexus_{os.getlogin()}/pipes/nvim_{project_name}.pipe"
    
    items = get_nvim_tabs(pipe) + get_shell_tabs()
    
    layout = create_layout(items)
    output = {
        "name": "mosaic-switcher",
        "layout": layout
    }
    
    with open("/tmp/nexus_mosaic.json", "w") as f:
        json.dump(output, f)
