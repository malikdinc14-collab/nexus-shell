import sys
import os
import json
import importlib.util
from typing import List, Optional

from ...base import MenuCapability, AdapterManifest, CapabilityType

# We conditionally import Textual later inside the methods to keep it an optional dependency.
# The adapter will return False for is_available() if textual is missing.

class TextualMenuAdapter(MenuCapability):
    """
    Implementation of MenuCapability using the 'textual' Python library.
    This adapter dynamically checks for textual so it remains an optional dependency.
    """

    manifest = AdapterManifest(
        name="textual",
        capability_type=CapabilityType.MENU,
        priority=60,
    )

    @property
    def capability_type(self):
        from ...base import CapabilityType
        return CapabilityType.MENU

    @property
    def capability_id(self): return "textual"

    def is_available(self) -> bool:
        return importlib.util.find_spec("textual") is not None

    def show_menu(self, options: List[str], prompt: str = "Select:") -> Optional[str]:
        if not options:
            return None
        # Convert simple options into JSON protocol format for the pick() method
        items_json = [json.dumps({"label": opt, "type": "ACTION", "payload": opt}) for opt in options]
        
        # Inject metadata so the UI recognizes this layout
        if items_json:
            first = json.loads(items_json[0])
            first["_root"] = {"name": prompt, "layout": "list"}
            items_json[0] = json.dumps(first)
            
        selected = self.pick("menu", items_json)
        if selected:
            try:
                return json.loads(selected).get("payload")
            except:
                return selected
        return None

    def pick(self, context: str, items_json: List[str]) -> Optional[str]:
        if not items_json:
            return None

        # Deferred imports for optional dependency
        from textual.app import App, ComposeResult
        from textual.containers import Container
        from textual.widgets import Input, ListItem, ListView, Static, Label
        from textual.binding import Binding
        from textual import events
        from textual.reactive import reactive

        class NexusListItem(ListItem):
            def __init__(self, label: str, e_type: str, payload: str, raw_json: str, disabled: bool = False):
                super().__init__()
                self.label_text = label
                self.e_type = e_type
                self.payload = payload
                self.raw_json = raw_json
                if disabled:
                    self.can_focus = False

            def compose(self) -> ComposeResult:
                yield Label(f" {self.label_text}")

        class NexusTile(Static):
            def __init__(self, label: str, e_type: str, payload: str, raw_json: str, meta: dict = None):
                super().__init__()
                self.label_text = label
                self.e_type = e_type
                self.payload = payload
                self.raw_json = raw_json
                self.meta = meta or {}
                self.can_focus = True

            def compose(self) -> ComposeResult:
                icon = self.meta.get("icon", "📦")
                yield Label(self.label_text, classes="tile-label")
                yield Label(icon, classes="tile-icon")
                if "description" in self.meta:
                    yield Label(self.meta["description"], classes="tile-desc")

        class NexusMenuApp(App):
            CSS = """
            NexusMenuApp { background: transparent; padding: 0; margin: 0; }
            Screen { background: transparent; align: center middle; }
            #main-container { width: 100%; height: 100%; align: center middle; }
            #search-bar { dock: bottom; background: transparent; border: none; padding: 0 1; display: none; height: 1; }
            #search-bar.-visible { display: block; }
            #header { background: $accent 10%; color: $accent; padding: 0 1; height: 1; text-style: bold; content-align: center middle; dock: top; }
            ListView { background: transparent; border: none; max-width: 60; min-width: 20; width: auto; align: center top; margin: 1 2; }
            ListItem { padding: 0 1; background: transparent; }
            ListItem:hover { background: $accent 20%; }
            ListView > ListItem.--highlight { background: $accent 30%; color: $text; text-style: bold; }
            #menu-list.hidden { display: none; }
            #grid-wrapper { align: center middle; width: 100%; height: 1fr; padding: 1 2; }
            #menu-grid { layout: grid; grid-size: 4; grid-gutter: 1; padding: 1; overflow-y: auto; max-width: 80; min-width: 40; width: auto; max-height: 85%; align: center top; margin: 0 2; }
            #menu-grid.hidden, #grid-wrapper.hidden { display: none; }
            NexusTile { background: $surface; border: tall $background; content-align: center middle; padding: 1; height: auto; min-height: 5; min-width: 12; transition: background 200ms, border 200ms, offset 200ms; }
            NexusTile:focus { background: $accent 15%; border: tall $accent; text-style: bold; offset-y: -1; }
            #status-bar { background: $surface; color: $text-muted; height: 1; dock: bottom; padding: 0 1; content-align: center middle; }
            .tile-icon { height: 2; content-align: center middle; }
            .tile-label { height: 1; content-align: center middle; }
            .tile-desc { color: $text-muted; height: 1; content-align: center middle; }
            Footer { display: none; }
            """

            BINDINGS = [
                Binding("j", "cursor_down", "Down", show=False),
                Binding("k", "cursor_up", "Up", show=False),
                Binding("h", "cursor_left", "Left", show=False),
                Binding("l", "cursor_right", "Right", show=False),
                Binding("enter", "run_item", "Select", show=True),
                Binding("/", "toggle_search", "Search", show=True),
                Binding("escape", "go_back", "Back", show=True),
                Binding("q", "quit", "Quit", show=True),
            ]

            def __init__(self, context_name: str, items: List[str]):
                super().__init__()
                self.context_name = context_name
                self.items_json = items
                self.all_items = []
                self.current_layout = "list"
                self.current_title = f"Nexus Hub: {context_name}"
                self.result: Optional[str] = None

            def compose(self) -> ComposeResult:
                with Container(id="main-container"):
                    yield Label(self.current_title, id="header")
                    yield ListView(id="menu-list")
                    with Container(id="grid-wrapper"):
                        yield Container(id="menu-grid")
                    yield Input(placeholder="/search...", id="search-bar")
                    yield Label("", id="status-bar")

            def on_mount(self) -> None:
                list_view = self.query_one("#menu-list", ListView)
                grid_view = self.query_one("#menu-grid", Container)

                if self.items_json:
                    try:
                        first_data = json.loads(self.items_json[0])
                        if "_root" in first_data:
                            self.current_layout = first_data["_root"].get("layout", "list")
                            self.current_title = first_data["_root"].get("name", self.current_title)
                    except:
                        pass

                display_list = self.current_layout == "list"
                if display_list:
                    list_view.remove_class("hidden")
                    grid_view.add_class("hidden")
                    self.query_one("#grid-wrapper").add_class("hidden")
                else:
                    list_view.add_class("hidden")
                    grid_view.remove_class("hidden")
                    self.query_one("#grid-wrapper").remove_class("hidden")

                for item_json in self.items_json:
                    try:
                        data = json.loads(item_json)
                        if not isinstance(data, dict):
                            label, e_type, payload = str(data), "ACTION", str(data)
                        else:
                            label = data.get("label") or data.get("name", "Unknown")
                            e_type = data.get("type", "ACTION")
                            payload = data.get("payload", "NONE")

                        if e_type == "SEPARATOR" and not display_list:
                            continue

                        if display_list:
                            is_disabled = (e_type in ("SEPARATOR", "DISABLED"))
                            item = NexusListItem(label, e_type, payload, item_json, disabled=is_disabled)
                            self.all_items.append(item)
                            list_view.append(item)
                        else:
                            tile = NexusTile(label, e_type, payload, item_json, meta=data)
                            self.all_items.append(tile)
                            grid_view.mount(tile)
                    except Exception:
                        pass

                if display_list and list_view.children:
                    list_view.index = 0
                    list_view.focus()
                elif not display_list and grid_view.children:
                    for child in grid_view.children:
                        child.focus()
                        break

                self.query_one("#header", Label).update(f" {self.current_title} ")
                self.query_one("#status-bar", Label).update(f"Loaded {len(self.all_items)} items.")

            def get_focused_item(self):
                if self.current_layout == "list":
                    lv = self.query_one("#menu-list", ListView)
                    return lv.highlighted_child
                else:
                    return self.focused if isinstance(self.focused, NexusTile) else None

            def action_run_item(self) -> None:
                item = self.get_focused_item()
                if item:
                    self.result = item.raw_json
                    self.exit(self.result)

            def action_toggle_search(self) -> None:
                search_bar = self.query_one("#search-bar")
                search_bar.toggle_class("-visible")
                if search_bar.has_class("-visible"):
                    search_bar.focus()
                else:
                    if self.current_layout == "list":
                        self.query_one("#menu-list").focus()
                    else:
                        item = self.get_focused_item()
                        if item: item.focus()

            def action_go_back(self) -> None:
                search_bar = self.query_one("#search-bar")
                if search_bar.has_focus:
                    search_bar.remove_class("-visible")
                    search_bar.value = ""
                    self.on_input_changed(events.InputChanged(search_bar, ""))
                    self.action_toggle_search()
                    self.action_toggle_search() # focus reset
                else:
                    self.exit(None)

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
                self.action_run_item()

            def on_list_view_selected(self, event: ListView.Selected) -> None:
                self.action_run_item()
                
            def action_cursor_down(self) -> None:
                if self.query_one("#search-bar").has_focus: return
                if self.current_layout == "list": self.query_one("#menu-list").action_cursor_down()
                else: self._move_grid(0, 1)

            def action_cursor_up(self) -> None:
                if self.query_one("#search-bar").has_focus: return
                if self.current_layout == "list": self.query_one("#menu-list").action_cursor_up()
                else: self._move_grid(0, -1)

            def action_cursor_left(self) -> None:
                if self.query_one("#search-bar").has_focus: return
                if self.current_layout == "list": self.action_go_back()
                else: self._move_grid(-1, 0)

            def action_cursor_right(self) -> None:
                if self.query_one("#search-bar").has_focus: return
                if self.current_layout == "list": self.action_run_item()
                else: self._move_grid(1, 0)
                
            def _move_grid(self, dx: int, dy: int) -> None:
                grid_view = self.query_one("#menu-grid", Container)
                tiles = list(grid_view.query("NexusTile"))
                if not tiles: return
                current_idx = next((i for i, t in enumerate(tiles) if t.has_focus), 0)
                cols = 4
                rows = (len(tiles) + cols - 1) // cols
                r, c = current_idx // cols, current_idx % cols
                nr, nc = max(0, min(rows-1, r+dy)), max(0, min(cols-1, c+dx))
                n_idx = nr * cols + nc
                if n_idx < len(tiles): tiles[n_idx].focus()

        # Run the app synchronously and return result
        app = NexusMenuApp(context, items_json)
        # Using dev/tty to ensure textual can render appropriately if piped via nxs wrapper
        try:
            return app.run()
        except:
            return None
