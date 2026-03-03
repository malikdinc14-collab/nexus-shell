#!/usr/bin/env python3
import json
import sys
import subprocess
import os

def run_tmux(args):
    return subprocess.check_output(['tmux'] + args).decode().strip()

def build_layout(pane_id, config, project_root):
    ltype = config.get('type')
    panes = config.get('panes', [])
    
    if not ltype:
        # It's a terminal pane
        cmd = config.get('command', '/bin/zsh')
        # Expand environment variables in command
        cmd = os.path.expandvars(cmd)
        
        # Wrap command
        wrapper = os.environ.get('WRAPPER', 'core/boot/pane_wrapper.sh')
        full_cmd = f"{wrapper} {cmd}"
        
        # If it's the first pane, we just send keys. Otherwise it was already split.
        # But wait, the standard way is to split then run.
        # For the very first pane (the one we start with), we use send-keys.
        return

    # Handle splits
    current_pane = pane_id
    for i, pane_config in enumerate(panes):
        is_last = (i == len(panes) - 1)
        size = pane_config.get('size')
        
        split_args = []
        if ltype == 'hsplit':
            split_args.append('-h')
        else:
            split_args.append('-v')
            
        if size:
            if str(size).endswith('%') or int(size) < 100:
                split_args.extend(['-p', str(size)])
            else:
                split_args.extend(['-l', str(size)])
        
        # We split from the 'current_pane'.
        # Actually, a better way is:
        # 1. Start with one pane.
        # 2. For each pane in config except the last:
        #    a. Split the current pane.
        #    b. Recurse into the new split or the remaining part.
        
        # This is getting complex for a bash-based layout engine replacement.
        # Let's keep it simple for now: just flat splits.

if __name__ == "__main__":
    # placeholder for a more advanced python layout engine
    pass
