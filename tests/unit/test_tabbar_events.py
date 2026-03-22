"""Tests for tab bar renderer (T014) and tmux event wiring (T015)."""

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Ensure engine.* imports resolve
sys.path.insert(0, str(PROJECT_ROOT / "core"))


def _load_module(name, rel_path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


stack_mod = _load_module("engine.stacks.stack", "core/engine/stacks/stack.py")
tabbar_mod = _load_module("engine.stacks.tabbar", "core/engine/stacks/tabbar.py")
events_mod = _load_module("engine.stacks.tmux_events", "core/engine/stacks/tmux_events.py")

Tab = stack_mod.Tab
TabStack = stack_mod.TabStack
render_tab_bar = tabbar_mod.render_tab_bar
render_for_pane = tabbar_mod.render_for_pane
generate_hook_commands = events_mod.generate_hook_commands
generate_pane_border_refresh = events_mod.generate_pane_border_refresh
install_hooks = events_mod.install_hooks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stack(*tab_specs, active_index=0):
    """Create a TabStack from (capability_type, role) tuples."""
    tabs = []
    for i, spec in enumerate(tab_specs):
        cap_type, role = spec if isinstance(spec, tuple) else (spec, None)
        tabs.append(Tab(
            capability_type=cap_type,
            adapter_name="test",
            role=role,
            is_active=(i == active_index),
        ))
    s = TabStack(pane_id="%1", tabs=tabs, active_index=active_index)
    return s


# ===========================================================================
# Tab Bar Renderer Tests (T014)
# ===========================================================================

class TestRenderTabBar:
    """Tests for render_tab_bar."""

    def test_single_active_tab_cyan_bold(self):
        stack = _make_stack("editor")
        result = render_tab_bar(stack)
        assert "#[fg=cyan,bold]" in result
        assert "[e]" in result

    def test_multiple_tabs_active_highlighted(self):
        stack = _make_stack("editor", "terminal", active_index=0)
        result = render_tab_bar(stack)
        parts = result.split(" ")
        assert len(parts) == 2
        assert "#[fg=cyan,bold][e]#[default]" == parts[0]
        assert "#[fg=white,dim][t]#[default]" == parts[1]

    def test_on_demand_hides_single_tab(self):
        stack = _make_stack("editor")
        result = render_tab_bar(stack, mode="on-demand")
        assert result == ""

    def test_on_demand_shows_multiple_tabs(self):
        stack = _make_stack("editor", "terminal")
        result = render_tab_bar(stack, mode="on-demand")
        assert result != ""
        assert "[e]" in result
        assert "[t]" in result

    def test_off_mode_always_empty(self):
        stack = _make_stack("editor", "terminal", "chat")
        result = render_tab_bar(stack, mode="off")
        assert result == ""

    def test_tab_with_role_shows_role(self):
        stack = _make_stack(("terminal", "build"))
        result = render_tab_bar(stack)
        assert "[build]" in result
        assert "[t]" not in result

    def test_empty_stack_returns_empty(self):
        stack = TabStack(pane_id="%1", tabs=[])
        result = render_tab_bar(stack)
        assert result == ""

    def test_render_for_pane_reads_config_mode(self):
        stack = _make_stack("editor")
        config = {"tabbar": {"mode": "off"}}
        result = render_for_pane(stack, config)
        assert result == ""

    def test_render_for_pane_default_config(self):
        stack = _make_stack("editor")
        result = render_for_pane(stack, {})
        assert "#[fg=cyan,bold][e]#[default]" in result

    def test_chat_tab_shows_c(self):
        stack = _make_stack("chat", active_index=0)
        result = render_tab_bar(stack)
        assert "[c]" in result

    def test_active_index_respected(self):
        stack = _make_stack("editor", "terminal", active_index=1)
        parts = result = render_tab_bar(stack).split(" ")
        assert "#[fg=white,dim][e]#[default]" == parts[0]
        assert "#[fg=cyan,bold][t]#[default]" == parts[1]


# ===========================================================================
# tmux Event Wiring Tests (T015)
# ===========================================================================

NEXUS_HOME = "/opt/nexus-shell"


class TestGenerateHookCommands:
    """Tests for generate_hook_commands."""

    def test_returns_correct_number_of_hooks(self):
        hooks = generate_hook_commands(NEXUS_HOME)
        assert len(hooks) == 3

    def test_after_split_window_contains_create_anonymous(self):
        hooks = generate_hook_commands(NEXUS_HOME)
        split_hook = [h for h in hooks if "after-split-window" in h]
        assert len(split_hook) == 1
        assert "create-anonymous" in split_hook[0]

    def test_pane_died_contains_cleanup(self):
        hooks = generate_hook_commands(NEXUS_HOME)
        died_hook = [h for h in hooks if "pane-died" in h]
        assert len(died_hook) == 1
        assert "cleanup" in died_hook[0]

    def test_after_kill_pane_contains_cleanup(self):
        hooks = generate_hook_commands(NEXUS_HOME)
        kill_hook = [h for h in hooks if "after-kill-pane" in h]
        assert len(kill_hook) == 1
        assert "cleanup" in kill_hook[0]

    def test_all_hooks_use_run_shell(self):
        hooks = generate_hook_commands(NEXUS_HOME)
        for hook in hooks:
            assert "run-shell" in hook

    def test_all_hooks_use_global_flag(self):
        hooks = generate_hook_commands(NEXUS_HOME)
        for hook in hooks:
            assert "-g" in hook

    def test_hooks_use_nexus_home_path(self):
        custom_home = "/home/user/.nexus"
        hooks = generate_hook_commands(custom_home)
        for hook in hooks:
            assert custom_home in hook


class TestGeneratePaneBorderRefresh:
    """Tests for generate_pane_border_refresh."""

    def test_contains_python3_path(self):
        result = generate_pane_border_refresh(NEXUS_HOME)
        assert "python3" in result

    def test_uses_correct_script_path(self):
        result = generate_pane_border_refresh(NEXUS_HOME)
        assert f"{NEXUS_HOME}/core/engine/stacks/render_border.py" in result

    def test_contains_pane_id_variable(self):
        result = generate_pane_border_refresh(NEXUS_HOME)
        assert "#{pane_id}" in result


class TestInstallHooks:
    """Tests for install_hooks."""

    def test_combines_all_commands(self):
        commands = install_hooks(NEXUS_HOME)
        # 3 hooks + 1 border format = 4
        assert len(commands) == 4

    def test_includes_hook_commands(self):
        commands = install_hooks(NEXUS_HOME)
        hook_cmds = [c for c in commands if "set-hook" in c]
        assert len(hook_cmds) == 3

    def test_includes_border_format(self):
        commands = install_hooks(NEXUS_HOME)
        border_cmds = [c for c in commands if "pane-border-format" in c]
        assert len(border_cmds) == 1
