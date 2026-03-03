#!/bin/bash
# @parallax-action
# @name: Focus Terminal
# @id: nexus:focus-terminal
# @description: Switch focus to the terminal pane
# @icon: terminal

tmux select-pane -t "${PX_NEXUS_TERMINAL_PANE:-2}"
