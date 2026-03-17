#!/usr/bin/env python3
"""
Nexus Sovereign Menu (NXM)
Vim-style modal explorer powered by Textual.
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import List, Tuple

from textual.app import App, ComposeResult
from textual.containers import Vertical, Container
from textual.widgets import Header, Footer, Input, ListItem, ListView, Static, Label
from textual.binding import Binding
from textual import events
from textual.reactive import reactive

# Add project root to sys.path to find lib.core.menu_engine
BIN_DIR = Path(__file__).parent.resolve()
MODULES_DIR = BIN_DIR.parent
sys.path.insert(0, str(MODULES_DIR))

from lib.core import menu_engine

# STARTUP TRACE
with open("/tmp/nexus_nxm_trace.log", "a") as f:
    f.write(f"NXM Start: {__file__} | CWD: {os.getcwd()}\n")

class NexusListItem(ListItem):
    def __init__(self, label: str, e_type: str, payload: str, disabled: bool = False):
        super().__init__()
        self.label_text = label
        self.e_type = e_type
        self.payload = payload
        self.disabled = disabled
        if disabled:
            self.can_focus = False

    def compose(self) -> ComposeResult:
        # Minimalist label-only layout
        yield Label(f" {self.label_text}")

class NexusTile(Static):
    """A focusable tile for the Grid layout."""
    def __init__(self, label: str, e_type: str, payload: str, meta: dict = None):
        super().__init__()
        self.label_text = label
        self.e_type = e_type
        self.payload = payload
        self.meta = meta or {}
        self.can_focus = True

    def compose(self) -> ComposeResult:
        icon = self.meta.get("icon", "📦")
        # Render label text first (top), then icon below it
        yield Label(self.label_text, classes="tile-label")
        yield Label(icon, classes="tile-icon")
        if "description" in self.meta:
            yield Label(self.meta["description"], classes="tile-desc")

    def on_click(self) -> None:
        self.app.action_item("run")

class NexusMenuApp(App):
    # Reactive properties for autoscaling
    grid_cols = reactive(4)
    tile_height = reactive(5)
    
    CSS = """
    NexusMenuApp {
        background: transparent;
        padding: 0;
        margin: 0;
    }
    Screen {
        background: transparent;
        align: center middle;
    }
    #main-container {
        width: 100%;
        height: 100%;
        border: none;
        padding: 0;
        background: transparent;
        align: center middle;
    }
    #search-bar {
        dock: bottom;
        background: transparent;
        border: none;
        padding: 0 1;
        display: none;
        color: $accent;
        height: 1;
    }
    #search-bar.-visible {
        display: block;
    }
    #header {
        background: $accent 10%;
        color: $accent;
        padding: 0 1;
        height: 1;
        text-style: bold;
        content-align: center middle;
        dock: top;
    }
    
    /* List View Styles - centered with max-width */
    ListView {
        background: transparent;
        border: none;
        max-width: 60;
        min-width: 20;
        width: auto;
        align: center top;
        margin: 1 2;
    }
    ListItem {
        padding: 0 1;
        background: transparent;
    }
    ListItem:hover {
        background: $accent 20%;
    }
    ListView > ListItem.--highlight {
        background: $accent 30%;
        color: $text;
        text-style: bold;
    }
    #menu-list.hidden {
        display: none;
    }
    
    /* Grid wrapper - centers the grid container */
    #grid-wrapper {
        align: center middle;
        width: 100%;
        height: 1fr;
        padding: 1 2;
    }
    #menu-grid {
        layout: grid;
        grid-size: 4;
        grid-gutter: 1;
        padding: 1;
        overflow-y: auto;
        overflow-x: hidden;
        /* Constrain to prevent clipping */
        max-width: 80;
        min-width: 40;
        width: auto;
        max-height: 85%;
        /* Center the grid within wrapper */
        align: center top;
        margin: 0 2;
    }
    #menu-grid.hidden {
        display: none;
    }
    #grid-wrapper.hidden {
        display: none;
    }

    NexusTile {
        background: $surface;
        border: tall $background;
        content-align: center middle;
        padding: 1;
        height: auto;
        min-height: 5;
        min-width: 12;
        transition: background 200ms, border 200ms, offset 200ms;
    }
    NexusTile:focus {
        background: $accent 15%;
        border: tall $accent;
        text-style: bold;
        offset-y: -1;
    }
    #status-bar {
        background: $surface;
        color: $text-muted;
        height: 1;
        dock: bottom;
        padding: 0 1;
        content-align: center middle;
    }
    .tile-icon {
        height: 2;
        content-align: center middle;
    }
    .tile-label {
        height: 1;
        content-align: center middle;
    }
    .tile-desc {
        color: $text-muted;
        height: 1;
        content-align: center middle;
    }

    /* Minimal footer replacement if needed, otherwise hidden */
    Footer {
        display: none;
    }
    """

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("h", "cursor_left", "Left", show=False),
        Binding("l", "cursor_right", "Right", show=False),
        Binding("e", "edit_item", "Edit", show=True),
        Binding("x", "context_item", "Context", show=True),
        Binding("f", "favorite_item", "Pin", show=True),
        Binding("/", "toggle_search", "Search", show=True),
        Binding("enter", "run_item('swap')", "Swap", show=True),
        Binding("shift+enter", "run_item('push')", "New Tab", show=True),
        Binding("ctrl+enter", "run_item('replace')", "Replace", show=True),
        Binding("alt+e", "edit_default", "Set Default", show=True),
        Binding("escape", "go_back", "Back", show=True),
        Binding("backspace", "go_back", "Back", show=False),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, context: str = "home"):
        super().__init__()
        self.current_context = context
        self.all_items = []
        self.context_stack = [context]
        self.current_layout = "list"
        self.current_title = "Nexus Hub v2.2.0"

    def compose(self) -> ComposeResult:
        with Container(id="main-container"):
            yield Label(self.current_title, id="header")
            # Both views coexist, we toggle visibility
            yield ListView(id="menu-list")
            with Container(id="grid-wrapper"):
                yield Container(id="menu-grid")
            yield Input(placeholder="/search...", id="search-bar")
            yield Label("", id="status-bar")

    def on_mount(self) -> None:
        self.refresh_items()

    def on_key(self, event: events.Key) -> None:
        """Global key logger and dispatcher."""
        search_bar = self.query_one("#search-bar")
        if search_bar.has_focus:
            return  # Let search bar handle input
        
        # Note: Basic navigation (j, k, h, l, enter, escape) is handled via BINDINGS.
        # This handler can be used for more complex conditional logic if needed.
        pass

    def refresh_items(self) -> None:
        items_raw = []
        try:
            items_raw = menu_engine.get_items(self.current_context)
        except Exception as e:
            items_raw = [menu_engine.fmt(f"Error in engine: {e}", "ERROR", "NONE")]
        
        list_view = self.query_one("#menu-list", ListView)
        grid_view = self.query_one("#menu-grid", Container)
        
        list_view.clear()
        self.all_items = [] # FIX: Clear item registry
        # Clear grid children manually
        for child in grid_view.children:
            child.remove()
        
        # Detect Layout and Root Metadata from the first item
        self.current_layout = "list"
        if items_raw:
            try:
                first_data = json.loads(items_raw[0])
                if "_root" in first_data:
                    self.current_layout = first_data["_root"].get("layout", "list")
                    self.current_title = first_data["_root"].get("name", "Nexus")
            except:
                pass

        # Apply Layout Visibility using CSS classes
        display_list = self.current_layout == "list"
        grid_wrapper = self.query_one("#grid-wrapper", Container)
        if display_list:
            list_view.remove_class("hidden")
            grid_view.add_class("hidden")
            grid_wrapper.add_class("hidden")
        else:
            list_view.add_class("hidden")
            grid_view.remove_class("hidden")
            grid_wrapper.remove_class("hidden")

        self.update_status(f"Loading {self.current_context}...")
        
        for item_json in items_raw:
            try:
                data = json.loads(item_json)
                
                if not isinstance(data, dict):
                    # Fallback for weird strings if somehow passed as raw JSON
                    label = str(data)
                    e_type = "ACTION"
                    payload = str(data)
                else:
                    label = data.get("label") or data.get("name")
                    e_type = data.get("type", "ACTION")
                    payload = data.get("payload", "NONE")
                    
                # Intelligent Labeling (Axiom: Sanity Fallback)
                if not label or label == "Unknown":
                    if ":" in payload: label = payload.split(":")[-1].replace("_", " ").capitalize()
                    elif "/" in payload: label = Path(payload).name
                    else: label = payload

                # Skip SEPARATOR items in grid mode
                if e_type == "SEPARATOR" and self.current_layout != "list":
                    continue
                
                if self.current_layout == "list":
                    is_disabled = (e_type in ("SEPARATOR", "DISABLED"))
                    item = NexusListItem(label, e_type, payload, disabled=is_disabled)
                    item.meta = data
                    self.all_items.append(item)
                    list_view.append(item)
                else:
                    if e_type == "SEPARATOR": continue
                    tile = NexusTile(label, e_type, payload, meta=data)
                    self.all_items.append(tile)
                    grid_view.mount(tile)
                    
            except Exception as e:
                with open("/tmp/nexus_menu_debug.log", "a") as f:
                    f.write(f"[UI] Refresh Failed on: {item_json} | Error: {e}\n")
                # Last resort: Try splitting as TSV if it's not JSON
                if isinstance(item_json, str) and "\t" in item_json:
                    parts = item_json.split("\t")
                    if len(parts) >= 3:
                        item = NexusListItem(parts[0].strip(), parts[1].strip(), parts[2].strip())
                        self.all_items.append(item)
                        list_view.append(item)

        if display_list and list_view.children:
            list_view.index = 0
            list_view.focus()
            self.update_status(f"ListView: {len(list_view.children)} items")
        elif not display_list and grid_view.children:
            # Re-mount focus strategy
            try:
                tiles = list(grid_view.query(NexusTile))
                if tiles:
                    tiles[0].focus()
                    self.update_status(f"Grid: {len(tiles)} items")
            except:
                pass
            
        # Update Header
        try:
            self.query_one("#header", Label).update(f" {self.current_title} ")
        except:
            pass

    def update_status(self, msg: str) -> None:
        try:
            self.query_one("#status-bar", Label).update(msg)
        except:
            pass

    def action_cursor_down(self) -> None:
        if self.query_one("#search-bar").has_focus:
            return
        if self.current_layout == "list":
            self.query_one("#menu-list").action_cursor_down()
        else:
            # Grid: move focus to next tile below
            self._move_grid_focus(0, 1)

    def action_cursor_up(self) -> None:
        if self.query_one("#search-bar").has_focus:
            return
        if self.current_layout == "list":
            self.query_one("#menu-list").action_cursor_up()
        else:
            # Grid: move focus to next tile above
            self._move_grid_focus(0, -1)

    def action_cursor_left(self) -> None:
        if self.query_one("#search-bar").has_focus:
            return
        if self.current_layout == "list":
            self.action_go_back()
        else:
            # Grid: move focus to next tile left
            self._move_grid_focus(-1, 0)

    def action_cursor_right(self) -> None:
        if self.query_one("#search-bar").has_focus:
            return
        if self.current_layout == "list":
            self.action_item("run")
        else:
            # Grid: move focus to next tile right
            self._move_grid_focus(1, 0)

    def _move_grid_focus(self, dx: int, dy: int) -> None:
        """Navigate grid tiles by delta x/y."""
        grid_view = self.query_one("#menu-grid", Container)
        tiles = list(grid_view.query(NexusTile))
        if not tiles:
            return
        
        # Find currently focused tile index
        current_idx = -1
        for i, tile in enumerate(tiles):
            if tile.has_focus:
                current_idx = i
                break
        
        if current_idx == -1:
            tiles[0].focus()
            return
        
        # Calculate grid dimensions (4 columns)
        cols = 4
        rows = (len(tiles) + cols - 1) // cols
        
        current_row = current_idx // cols
        current_col = current_idx % cols
        
        new_row = max(0, min(rows - 1, current_row + dy))
        new_col = max(0, min(cols - 1, current_col + dx))
        
        new_idx = new_row * cols + new_col
        if new_idx < len(tiles):
            tiles[new_idx].focus()

    def action_toggle_search(self) -> None:
        search_bar = self.query_one("#search-bar")
        search_bar.toggle_class("-visible")
        if search_bar.has_class("-visible"):
            search_bar.focus()
        else:
            if self.current_layout == "list":
                self.query_one("#menu-list").focus()
            else:
                tiles = list(self.query("#menu-grid NexusTile"))
                if tiles:
                    tiles[0].focus()

    def action_go_back(self) -> None:
        """Go back one context level or close search."""
        search_bar = self.query_one("#search-bar")
        if search_bar.has_focus:
            search_bar.remove_class("-visible")
            search_bar.value = ""
            self.on_input_changed(events.InputChanged(search_bar, ""))
            if self.current_layout == "list":
                self.query_one("#menu-list").focus()
            else:
                tiles = list(self.query("#menu-grid NexusTile"))
                if tiles:
                    tiles[0].focus()
        elif len(self.context_stack) > 1:
            self.context_stack.pop()
            self.current_context = self.context_stack[-1]
            self.refresh_items()
        else:
            # Axiom: Escape at root context = Exit Menu (Return to Portal)
            self.exit()

    def on_input_changed(self, event: Input.Changed) -> None:
        search_term = event.value.lower()
        list_view = self.query_one("#menu-list", ListView)
        list_view.clear()
        
        for item in self.all_items:
            if search_term in item.label_text.lower() or search_term in item.payload.lower():
                list_view.append(item)
        
        if list_view.children:
            list_view.index = 0

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in search bar."""
        self.action_item("run")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle Enter/Selection in list."""
        self.action_run_item("swap")

    def action_run_item(self, intent: str = "swap") -> None:
        self.action_item("run", intent=intent)

    def action_edit_item(self) -> None:
        self.action_item("edit")

    def action_context_item(self) -> None:
        self.action_item("context")

    def action_favorite_item(self) -> None:
        self.action_item("favorite")

    def action_edit_default(self) -> None:
        """Trigger 'Set Default' flow for the highlighted role/module."""
        item = None
        if self.current_layout == "list":
            list_view = self.query_one("#menu-list", ListView)
            if list_view.highlighted_child:
                item = list_view.highlighted_child
        else:
            item = self.focused if isinstance(self.focused, NexusTile) else None
        
        if not item or item.e_type != "ROLE":
            self.update_status("Alt+e only works on Roles/Modules")
            return

        # Trigger specialized selection menu for this role
        role_name = item.payload.strip().lower()
        self.current_context = f"set_default:{role_name}"
        self.context_stack.append(self.current_context)
        self.refresh_items()

    def action_item(self, verb: str, intent: str = "swap") -> None:
        item = None
        if self.current_layout == "list":
            list_view = self.query_one("#menu-list", ListView)
            if list_view.highlighted_child:
                item = list_view.highlighted_child
        else:
            # For Grid, use focused child or first if none
            item = self.focused if isinstance(self.focused, NexusTile) else None
            if not item:
                tiles = list(self.query("#menu-grid NexusTile"))
                if tiles: item = tiles[0]
        
        with open("/tmp/nexus_menu_debug.log", "a") as f:
            if item:
                f.write(f"[UI] Action: {verb} | Label: {item.label_text} | Type: {item.e_type} | Payload: {item.payload}\n")
            else:
                f.write(f"[UI] Action: {verb} | No item focused/highlighted\n")

        if item:
            # Drill down logic for folders/planes
            if verb == "run" and item.e_type in ("PLANE", "FOLDER"):
                self.current_context = item.payload
                self.context_stack.append(self.current_context)
                self.refresh_items()
                return

            if verb == "edit":
                source_path = item.meta.get("source_path")
                if source_path:
                    # Deterministic editing of the source file/script
                    self.run_nexus_action("run", "ACTION", f"nvim {source_path}")
                    return

            # Otherwise, call nxs-action-dispatch
            self.run_nexus_action(verb, item.e_type, item.payload, intent=intent)

    def run_nexus_action(self, verb: str, e_type: str, payload: str, intent: str = "swap") -> None:
        # We need to suspend the TUI and run the command
        env = os.environ.copy()
        env["NXS_INTENT"] = intent
        env["NXS_CALLER"] = "menu"
        
        with self.suspend():
            try:
                dispatch_bin = BIN_DIR / "nxs-action-dispatch"
                subprocess.run([str(dispatch_bin), verb, e_type, payload], env=env)
            except Exception as e:
                with open("/tmp/nexus_menu_debug.log", "a") as f:
                    f.write(f"[UI] Error running action: {e}\n")
        
        if verb in ("favorite"): # Refresh if we pinned something
            self.refresh_items()

if __name__ == "__main__":
    initial_context = "home"
    
    # Robust argument parsing
    for i, arg in enumerate(sys.argv):
        if arg == "--context" and i + 1 < len(sys.argv):
            initial_context = sys.argv[i + 1].lower()
        elif not arg.startswith("-") and i > 0:
            # Positional argument context (nxm.py home)
            initial_context = arg.lower()
    
    app = NexusMenuApp(context=initial_context)
    app.run()
