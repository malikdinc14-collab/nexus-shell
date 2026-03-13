#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import subprocess
from pathlib import Path

import yaml
import re

class SovereignDaemon:
    def __init__(self):
        self.user = os.environ.get("USER", "unknown")
        self.project = os.environ.get("NEXUS_PROJECT", "default")
        self.nexus_home = os.environ.get("NEXUS_HOME", os.path.expanduser("~/Projects/nexus-shell"))
        self.socket_path = f"/tmp/nexus_{self.user}/{self.project}/bus.sock"
        self.agent0_log = "/tmp/agent0_sandbox_stream.log"
        self.safety_config = self.load_safety_config()
        self.privacy_patterns = [re.compile(p) for p in self.safety_config.get("privacy_exclusions", [])]
        self.running = True

    def load_safety_config(self):
        """Load safety configuration from nexus-shell home"""
        config_path = Path(self.nexus_home) / "config" / "safety.yaml"
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}

    def is_private(self, path):
        """Check if a path matches any privacy exclusion patterns"""
        return any(pattern.search(path) for pattern in self.privacy_patterns)

    async def connect_bus(self):
        """Establish connection to the Event Bus"""
        while self.running:
            try:
                reader, writer = await asyncio.open_unix_connection(self.socket_path)
                return reader, writer
            except Exception as e:
                print(f"[SID] Waiting for Event Bus at {self.socket_path}...", file=sys.stderr)
                await asyncio.sleep(1)

    async def publish(self, writer, event_type, data):
        """Publish an event to the bus"""
        message = {
            "action": "publish",
            "type": event_type,
            "source": "SID",
            "timestamp": asyncio.get_event_loop().time(),
            "data": data
        }
        writer.write(json.dumps(message).encode() + b'\n')
        await writer.drain()

    async def tail_agent_logs(self, writer):
        """Bridge Agent Zero logs to the Event Bus"""
        if not os.path.exists(self.agent0_log):
            # Create it if it doesn't exist to avoid tail failure
            open(self.agent0_log, 'a').close()

        process = await asyncio.create_subprocess_exec(
            "tail", "-f", self.agent0_log,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        while self.running:
            line = await process.stdout.readline()
            if not line:
                break
            
            content = line.decode().strip()
            
            # Detect Ghost Driving Signals
            if "[SIGNAL:OPEN]" in content:
                path = content.split(">> ")[-1]
                if self.is_private(path):
                    print(f"[SID] Privacy Alert: Blocked broadcast of sensitive path: {path}", file=sys.stderr)
                    await self.publish(writer, "AI_EVENT", {"action": "privacy_block", "reason": "sensitive_path"})
                else:
                    await self.publish(writer, "AI_EVENT", {"action": "ghost_open", "path": path})
            
            # Detect Standard Output (Forward to stream)
            await self.publish(writer, "AI_STREAM", {"text": content})

    async def handle_mission(self, writer, query_data):
        """Dispatch the mission to the AI engine"""
        query = query_data.get("query")
        cwd = query_data.get("cwd", self.project)
        
        # Publish start event
        await self.publish(writer, "AI_EVENT", {"action": "mission_started", "query": query})
        await self.publish(writer, "AI_STREAM", {"text": f"[SID] Dispatching Mission: {query}"})

        # --- BRIDGE TO AGENT ZERO ---
        # For now, we simulate the dispatch. In Phase 2, this will call AgentZero's CLI
        # or send it via a socket to the headless engine.
        print(f"[SID] Mission Received: {query}", file=sys.stderr)

    async def listen_missions(self, reader, writer):
        """Listen for missions sent to the AI via AI_QUERY events"""
        try:
            while self.running:
                line = await reader.readline()
                if not line:
                    break
                
                try:
                    message = json.loads(line.decode().strip())
                    # Check if it's a published event of type AI_QUERY
                    if message.get("type") == "AI_QUERY":
                        query_data = message.get("data", {})
                        await self.handle_mission(writer, query_data)
                except json.JSONDecodeError:
                    continue
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[SID] Error in mission listener: {e}", file=sys.stderr)

    async def run(self):
        print(f"[SID] Sovereign Intelligence Daemon starting for {self.project}...", file=sys.stderr)
        reader, writer = await self.connect_bus()
        
        # Subscribe to AI_QUERY
        sub_msg = {"action": "subscribe", "type": "AI_QUERY"}
        writer.write(json.dumps(sub_msg).encode() + b'\n')
        await writer.drain()

        # Run bridge tasks
        # Note: listen_missions needs the writer to acknowledge missions on the bus
        await asyncio.gather(
            self.tail_agent_logs(writer),
            self.listen_missions(reader, writer)
        )

if __name__ == "__main__":
    daemon = SovereignDaemon()
    asyncio.run(daemon.run())
