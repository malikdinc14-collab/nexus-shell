# Contributing to Nexus Shell

Welcome to the Nexus Shell project! We aim to build the most modular and high-performance terminal IDE framework.

## Repository Structure
- `bin/`: CLI entry point (`nxs`).
- `core/`: Internal system logic (layout engine, API, boot scripts, themes).
- `config/`: Default and user-specific configurations.
- `modules/`: Feature-specific modules (editor, chat, web).
- `docs/`: Documentation and architectural specs.
- `scripts/`: Maintenance scripts and installers.

## Development Workflow
1. **Setup**: Run `make install` to set up your environment.
2. **Changes**: Keep the `core/` lean. Move feature-specific logic to `modules/`.
3. **Quality**: Run `make lint` before submitting a PR.
4. **Docs**: Update `SOVEREIGN_INDEX.md` if you add new documentation.

## Standards
- **Shell**: Use `zsh` or `bash`. Ensure scripts are `shellcheck` clean.
- **Python**: Use Python 3.11+. Follow PEP 8 (enforced by `ruff`).
- **AI**: All new features should consider "Agentic Sovereignty" and follow the GAP protocol where applicable.
