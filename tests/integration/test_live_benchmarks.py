"""Live benchmark stubs for T090-T092: require live tmux session.

These tests are skipped by default. They serve as documentation for
manual or CI verification with a real tmux environment.
"""

import pytest


@pytest.mark.skip(reason="requires live tmux session")
def test_install_timing():
    """T090: measures nexus-shell install time (target < 2s).

    Steps:
    1. Run install.sh in a clean environment
    2. Measure wall-clock time from start to completion
    3. Assert total < 2.0 seconds
    """


@pytest.mark.skip(reason="requires live tmux session")
def test_alt_m_menu_open():
    """T091: measures Alt+m to menu display latency (target < 200ms).

    Steps:
    1. Start nexus-shell in a tmux session
    2. Send Alt+m key sequence via tmux send-keys
    3. Measure time until menu content appears in pane output
    4. Assert latency < 200ms
    """


@pytest.mark.skip(reason="requires live tmux session")
def test_workspace_save_restore_e2e():
    """T092: full workspace save/restore through tmux.

    Steps:
    1. Start nexus-shell, open multiple panes with different capabilities
    2. Run nexus-ctl workspace save
    3. Kill session, restart, run nexus-ctl workspace restore
    4. Verify all panes, tabs, and geometry are restored
    """


@pytest.mark.skip(reason="requires live tmux session")
def test_all_keybindings_functional():
    """T092: verifies all Alt+key bindings are registered in tmux.

    Steps:
    1. Start nexus-shell in a tmux session
    2. Query tmux list-keys for all M-{key} bindings
    3. Verify all 13 required Alt+key bindings are present
    4. Send each key and verify the correct handler is invoked
    """
