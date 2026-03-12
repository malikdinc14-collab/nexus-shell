# Requirements: Project Profiles

## Functional Requirements
1.  **Profile Definition**: Profiles must be defined in YAML files (e.g., `profiles/focus.yaml`).
2.  **Activation**: The `:profile <name>` command must trigger the hot-swap.
3.  **Scoped Settings**: Profiles must be able to override:
    - `NEXUS_THEME`
    - `NEXUS_COMPOSITION`
    - `NEXUS_DAEMONS` (a list of services to ensure are running)
4.  **Persistence**: The active profile must be saved to `.nexus/state.json` or similar to persist across sessions.

## Technical Requirements
- **YAML Engine**: Use `yq` for parsing profile definitions.
- **Hot-Reloading**: Must not require a full shell restart (Tmux source + nvim RPC).
- **Inheritance**: (Optional) Profiles can inherit from a `base` profile.

## Non-Functional Requirements
- **Speed**: Profile switching should complete in under 500ms.
- **Transparency**: The HUD must immediately reflect the profile change.
