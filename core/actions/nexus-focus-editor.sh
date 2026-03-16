#!/bin/bash
# @parallax-action
# @name: Focus Editor
# @id: nexus:focus-editor
# @description: Switch focus to the editor pane
# @icon: code

tmux select-pane -t "${PX_NEXUS_EDITOR_PANE:-1}"
