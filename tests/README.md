# Nexus Shell Test Suite

This directory contains the automated tests for Nexus Shell.

## Structure
- `/unit`: Functional tests for individual scripts in `core/` and `lib/`.
- `/integration`: Lifecycle tests for Tmux sessions and multi-pane orchestration.

## Execution
We use [BATS](https://github.com/bats-core/bats-core) for testing.

```bash
# Example run
bats tests/unit/profile_loader_test.bats
```

## Jules's Backlog
- [ ] Implement `tests/unit/workspace_manager_test.bats`: Test JSON parsing and path merging.
- [ ] Implement `tests/unit/telemetry_aggregator_test.bats`: Test JSON state updates.
- [ ] Implement `tests/unit/jump_regex_test.bats`: Test extraction of stack trace patterns.
