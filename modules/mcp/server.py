import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
import mcp.server.stdio

# Add project root to sys.path to allow importing from other modules
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Attempt to import menu_engine for list discovery
try:
    from modules.menu.lib.core import menu_engine
except ImportError:
    menu_engine = None

server = Server("nexus-mcp")

@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available Nexus Shell tools."""
    tools = [
        types.Tool(
            name="tmux_list_panes",
            description="List all active tmux panes in the current session.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="tmux_capture_pane",
            description="Capture the content of a specific tmux pane.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pane_id": {"type": "string", "description": "The ID of the pane (e.g., %1)."},
                    "lines": {"type": "integer", "description": "Number of lines to capture (default 100).", "default": 100},
                },
                "required": ["pane_id"],
            },
        ),
        types.Tool(
            name="get_shelf_items",
            description="List items currently stowed on the Nexus Shelf (background panes).",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_workspace_info",
            description="Get information about the current Nexus Shell workspace and lists.",
            inputSchema={
                "type": "object",
                "properties": {
                    "context": {"type": "string", "description": "The list context (e.g., 'scripts', 'actions').", "default": "actions"},
                },
            },
        ),
    ]
    return tools

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> List[types.TextContent]:
    """Execute a Nexus Shell tool."""
    if name == "tmux_list_panes":
        try:
            # Format: pane_id, pane_current_command, window_name
            cmd = ["tmux", "list-panes", "-a", "-F", "#{pane_id}|#{window_name}|#{pane_current_command}"]
            result = subprocess.check_output(cmd, text=True)
            return [types.TextContent(type="text", text=result)]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error listing panes: {str(e)}")]

    elif name == "tmux_capture_pane":
        pane_id = arguments.get("pane_id")
        lines = arguments.get("lines", 100)
        try:
            cmd = ["tmux", "capture-pane", "-p", "-t", pane_id, "-S", f"-{lines}"]
            result = subprocess.check_output(cmd, text=True)
            return [types.TextContent(type="text", text=result)]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error capturing pane {pane_id}: {str(e)}")]

    elif name == "get_shelf_items":
        try:
            # We look for the NEXUS_SHELF window in the current session
            # Note: We assume standard session discovery logic similar to shelf_provider.py
            result = subprocess.check_output([
                "tmux", "list-panes", "-t", "NEXUS_SHELF", 
                "-F", "#{pane_id}|#{pane_current_command}|#{@nexus_tab_name}"
            ], text=True).strip()
            
            if not result:
                return [types.TextContent(type="text", text="Shelf is empty.")]
                
            return [types.TextContent(type="text", text=result)]
        except Exception:
            # If window doesn't exist, it likely means shelf is empty or not initialized
            return [types.TextContent(type="text", text="Shelf is empty or reservoir missing.")]

    elif name == "get_workspace_info":
        context = arguments.get("context", "actions")
        info = {
            "project_root": str(PROJECT_ROOT),
            "active_profile": os.environ.get("NEXUS_PROFILE", "default"),
            "sovereign_layers": []
        }
        
        if menu_engine:
            layers = menu_engine.get_list_layers(context)
            for layer in layers:
                items = []
                for item in layer.glob("*"):
                    items.append(item.name)
                info["sovereign_layers"].append({
                    "path": str(layer),
                    "items": items
                })
        
        return [types.TextContent(type="text", text=json.dumps(info, indent=2))]

    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="nexus-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
