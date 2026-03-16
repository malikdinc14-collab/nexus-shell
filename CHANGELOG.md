# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-03-15
### Added
- Unified CLI dispatcher (`bin/nxs`) with subcommands: `boot`, `list`, `doctor`, `status`.
- Modular `doctor.sh` health check.
- `Makefile` for developer lifecycle (install, lint, test, doctor).
- `pyproject.toml` for Python dependency management.
- `CONTRIBUTING.md` and `CHANGELOG.md`.

### Changed
- **Aggressive Repository Reorganization**: Consolidated internal logic into `core/`, documentation into `docs/`, and installers into `scripts/`.
- Updated path references across all core scripts to support the "Pro" repository structure.
- Professionalized the repository root by pruning legacy and redundant files.

### Fixed
- Infinite recursion issue in `nexus-shell` indexing caused by circular symlinks.
