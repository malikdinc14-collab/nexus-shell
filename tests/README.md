# Nexus Shell Test Suite (The Indestructible Shield)

This suite is the primary defensive layer of the Nexus Factory.

## Target: THE CORE (Jules's Mission)
The following unit tests MUST be implemented using BATS to ensure Phase 4/5 stability.

### 1. `tests/unit/workspace_manager.bats`
- **Verify**: Correct merging of multiple roots into `NEXUS_ROOTS`.
- **Verify**: Handling of empty or malformed `.nxs-workspace` files.

### 2. `tests/unit/profile_loader.bats`
- **Verify**: Correct parsing of `config/profiles/*.yaml`.
- **Verify**: Theme and Composition variables are correctly exported based on selection.

### 3. `tests/unit/telemetry_aggregator.bats`
- **Verify**: Atomic writes to `/tmp/nexus_telemetry.json`.
- **Verify**: Detection of Learner Level (Ascent) and Git Branch.

### 4. `tests/unit/jump_extraction.bats`
- **Verify**: Regex extraction of `file:line` for Python, Rust, and Node.js traces.
- **Verify**: Filtering of non-existent files.

### 5. `tests/unit/launcher_logic.bats` (CRITICAL)
- **Verify**: Identity Guard prevents recursive Nexus sessions.
- **Verify**: Multi-window lookup logic finds the correct available slot (0-9).
- **Mocking**: You MUST mock the `tmux` command to simulate session/window states.

## Execution
Run all tests: `bats tests/unit/*.bats`
Check coverage: `kcov tests/coverage bats tests/unit/*.bats` (Optional but recommended)

**STATUS**: Awaiting Implementation by Jules.
