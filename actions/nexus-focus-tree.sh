#!/bin/bash
# @parallax-action
# @name: Focus Tree
# @id: nexus:focus-tree
# @description: Switch focus to the file tree pane
# @icon: folder-tree

tmux select-pane -t "${PX_NEXUS_TREE_PANE:-0}"
