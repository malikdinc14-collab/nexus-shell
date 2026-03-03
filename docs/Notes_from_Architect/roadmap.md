# Nexus-Menu Roadmap

This document outlines the next priorities and potential issues following the transition to the "Dumb Menu" architecture (where the menu is a pure UI that pipes stdout to `nxs-router`).

## Priorities & Next Steps

1. **Refine execution routes in `nxs-router`**:
   - Determine how `PLACE`, `ACTION`, `NOTE/DOC`, and `MODEL/AGENT` should be handled ideally.
   - Example behavior tuning: How should the router manipulate Tmux panes? Should it open `NOTE` in the editor pane or spawn a new one?

2. **Refactor the Core Pillars (`Places`, `Notes`, `Projects`)**:
   - The original pillars inside `modules/menu/lib/core/pillars/` still output legacy dictionaries.
   - We must update them to ensure they push clean, predictable Taxonomy strings (e.g. `PLACE|/dir`) that the router understands.

3. **Develop the `user_lists` Pillar**:
   - Build a dynamic pillar that reads user-defined `*.yaml` files from `.nexus/lists/` inside the active project workspace.
   - Automatically parse these lists into custom actions or places that get fed through to the menu and router.

4. **Address User-Reported Layout Issues**:
   - The "Module Selectors" (where you pick which tool goes in which pane) are currently broken for Editor and Render, and they should be replaced with native `nexus-menu` lists instead of whatever custom selector they use now.
   - Re-evaluate **Yazi** as the default explorer. Its default 3-way split (with preview) is too bulky for a slim IDE sidebar.
     - *Goal*: An IDE typically has an Explorer (file tree), Editor, Renderer/Viewer, Chat Pane, and Terminal (Bash/Zsh). We need to align the default `vscodelike` layout to spawn these standard components out of the box.
