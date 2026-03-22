#!/usr/bin/env python3
# core/engine/lib/daemon_client.py
"""
Nexus Daemon Client Bridge
==========================
Simple IPC client to communicate with nxs-d via Unix Socket.
"""

import os
import sys
import json
import socket
from pathlib import Path

import getpass
import subprocess
import time
# IPC Configuration
USER = getpass.getuser()
DEFAULT_SOCKET = Path(f"/tmp/nexus_{USER}.sock")
SOCKET_PATH = Path(os.environ.get("NEXUS_SOCKET", DEFAULT_SOCKET))
NEXUS_HOME = Path(os.environ.get("NEXUS_HOME", Path(__file__).resolve().parents[3]))

class NexusDaemonClient:
    def __init__(self, socket_path=SOCKET_PATH):
        self.socket_path = socket_path

    def send(self, action, payload=None, retry=True):
        """Sends a request to the daemon and returns the response."""
        if not self.socket_path.exists():
            if retry:
                self.ensure_alive()
                return self.send(action, payload, retry=False)
            return {"status": "error", "message": "Daemon not running."}
        
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(2.0)
                client.connect(str(self.socket_path))
                
                payload = payload or {}
                if "socket_label" not in payload:
                    sl = os.environ.get("SOCKET_LABEL")
                    if sl:
                        payload["socket_label"] = sl
                
                message = json.dumps({"action": action, "payload": payload})
                client.sendall(message.encode())
                
                data = client.recv(16384)
                if not data:
                    return {"status": "error", "message": "No response."}
                return json.loads(data.decode())
        except (socket.timeout, ConnectionRefusedError):
            if retry:
                if self.socket_path.exists(): self.socket_path.unlink()
                self.ensure_alive()
                return self.send(action, payload, retry=False)
            return {"status": "error", "message": "Connection failed."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def ensure_alive(self):
        """Ensures the daemon (and core services) are running."""
        if self.socket_path.exists():
            # Quick check
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    s.connect(str(self.socket_path))
                    return True
            except:
                self.socket_path.unlink()

        daemon_py = NEXUS_HOME / "core/services/internal/daemon.py"
        log_file = f"/tmp/nexus_{USER}/daemon.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Start Daemon
        subprocess.Popen(
            [sys.executable, str(daemon_py)],
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setpgrp # Disown
        )
        
        # Wait for socket
        for _ in range(20):
            if self.socket_path.exists():
                # Now that daemon is up, it will eventually start Bus/SID via its own init if needed
                # (Or we can trigger them here if we prefer)
                return True
            time.sleep(0.1)
        return False

    def ping(self):
        return self.send("ping")

    def get_state(self):
        return self.send("get_state")

    def set_state(self, state):
        return self.send("set_state", payload=state)

    def tmux(self, *args):
        return self.send("tmux", payload={"args": list(args)})

if __name__ == "__main__":
    import sys
    client = NexusDaemonClient()
    
    if len(sys.argv) > 1 and sys.argv[1] == "ensure":
        if client.ensure_alive():
            sys.exit(0)
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: daemon_client.py <action> [payload_json]")
        sys.exit(1)
    
    action = sys.argv[1]
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    
    res = client.send(action, payload)
    print(json.dumps(res, indent=2))
