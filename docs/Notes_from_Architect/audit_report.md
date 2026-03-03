# Nexus-Shell Audit Report: Layout and Module Failures

Based on my review of the `vscodelike.json` layout composition, the `pane_wrapper.sh` execution handler, and the newly rewritten `nexus-menu`, here are my findings regarding the bugs you reported:

## 1. Yazi 3-Way Split Issue
**Symptom**: Yazi still launches with a 3-way split (Parent | Current | Preview) instead of functioning as a slim, single-column tree explorer.
**Cause**: My previous attempt to fix this by injecting `YAZI_RATIO=1:4:0` as an environment variable was invalid. Yazi does *not* accept layout ratios via environment variables. It strictly requires them to be set in a `yazi.toml` configuration file under `[manager] ratio = [...]`.
**Solution**: To solve this elegantly without messing up your global Yazi configuration (`~/.config/yazi/`), Nexus needs to generate a dedicated `yazi.toml` (e.g., inside `$PX_STATE_DIR/yazi/`) that forces a `1:0:0` or `0:1:0` ratio, and then launch Yazi via the wrapper passing `--local-config` or setting `YAZI_CONFIG_HOME=$PX_STATE_DIR/yazi/`. 

## 2. Editor and Render Panes Crashing
**Symptom**: Hitting the Editor or Render options drops the pane into a broken interactive state or just doesn't launch.
**Cause**: 
- For the Editor: The `EDITOR_CMD` resolution pipeline is brittle. `launcher.sh` constructs `EDITOR_CMD="nvim --listen /tmp/...pipe"`, but when `layout_engine.sh` uses `processor.py` to launch it, something in the `tmux send-keys` translation pipeline causes it to fail (sometimes executing an empty string if the environment drops, or tripping over the double quotes in standard evaluation). When it crashes, `pane_wrapper.sh` catches the exit and triggers its fallback `show_hub()` loop.
- For the Renderer: The "Render" module was historically launching `lib/swap.sh`. However, during our architectural simplification, `swap.sh` was deleted! Thus, the "render" target literally crashes because the file no longer exists.

## 3. Disjointed Module Selector Menu
**Symptom**: When a pane crashes (or immediately boots to the fallback selector), the menu shows the generic "Nexus Dashboard" (`system` context) instead of a tailored list of tools for that pane.
**Cause**: In `pane_wrapper.sh`, the old fallback menu hardcoded `fzf` with 6 specific options (Editor, Render, Shell, Files, Chat, Git). I blindly replaced it with `$MENU_BIN`, which defaults to the overarching `system` list.
**Solution**: `nexus-menu` needs a new, strict feature to consume static lists. We can either:
1. Add a specific `modules` context to `session.py` that outputs just those 6 pane assignments.
2. Modify `nexus-menu`'s wrapper shell script to accept standard input (stdin). That way, `pane_wrapper.sh` can just pipe `echo -e "EDITOR\nFILES"` directly into `nexus-menu`, giving us a beautiful, standardized menu without needing to create bloated Python plugins for every minor layout decision!

## Summary of Fix Protocol
Before proceeding to code, I recommend we:
1. Strip the `swap.sh` logic completely out of the IDE unless you want a dedicated Glow toggle.
2. Add a `yazi.toml` generator to `launcher.sh` specifically overriding the ratio.
3. Update `nexus-menu` to natively consume STDIN for ad-hoc menus like the `pane_wrapper.sh` module selector.
