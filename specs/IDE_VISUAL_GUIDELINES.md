# Visual Design Guidelines: Nexus High-Fidelity IDE

**Status**: V1.0
**Objective**: Ensure consistent, premium aesthetics across all Nexus-Shell modules.

---

## 1. Typography & Icons
Nexus-Shell expects a **Nerd Font** (e.g., JetBrainsMono, FiraCode) to be installed on the host terminal.

### Standard Icons
- **Files**: `󰈚` (Generic), `` (Python), `` (Rust), `󰨡` (TS)
- **Status**: `●` (Dirty/Unsaved), `✔` (Success), `✖` (Error), `⚠` (Warning)
- **Git**: `` (Branch), `󰃐` (Thinking/Working)
- **Separators**: `` (Breadcrumb Arrow), `|` (Vertical Divider)

---

## 2. Color Palette (Cyber Theme Base)
Use these TMUX format color tokens for consistent UI rendering:

- **Primary**: `cyan` / `#00ffff` (Active Tab, Interactive elements)
- **Secondary**: `magenta` / `#ff00ff` (AI indicators, Special highlights)
- **Success**: `green` / `#00ff00`
- **Warning**: `yellow` / `#ffff00`
- **Error**: `red` / `#ff0000`
- **Subdued**: `white,dim` / `#666666` (Inactive tabs, breadcrumbs)

---

## 3. UI Component Models

### Tab Bar (Local per Pane)
- **Active**: `#[bg=cyan,fg=black,bold]  󰈚 main.py  #[default]`
- **Inactive**: `#[fg=white,dim]  󰈚 utils.sh  #[default]`
- **Dirty**: `#[fg=yellow]●#[default]`

### Breadcrumbs (Top of Editor)
`#{pane_title} #[fg=white,dim] core  boot  #[fg=cyan,bold]launcher.sh#[default]`

### Global Status Bar (Bottom)
` NEXUS #[fg=white]| #[fg=cyan]󱓞 󱓟 Pilot Mode #[fg=white]|  main #[fg=white]| #{?window_zoomed_flag,#[fg=magenta,bold][ZOOM] ,}✖ 2 ⚠ 1 `

---

## 4. Interaction Principles
1. **Snappy Transitions**: No long animations. Use `refresh-client` immediately on state change.
2. **Contextual Focus**: The `M-1` through `M-5` keys should use high-contrast border colors to clearly indicate which quadrant has focus.
3. **Ghosting**: Inactive areas of the IDE should dim slightly to prioritize the active work area.
