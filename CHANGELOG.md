# Changelog

All notable changes to Nexus Shell will be documented in this file.

## [2.2.0] - 2026-03-16

### Added - Extension-First Architecture

**Core System:**
- `core/lib/detector.sh` - System tool detection engine with JSON output
- `core/boot/first_run.sh` - Interactive first-run wizard with tool detection
- Extension categories: 14 categories (editor, explorer, chat, terminal, viewer, search, devops, ai, monitor, media, database, network, git, utility)
- 47 extension manifests for common CLI/TUI tools

**New Commands:**
- `nxs wizard` - Run first-run setup wizard
- `nxs profile show` - Display current profile configuration
- `nxs profile edit` - Open profile in $EDITOR
- `nxs profile reset` - Delete profile and first-run flag
- `nxs profile detect` - Re-run tool detection
- `nxs profile roles` - Show configured roles
- `nxs extension list` - List all extensions by category
- `nxs extension categories` - List all extension categories

**Profile System:**
- `~/.nexus/profile.yaml` - User profile storing detected tools, role assignments, and preferences
- Priority hierarchy: Environment > Profile > Detected > Fallback
- Per-role prompts during first-run wizard

**Modified:**
- `core/boot/launcher.sh` - Added first-run check, profile loading, dynamic tool resolution
- `core/boot/doctor.sh` - Extension-aware diagnostics with detected tools display
- `bin/nxs` - Added profile and wizard commands
- `config/modules.yaml` - Updated to reference profile system
- `extensions/loader.sh` - Enhanced with category support, nested structure

**Architecture:**
- Pure core: tmux, python3, shell (never extensions)
- Everything else: detectable extension
- Smart detection via `command -v` for installed tools
- First-run experience with per-role tool selection

### Changed
- Moved `core/`, documentation into `docs/`, and installers into `scripts/`.
- Updated path references across all core scripts to support the "Pro" repository structure.
- Professionalized the repository root by pruning legacy and redundant files.

### Fixed
- Infinite recursion issue in `nexus-shell` indexing caused by circular symlinks.
