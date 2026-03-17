# Extension-First Architecture Implementation

**Date:** 2026-03-16  
**Status:** Complete

---

## Overview

Nexus Shell has been refactored to use an **extension-first architecture** where everything except the absolute core is treated as a detectable, installable extension.

### Core Principle

```
Core (Never Extensions):
  - tmux (terminal multiplexer)
  - python3 (runtime)
  - zsh/bash (shell)

Everything Else: Extension with Smart Detection
```

---

## Implementation Summary

### Statistics

| Metric | Value |
|--------|-------|
| Total Extensions | 47 |
| Categories | 14 |
| Core Files Created | 2 |
| Core Files Modified | 5 |

---

## Files Created

### Core System

| File | Lines | Purpose |
|------|-------|---------|
| `core/engine/lib/detector.sh` | ~200 | System tool detection engine |
| `core/kernel/boot/first_run.sh` | ~250 | Interactive first-run wizard |

### Extensions

All extensions follow the manifest schema:

```yaml
name: <tool>
version: 1.0.0
type: tool
category: <category>
description: <desc>
binary: <binary-name>
role: <role>           # Which Nexus role this provides
role_priority: 100     # Higher = preferred for this role
install:
  macos: [brew install <tool>]
  linux: [apt install <tool>]
```

**Extension Categories:**

| Category | Count | Extensions |
|----------|-------|------------|
| editor | 4 | nvim, helix, micro, code |
| explorer | 4 | yazi, nnn, ranger, lf |
| chat | 2 | opencode, gptme |
| terminal | 1 | zellij |
| viewer | 3 | glow, bat, nxs-view |
| search | 3 | grepai, television, ripgrep |
| devops | 5 | k9s, lazydocker, lazygit, dive, process-compose |
| ai | 2 | optillm, openevolve |
| monitor | 4 | btop, bottom, glances, bandwhich |
| media | 3 | ncspot, cava, spotify-player |
| database | 3 | harlequin, lazysql, sc-im |
| network | 3 | termshark, trippy, termscp |
| git | 3 | lazygit, gh-dash, serie |
| utility | 7 | fzf, gum, presenterm, slumber, posting, taskwarrior-tui, visidata |

---

## Files Modified

### 1. `core/kernel/boot/launcher.sh`

**Changes:**
- Added first-run check (lines ~48-55)
- Added profile loading function `load_profile_env()`
- Added dynamic tool resolution function `get_tool_for_role()`
- Replaced hardcoded tool defaults with dynamic resolution

**Before:**
```bash
export NEXUS_EDITOR="${NEXUS_EDITOR:-nvim}"
export NEXUS_FILES="${NEXUS_FILES:-yazi}"
```

**After:**
```bash
export NEXUS_EDITOR="${NEXUS_EDITOR:-$(get_tool_for_role editor)}"
export NEXUS_FILES="${NEXUS_FILES:-$(get_tool_for_role explorer)}"
```

### 2. `core/kernel/boot/doctor.sh`

**Changes:**
- Complete rewrite to be extension-aware
- Uses detector.sh for tool detection
- Shows profile status
- Displays detected tools by role
- Lists extension status

### 3. `bin/nxs`

**New Commands:**
```bash
nxs profile show     # Display current profile
nxs profile edit     # Open profile in $EDITOR
nxs profile reset    # Delete profile and first-run flag
nxs profile detect   # Re-run tool detection
nxs profile roles    # Show configured roles
nxs wizard           # Run first-run wizard manually
```

### 4. `config/modules.yaml`

**Changes:**
- Added documentation about priority hierarchy
- Added role_descriptions for wizard
- Simplified to reference profile system

### 5. `extensions/loader.sh`

**New Functions:**
- `list_all_extensions()` - Detailed listing for fzf
- `list_by_category()` - Filter by category
- `find_manifest()` - Locate manifest by extension name
- `find_ext_dir()` - Find extension directory
- Enhanced category support for nested structure

---

## New Architecture

### Profile System

**Location:** `~/.nexus/profile.yaml`

```yaml
version: 1
created: 2026-03-16T20:00:00Z
last_modified: 2026-03-16T20:00:00Z

detected:
  editor: nvim
  explorer: yazi
  chat: opencode

roles:
  editor: nvim
  explorer: yazi
  chat: opencode
  terminal: zellij
  viewer: glow
  search: grepai

extensions:
  - grepai
  - lazygit

preferences:
  first_run_complete: true
```

### Priority Hierarchy

```
1. Environment Variables (highest)
   NEXUS_EDITOR=helix nxs boot
   
2. User Profile
   ~/.nexus/profile.yaml roles section
   
3. Detected Tools
   ~/.nexus/profile.yaml detected section
   
4. System Fallbacks (lowest)
   editor: vi, explorer: ls, etc.
```

### First-Run Wizard Flow

```
┌─────────────────────────────────────┐
│  WELCOME BANNER                     │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  PHASE 1: SYSTEM SCAN               │
│  - Detect installed tools           │
│  - Map tools to roles               │
│  - Display detected: ✓/○            │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  PHASE 2: ROLE ASSIGNMENT           │
│  - For each role:                   │
│    - Show detected tool             │
│    - Accept or change               │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  PHASE 3: EXTENSION SUGGESTIONS     │
│  - Suggest extensions for missing   │
│  - fzf multi-select                 │
│  - Install selected                 │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  PHASE 4: OPTIONAL EXTENSIONS       │
│  - Browse all extensions            │
│  - Select additional tools          │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  COMPLETE                           │
│  - Save profile.yaml                │
│  - Set first_run_complete flag      │
└─────────────────────────────────────┘
```

---

## CLI Commands Reference

### Extension Management

```bash
# List all extensions
nxs extension list

# List by category
nxs extension list-category editor

# Show extension info
nxs extension info nvim

# Install extension
nxs extension install grepai

# Uninstall extension
nxs extension uninstall grepai

# View categories
nxs extension categories
```

### Profile Management

```bash
# Show profile
nxs profile show

# Edit profile
nxs profile edit

# Reset profile (re-run wizard on next boot)
nxs profile reset

# Re-detect tools
nxs profile detect

# Show configured roles
nxs profile roles
```

### System

```bash
# Run first-run wizard
nxs wizard

# Health check (extension-aware)
nxs doctor
```

---

## Directory Structure

```
extensions/
├── .registry.json          # Auto-generated extension index
├── loader.sh               # Extension manager
├── README.md               # Extension documentation
│
├── ai/
│   ├── openevolve/manifest.yaml
│   └── optillm/manifest.yaml
│
├── chat/
│   ├── opencode/manifest.yaml
│   └── gptme/manifest.yaml
│
├── database/
│   ├── harlequin/manifest.yaml
│   ├── lazysql/manifest.yaml
│   └── sc-im/manifest.yaml
│
├── devops/
│   ├── k9s/manifest.yaml
│   ├── lazydocker/manifest.yaml
│   ├── lazygit/manifest.yaml
│   ├── dive/manifest.yaml
│   └── process-compose/manifest.yaml
│
├── editor/
│   ├── nvim/manifest.yaml
│   ├── helix/manifest.yaml
│   ├── micro/manifest.yaml
│   └── code/manifest.yaml
│
├── explorer/
│   ├── yazi/manifest.yaml
│   ├── nnn/manifest.yaml
│   ├── ranger/manifest.yaml
│   └── lf/manifest.yaml
│
├── git/
│   ├── lazygit/manifest.yaml
│   ├── gh-dash/manifest.yaml
│   └── serie/manifest.yaml
│
├── media/
│   ├── ncspot/manifest.yaml
│   ├── cava/manifest.yaml
│   └── spotify-player/manifest.yaml
│
├── monitor/
│   ├── btop/manifest.yaml
│   ├── bottom/manifest.yaml
│   ├── glances/manifest.yaml
│   └── bandwhich/manifest.yaml
│
├── network/
│   ├── termshark/manifest.yaml
│   ├── trippy/manifest.yaml
│   └── termscp/manifest.yaml
│
├── search/
│   ├── grepai/
│   │   ├── manifest.yaml
│   │   ├── bin/nxs-grepai
│   │   ├── hooks/search_provider.sh
│   │   ├── hooks/menu_provider.sh
│   │   ├── mcp/register.sh
│   │   └── config/grepai.yaml
│   ├── television/manifest.yaml
│   └── ripgrep/manifest.yaml
│
├── terminal/
│   └── zellij/manifest.yaml
│
├── utility/
│   ├── fzf/manifest.yaml
│   ├── gum/manifest.yaml
│   ├── presenterm/manifest.yaml
│   ├── slumber/manifest.yaml
│   ├── posting/manifest.yaml
│   ├── taskwarrior-tui/manifest.yaml
│   └── visidata/manifest.yaml
│
└── viewer/
    ├── glow/manifest.yaml
    ├── bat/manifest.yaml
    └── nxs-view/manifest.yaml
```

---

## Backwards Compatibility

### Preserved

- `scripts/installers/` - Kept as archive
- `config/modules.yaml` - Still works as fallback
- Environment variables - Highest priority
- All existing compositions - Work unchanged

### Migration Notes

- Old `setup_wizard.sh` superseded by `first_run.sh`
- Tool detection now automatic via extensions
- Profile system is new but optional

---

## Future Enhancements

### Potential Additions

1. **Extension Auto-Update**
   ```bash
   nxs extension update grepai
   nxs extension update-all
   ```

2. **Extension Search**
   ```bash
   nxs extension search "kubernetes"
   ```

3. **Extension Dependencies**
   - Auto-install dependencies when installing extension

4. **Extension Hooks**
   - `boot_provider.sh` - Run at station boot
   - `shutdown_provider.sh` - Run at station stop

5. **Remote Extensions**
   ```bash
   nxs extension add https://github.com/user/nxs-myext
   ```

---

## Testing Checklist

- [x] `nxs extension list` shows all 47 extensions
- [x] `nxs extension info <name>` works
- [x] `nxs profile detect` outputs JSON
- [x] `nxs doctor` shows detected tools
- [x] `nxs wizard` runs (interactive)
- [x] Extension categories correct
- [x] Installed tools show ✓
- [x] Missing tools show ○
- [x] First-run check triggers wizard
- [x] Profile loading works

---

## Notes

- The `grepai` extension includes full hooks (search, menu, MCP)
- Other extensions are manifest-only (no install scripts yet)
- Install scripts can be added per-extension as needed
- The system gracefully handles missing tools (falls back to vi, ls, etc.)
