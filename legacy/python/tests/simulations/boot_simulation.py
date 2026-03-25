#!/usr/bin/env python3
# tests/simulations/boot_simulation.py
import os
import sys
import json
import time
import subprocess
from pathlib import Path

# Setup Paths
NEXUS_HOME = Path(__file__).resolve().parents[2]
sys.path.append(str(NEXUS_HOME / "core"))

USER = os.getlogin()
TEST_SOCKET = f"/tmp/nexus_sim_{int(time.time())}.sock"

def log(msg):
    print(f"[SIM] {msg}", flush=True)

class BootSimulation:
    def __init__(self):
        self.daemon_proc = None
        self.socket_path = TEST_SOCKET
        self.project_root = NEXUS_HOME
        
    def setup(self):
        log(f"Setting up simulation with socket: {self.socket_path}")
        
        env = os.environ.copy()
        env["NEXUS_HOME"] = str(NEXUS_HOME)
        env["PROJECT_ROOT"] = str(self.project_root)
        env["NEXUS_SIMULATION"] = "1"
        env["NEXUS_SOCKET"] = self.socket_path
        
        daemon_py = NEXUS_HOME / "core/services/internal/daemon.py"
        self.daemon_proc = subprocess.Popen(
            [sys.executable, str(daemon_py)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for socket
        for i in range(20):
            if Path(self.socket_path).exists():
                log(f"Daemon socket discovered after {i*0.1:.1f}s.")
                return
            if self.daemon_proc.poll() is not None:
                out, err = self.daemon_proc.communicate()
                log(f"FAILURE: Daemon died early. Exit Code: {self.daemon_proc.returncode}")
                log(f"Daemon Output: {out}")
                log(f"Daemon Error: {err}")
                sys.exit(1)
            time.sleep(0.1)
        log("FAILURE: Daemon failed to create socket.")
        sys.exit(1)

    def teardown(self):
        log("Tearing down simulation...")
        if self.daemon_proc:
            if self.daemon_proc.poll() is None:
                self.daemon_proc.terminate()
                self.daemon_proc.wait()
            else:
                out, err = self.daemon_proc.communicate()
                log(f"Daemon Final Output: {out}")
                log(f"Daemon Final Error: {err}")
        if Path(self.socket_path).exists():
            Path(self.socket_path).unlink()
        log("Teardown complete.")

    def run_client(self, action, payload=None):
        client_py = NEXUS_HOME / "core/engine/lib/daemon_client.py"
        env = os.environ.copy()
        env["NEXUS_HOME"] = str(NEXUS_HOME)
        env["PROJECT_ROOT"] = str(self.project_root)
        env["NEXUS_SIMULATION"] = "1"
        env["NEXUS_SOCKET"] = self.socket_path
        
        args = [sys.executable, str(client_py), action]
        if payload:
            args.append(json.dumps(payload))
            
        proc = subprocess.run(args, env=env, capture_output=True, text=True)
        if proc.stderr:
            log(f"Client Internal Error ({action}): {proc.stderr.strip()}")
        return json.loads(proc.stdout) if proc.stdout else {"status": "error", "message": "Empty response"}

    def run(self):
        try:
            self.setup()
            
            # 1. Initialize the real session on isolated socket
            log(f"Initializing real isolated tmux session on {self.socket_path}...")
            # We don't use -L here because the run_client/daemon already handles NEXUS_SOCKET
            res = self.run_client("tmux", {"args": ["new-session", "-d", "-s", "nexus_sim", "-n", "workspace_0"]})
            log(f"New Session Result: {res}")
            
            # 2. Invoke boot_layout against the real isolated server
            log("Invoking boot_layout (Authentic Mode)...")
            payload = {
                "name": "vscodelike",
                "window": "nexus_sim:0",
                "project_root": str(self.project_root)
            }
            res = self.run_client("boot_layout", payload)
            log(f"Boot Layout Result: {res}")
            
            # 3. Wait for orchestration to complete (Real splits take time)
            log("Waiting for physical orchestration...")
            time.sleep(3)
            
            # 4. Verify Final State (Observed from real system)
            log("Verifying results from Daemon Registry...")
            state = self.run_client("get_state")
            stacks = state.get("data", {}).get("stacks", {})
            
            found_roles = [s["role"] for s in stacks.values() if s.get("role")]
            log(f"Registered Roles: {found_roles}")
            
            # 5. Assert Invariants
            expected_roles = ["editor", "files", "menu", "terminal", "chat"]
            missing = [r for r in expected_roles if r not in found_roles]
            
            # 6. Physical Verification
            res = self.run_client("tmux", {"args": ["list-panes", "-t", "nexus_sim:0"]})
            actual_panes = res.get("data", "").strip().split("\n")
            log(f"Physical Panes Detected: {len(actual_panes)}")

            if missing:
                log(f"FAILURE: Missing registered stacks for: {missing}")
            elif len(actual_panes) < len(expected_roles):
                log(f"FAILURE: Physical pane count mismatch. Found {len(actual_panes)}, expected {len(expected_roles)}")
            else:
                log("SUCCESS: Authentic simulation complete. All systems nominal.")

        except Exception as e:
            log(f"Simulation Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.teardown()

if __name__ == "__main__":
    sim = BootSimulation()
    sim.run()
