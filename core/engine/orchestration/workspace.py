#!/usr/bin/env python3
# core/engine/orchestration/workspace.py
"""
Nexus Workspace Orchestrator (V3)
=================================
Automates complex Tmux layouts from JSON compositions.
Replaces legacy layout_engine.sh and processor.py.
"""

import json
import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional
import getpass

class WorkspaceOrchestrator:
    def __init__(self, nexus_home: Path, project_root: Path,
                 socket_label: Optional[str] = None,
                 multiplexer=None):
        self.nexus_home = nexus_home
        self.project_root = project_root
        self.socket_label = socket_label
        self.wrapper = str(nexus_home / "core/kernel/boot/pane_wrapper.sh")
        user = getpass.getuser()
        self.log_file = Path(f"/tmp/nexus_{user}/daemon.log")
        self.env = {}

        # --- Multiplexer Backend (Dependency Injection) ---
        # Default to TmuxAdapter; pass a different MultiplexerCapability
        # to drive Ghostty, WezTerm, iTerm2, or a NullAdapter for tests.
        if multiplexer is not None:
            self.mux = multiplexer
        else:
            try:
                sys.path.insert(0, str(nexus_home / "core"))
                from engine.capabilities.adapters.tmux import TmuxAdapter
                tmux_conf = str(nexus_home / "config/tmux/nexus.conf")
                self.mux = TmuxAdapter(
                    socket_label=socket_label or "",
                    conf=tmux_conf if Path(tmux_conf).exists() else ""
                )
                self.log("Axiom-D: TmuxAdapter initialized.")
            except Exception as e:
                self.log(f"Warning: Could not initialize TmuxAdapter: {e}. Falling back to run_tmux.")
                self.mux = None

        # Initialize State Engine for Momentum
        sys.path.append(str(nexus_home / "core/engine/state"))
        try:
            from state_engine import NexusStateEngine
            self.state = NexusStateEngine(self.project_root)
            self.log(f"Axiom-D: State loaded from {self.state.active_file}")
        except ImportError:
            self.log("Warning: Could not import NexusStateEngine. Momentum disabled.")
            self.state = None

        # Capability Registry
        try:
            sys.path.insert(0, str(nexus_home / "core"))
            from engine.capabilities.registry import CapabilityRegistry
            profile_path = Path(os.path.expanduser("~/.nexus/profile.yaml"))
            self._registry = CapabilityRegistry(profile_path)
            self.log("Axiom-D: Capability Registry initialized.")
        except Exception as e:
            self.log(f"Warning: Could not initialize CapabilityRegistry: {e}")
            self._registry = None

    def log(self, msg: str):
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [orchestrator] {msg}"
        print(line, flush=True)
        # Force stderr so it shows up in simulation/terminal
        print(line, file=sys.stderr, flush=True)
        with open(self.log_file, "a") as f:
            f.write(line + "\n")

    def run_tmux(self, args: list) -> str:
        if os.environ.get("NEXUS_SIMULATION") == "1":
            # Redirect to Daemon RPC for state synchronization in simulation
            try:
                from engine.lib.daemon_client import NexusDaemonClient
                client = NexusDaemonClient()
                res = client.send("tmux", {"args": args, "socket_label": self.socket_label})
                if res.get("status") == "ok":
                    return str(res.get("data", ""))
            except Exception as e:
                self.log(f"Sim-Orchestration Error: {e}")
                return ""

        try:
            cmd = ["tmux"]
            if self.socket_label:
                cmd += ["-L", self.socket_label]
            
            # Log every tmux execution for Negative Space Debugging
            full_cmd = " ".join(cmd + args)
            # self.log(f"TX: {full_cmd}") 
            
            process = subprocess.run(
                cmd + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return process.stdout.strip()
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.strip() or e.stdout.strip()
            self.log(f"AXIOM-E: Tmux Command Failed!\nCMD: {' '.join(cmd+args)}\nERROR: {err_msg}")
            return ""

    def apply_composition(self, layout_name: str, target_window: str):
        """Resolves and applies a named JSON composition."""
        try:
            self.log(f"Applying composition '{layout_name}' to window '{target_window}'")
            self._setup_environment(target_window)
            
            # --- Momentum Restoration ---
            if layout_name == "__saved_session__":
                if not self.state:
                    self.log("Error: State Engine not available for __saved_session__")
                    return
                
                # Get the window index from target_window (e.g. "nexus_proj:0")
                try:
                    win_idx = target_window.split(":")[1]
                except IndexError:
                    win_idx = "0"
                
                saved_layout = self.state.get(f"session.windows.{win_idx}")
                if not saved_layout:
                    self.log(f"No saved session found for window index {win_idx}. Falling back to vscodelike.")
                    layout_name = "vscodelike"
                else:
                    self.log(f"Restoring Momentum Snapshot for window {win_idx}")
                    self._build_momentum(saved_layout, target_window)
                    self._finalize(target_window)
                    return
            
            # 1. Resolve JSON Path
            paths = [
                self.nexus_home / f"core/ui/compositions/{layout_name}.json",
                self.project_root / f".nexus/compositions/{layout_name}.json"
            ]
            
            comp_json = None
            for p in paths:
                if p.exists():
                    comp_json = p
                    break
            
            if not comp_json:
                self.log(f"Error: Composition '{layout_name}' not found.")
                return

            with open(comp_json) as f:
                data = json.load(f)

            # 2. Get Starting Pane
            start_pane = self.run_tmux(["display-message", "-t", target_window, "-p", "#{pane_id}"])
            if not start_pane:
                self.log(f"Error: Could not resolve starting pane for window '{target_window}'")
                return

            self.log(f"Starting build from pane '{start_pane}'")
            # 3. Recursive Build
            self._build(data.get("layout", {}), start_pane)
            
            # 4. Final Focus & Slotting
            self._finalize(target_window)
            self.log("Composition applied successfully.")
        except Exception as e:
            self.log(f"CRITICAL ERROR in Orchestrator: {e}")
            import traceback
            self.log(traceback.format_exc())

    def _build_leaf(self, config: Dict[str, Any], target_pane: str):
        """Builds a single leaf pane (Terminal/Editor/Tool)."""
        # Leaf: Prepare Command
        cmd = config.get("command", "/bin/zsh -i")
        # Axiom: ID-First Identity (v11 Hardening)
        stack_id = config.get("id") or config.get("role")
        role_label = config.get("role")
        
        if stack_id:
            # Physical Identity
            self.run_tmux(["set-option", "-p", "-t", target_pane, "@nexus_stack_id", str(stack_id)])
            self.run_tmux(["select-pane", "-t", target_pane, "-T", str(stack_id)])
            
            # Legacy Metadata (Retained for secondary compatibility)
            if role_label:
                self.run_tmux(["set-option", "-p", "-t", target_pane, "@nexus_role", str(role_label)])
        
        # Send Command via Wrapper
        if cmd:
            # Axiom: Explicit Expansion of all capability variables
            for k, v in self.env.items():
                var_pattern = f"${k}"
                if var_pattern in cmd:
                    self.log(f"Expanding {var_pattern} to {v}")
                    cmd = cmd.replace(var_pattern, str(v))
            
            # Fallback for braces ${VAR}
            for k, v in self.env.items():
                var_pattern = f"${{{k}}}"
                if var_pattern in cmd:
                    cmd = cmd.replace(var_pattern, str(v))

            self.log(f"Sending wrapped command to pane {target_pane}: {cmd}")
            
            # Axiom Adapter-01: Ask the registry for the best launch command.
            # The adapter may wrap the command with delays, full paths, or flags.
            role = config.get("id") or config.get("role")
            if role and hasattr(self, '_registry') and self._registry:
                adapter_cmd = self._registry.get_launch_command(role)
                if adapter_cmd and adapter_cmd != role:
                    self.log(f"Adapter override: '{cmd}' -> '{adapter_cmd}'")
                    cmd = adapter_cmd

            wrapped = f"{self.wrapper} {cmd}"
            self.run_tmux(["send-keys", "-t", target_pane, wrapped, "ENTER"])
        
        # Lazy Adoption Trigger: Call stack init as 'local' to ensure unique identity
        stack_bin = self.nexus_home / "core/kernel/stack/stack"
        # We pass 'local' to ensure the Daemon generates a fresh UUID for this container.
        # The 'role' metadata is already set as a tmux option and will be adopted during the init.
        subprocess.run([str(stack_bin), "init", "local"], 
                       env={**os.environ, "TMUX_PANE": target_pane})

    def _build_momentum(self, snapshot: Dict[str, Any], target_window: str):
        """Restores a window from a high-fidelity 'Moment' snapshot."""
        try:
            panes = snapshot.get("panes", [])
            layout_str = snapshot.get("layout_string")
            if not panes:
                self.log("AXIOM-W: No panes found in momentum snapshot.")
                return

            self.log(f"AXIOM-G: Restoring {len(panes)} panes via Momentum.")

            # --- PHASE 1: ADAPTIVE SUBDIVISION ---
            # Axiom: Invariant-driven state convergence.
            expected_count = len(panes)
            curr_panes = self.run_tmux(["list-panes", "-t", target_window, "-F", "#{pane_id}"]).splitlines()
            count_delta = expected_count - len(curr_panes)
            
            self.log(f"AXIOM-G: Subdivision Phase. Current: {len(curr_panes)}, Goal: {expected_count}")
            
            if count_delta > 0:
                # Need more panes
                for i in range(count_delta):
                    # Axiom: Atomic creation + identification
                    # We get the new pane ID immediately to prevent "Orphan Drift"
                    res = self.run_tmux(["split-window", "-t", target_window, "-P", "-F", "#{pane_id}"])
                    
                    if not res:
                        self.log("WARNING: Split failed. Re-balancing...")
                        self.run_tmux(["select-layout", "-t", target_window, "even-horizontal"])
                        res = self.run_tmux(["split-window", "-t", target_window, "-P", "-F", "#{pane_id}"])
                        
                    if res:
                        self.log(f"Created atomic pane: {res.strip()}")
                    else:
                        raise RuntimeError(f"Window too small for {expected_count} panes.")
                    
            elif count_delta < 0:
                # Too many panes (e.g. from a partial previous boot)
                self.log(f"Cleaning up {-count_delta} excess panes...")
                for i in range(-count_delta):
                    self.run_tmux(["kill-pane", "-t", f"{target_window}.{expected_count+i}"])

            # Verify physical invariant
            actual_panes = self.run_tmux(["list-panes", "-t", target_window, "-F", "#{pane_id}"]).splitlines()
            if len(actual_panes) != expected_count:
                raise RuntimeError(f"Invariant Violation: Built {len(actual_panes)}, expected {expected_count}")

            # 2. Geometry Scaling Phase (Proportional Restoration)
            # Axiom G-02: Layout must be scaled to current terminal, not blindly restored.
            saved_dims = snapshot.get("dimensions", {})
            saved_w = saved_dims.get("w", 0)
            saved_h = saved_dims.get("h", 0)

            # Read current window dimensions
            cur_geo = self.run_tmux(["display-message", "-t", target_window, "-p",
                                     "#{window_width},#{window_height}"])
            try:
                cur_w, cur_h = (int(x) for x in cur_geo.split(","))
            except Exception:
                cur_w, cur_h = 80, 24

            self.log(f"AXIOM-G2: Saved={saved_w}x{saved_h}, Current={cur_w}x{cur_h}")

            # Only attempt layout string restore if terminal is large enough to
            # accommodate all panes with a minimum 10-column, 4-row floor.
            MIN_PANE_W, MIN_PANE_H = 10, 4
            min_required_w = MIN_PANE_W * expected_count
            min_required_h = MIN_PANE_H * 2  # rough estimate for vsplit rows

            if layout_str and saved_w > 0 and cur_w >= min_required_w and cur_h >= min_required_h:
                # Scale layout string dimensions proportionally
                sx = cur_w / saved_w
                sy = cur_h / saved_h
                scaled = self._scale_layout_string(layout_str, sx, sy, cur_w, cur_h)
                remapped = self._remap_layout_string(scaled, actual_panes)
                res = self.run_tmux(["select-layout", "-t", target_window, remapped])
                if res is None:
                    self.log("WARNING: Scaled layout rejected. Using even-horizontal fallback.")
                    self.run_tmux(["select-layout", "-t", target_window, "even-horizontal"])
                else:
                    self.log(f"AXIOM-G2: Proportional layout applied (scale {sx:.2f}x{sy:.2f}).")
            else:
                self.log(f"AXIOM-G2: Terminal too narrow for saved layout. Using even-horizontal.")
                self.run_tmux(["select-layout", "-t", target_window, "even-horizontal"])

            # 3. Role/Command Binding Phase
            self.log("AXIOM-G: Binding roles and executing commands.")
            # Refresh actual panes once more in case select-layout shifted them
            actual_panes = self.run_tmux(["list-panes", "-t", target_window, "-F", "#{pane_id}"]).splitlines()
            
            for i, pane_cfg in enumerate(panes):
                target_pane = actual_panes[i]
                stack_id = pane_cfg.get("id") or pane_cfg.get("role", "unknown")
                self.log(f"Binding Identity '{stack_id}' -> {target_pane}")
                self._build_leaf(pane_cfg, target_pane)

            self.log("AXIOM-D: Momentum Restoration Verified.")

        except Exception as e:
            self.log(f"ERROR: Momentum restoration failed: {e}")
            import traceback
            self.log(traceback.format_exc())

    def _scale_layout_string(self, layout_str: str, sx: float, sy: float,
                             cur_w: int, cur_h: int) -> str:
        """
        Scales all numeric dimension/position tokens in a tmux layout string
        proportionally. Tmux layout format:
          checksum,WxH,X,Y[{...}|[...]] for branches
          checksum,WxH,X,Y,ID          for leaves
        We strip the checksum; _remap_layout_string will recalculate it.
        """
        import re

        # Strip checksum prefix (everything before first comma)
        try:
            _, body = layout_str.split(",", 1)
        except ValueError:
            return layout_str

        # Scale every WxH,X,Y group. Pattern captures: width, height, x, y
        # and an optional pane ID (digit sequence) at the end of a leaf segment.
        def scale_token(m):
            w = max(1, int(round(int(m.group(1)) * sx)))
            h = max(1, int(round(int(m.group(2)) * sy)))
            x = max(0, int(round(int(m.group(3)) * sx)))
            y = max(0, int(round(int(m.group(4)) * sy)))
            # clamp root width/height to current dims
            w = min(w, cur_w)
            h = min(h, cur_h)
            suffix = f",{m.group(5)}" if m.group(5) else ""
            return f"{w}x{h},{x},{y}{suffix}"

        scaled_body = re.sub(
            r"(\d+)x(\d+),(\d+),(\d+)(?:,(\d+))?",
            scale_token,
            body
        )

        # Return without checksum; _remap_layout_string will add the correct one.
        return f"0000,{scaled_body}"

    def _remap_layout_string(self, layout_str: str, new_panes: list) -> str:
        """
        Remaps pane IDs in a tmux layout string to new pane IDs and recalculates checksum.
        Tmux layout strings use [WxH,X,Y,ID] for leaves and [WxH,X,Y] for branches.
        """
        import re
        new_ids = [p.replace("%", "") for p in new_panes]
        
        # 1. Strip the old checksum (before the first comma)
        try:
            _, body = layout_str.split(",", 1)
        except ValueError:
            return layout_str

        # 2. Remap Pane IDs
        # Regex to find the ID part of a leaf: [width]x[height],[x],[y],[id]
        pattern = r"(\d+x\d+,\d+,\d+),(\d+)"
        
        self.ids_found = 0
        def replace_fn(match):
            prefix = match.group(1)
            old_id = match.group(2)
            if self.ids_found < len(new_ids):
                replacement = f"{prefix},{new_ids[self.ids_found]}"
                self.ids_found += 1
                return replacement
            return f"{prefix},{old_id}"

        remapped_body = re.sub(pattern, replace_fn, body)
        
        # 3. Recalculate Checksum
        csum = 0
        for char in remapped_body:
            # 16-bit rotate right one bit
            csum = ((csum >> 1) & 0x7FFF) | ((csum & 1) << 15)
            # Add the character code
            csum = (csum + ord(char)) & 0xFFFF
        
        new_checksum = f"{csum:04x}"
        return f"{new_checksum},{remapped_body}"

    def _build(self, config: Dict[str, Any], target_pane: str):
        if "panes" not in config:
            self._build_leaf(config, target_pane)
            return
            
        ltype = config.get("type", "hsplit")
        direction = "-h" if ltype == "hsplit" else "-v"
        panes = config.get("panes", [])
        
        remaining_pane = target_pane
        for i in range(len(panes) - 1):
            pane_cfg = panes[i]
            size = pane_cfg.get("size")
            size_args = ["-p", str(size)] if isinstance(size, int) else (["-l", str(size)] if size else [])
            
            # Axiom: Elastic Splitting with Atomic Identification
            new_pane = self.run_tmux([
                "split-window", direction, "-b", "-d", 
                "-t", remaining_pane, "-P", "-F", "#{pane_id}",
                "-c", str(self.project_root)
            ] + size_args + ["/bin/zsh"])
            
            if not new_pane:
                self.log("WARNING: Recursive split failed. Re-balancing window...")
                self.run_tmux(["select-layout", "-t", remaining_pane, "even-horizontal"])
                new_pane = self.run_tmux([
                    "split-window", direction, "-b", "-d", 
                    "-t", remaining_pane, "-P", "-F", "#{pane_id}",
                    "-c", str(self.project_root)
                ] + size_args + ["/bin/zsh"])

            if new_pane:
                new_pane = new_pane.strip()
                self.log(f"Branching: {remaining_pane} -> {new_pane} (Stack: {pane_cfg.get('id', 'null')})")
                time.sleep(0.05)
                self._build(pane_cfg, new_pane)
            else:
                self.log(f"CRITICAL: Failed to carve space for branch {i}. Proceeding with compressed layout.")

        # Build last pane in the remaining space
        self._build(panes[-1], remaining_pane)

    def _setup_environment(self, target_window: str):
        """Sets up the global and session-level environment in Tmux."""
        user = getpass.getuser()
        session = target_window.split(":")[0]
        
        env = {
            "NEXUS_HOME": str(self.nexus_home),
            "PROJECT_ROOT": str(self.project_root),
            "YAZI_CONFIG_HOME": str(self.nexus_home / "config"/ "yazi"),
            "NVIM_PIPE": f"/tmp/nexus_{user}/pipes/nvim_{session}.pipe",
            "PX_STATE_DIR": f"/tmp/nexus_{user}/{session}/parallax",
            "VIRTUAL_ROOT": str(self.project_root),
            "NEXUS_STATION_ACTIVE": "1",
            "NEXUS_PROJECT": session.replace("nexus_", ""),
            "SOCKET_LABEL": self.socket_label if self.socket_label else "",
        }
        
        # Tools from CapabilityRegistry
        sys.path.append(str(self.nexus_home / "core"))
        from engine.capabilities.registry import CapabilityRegistry
        profile_path = Path(os.path.expanduser("~/.nexus/profile.yaml"))
        reg = CapabilityRegistry(profile_path) 
        
        env["NEXUS_EDITOR"] = reg.get_tool_for_role("editor")
        env["NEXUS_FILES"] = reg.get_tool_for_role("explorer")
        env["NEXUS_CHAT"] = reg.get_tool_for_role("chat")
        env["EDITOR_CMD"] = env["NEXUS_EDITOR"]
        if "nvim" in env["NEXUS_EDITOR"]:
            env["EDITOR_CMD"] += f" --listen {env['NVIM_PIPE']}"
        
        env["NEXUS_MENU_CMD"] = str(self.nexus_home / "modules/menu/bin/nexus-menu")
        self.env = env

        for k, v in env.items():
            self.run_tmux(["set-environment", "-g", k, v])
            self.run_tmux(["set-environment", "-t", session, k, v])

    def _finalize(self, target_window: str):
        """Focus first pane and display a health toast."""
        # Focus the first (editor/files) pane
        panes = self.run_tmux(["list-panes", "-t", target_window,
                               "-F", "#{pane_id}|#{@nexus_stack_id}"]).splitlines()
        if panes:
            first_pane = panes[0].split("|")[0]
            self.run_tmux(["select-pane", "-t", first_pane])

        # Tally identified vs orphan panes
        identified = [p for p in panes if len(p.split("|")) > 1 and p.split("|")[1]]
        total = len(panes)
        ok = len(identified)
        orphans = total - ok

        geo = self.run_tmux(["display-message", "-t", target_window, "-p",
                             "#{window_width}x#{window_height}"]) or "?x?"

        status_icon = "✓" if orphans == 0 else "⚠"
        orphan_part = f"  {orphans} Orphan(s)" if orphans > 0 else ""
        toast = f"{status_icon} {ok}/{total} panes bound  |  {target_window}  |  {geo}{orphan_part}"
        self.run_tmux(["display-message", "-t", target_window, toast])
        self.log(f"AXIOM-BOOT: {toast}")
