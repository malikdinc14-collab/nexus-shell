#!/usr/bin/env python3
"""
Nexus Event Bus Server
Real-time inter-pane communication via Unix socket
"""

import asyncio
import json
import os
import sys
import signal
from pathlib import Path
from typing import Dict, Set
from datetime import datetime

class EventBus:
    """
    Async event bus using Unix domain sockets.
    Supports pub/sub pattern with multiple subscribers per event type.
    """
    
    def __init__(self, socket_path: str):
        self.socket_path = socket_path
        self.subscribers: Dict[str, Set[asyncio.StreamWriter]] = {}
        self.event_history = []  # Circular buffer of last 1000 events
        self.max_history = 1000
        self.server = None
        self.running = False
        
    async def start(self):
        """Start the event bus server"""
        # Remove old socket if exists
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.socket_path), exist_ok=True)
        
        # Create Unix socket server
        self.server = await asyncio.start_unix_server(
            self.handle_client,
            path=self.socket_path
        )
        
        self.running = True
        print(f"[Event Bus] Started on {self.socket_path}", file=sys.stderr)
        
        async with self.server:
            await self.server.serve_forever()
            
    async def stop(self):
        """Stop the event bus server"""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
        # Close all subscriber connections
        for subscribers in self.subscribers.values():
            for writer in subscribers:
                writer.close()
                await writer.wait_closed()
                
        # Remove socket file
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
            
        print("[Event Bus] Stopped", file=sys.stderr)
        
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection"""
        addr = writer.get_extra_info('peername')
        print(f"[Event Bus] Client connected: {addr}", file=sys.stderr)
        
        try:
            while self.running:
                # Read line-delimited JSON
                data = await reader.readline()
                if not data:
                    break
                    
                try:
                    message = json.loads(data.decode().strip())
                    action = message.get("action")
                    
                    if action == "subscribe":
                        await self.handle_subscribe(message, writer)
                    elif action == "publish":
                        await self.handle_publish(message)
                    elif action == "list":
                        await self.handle_list(writer)
                    elif action == "history":
                        await self.handle_history(message, writer)
                    else:
                        await self.send_error(writer, f"Unknown action: {action}")
                        
                except json.JSONDecodeError as e:
                    await self.send_error(writer, f"Invalid JSON: {e}")
                except Exception as e:
                    await self.send_error(writer, f"Error: {e}")
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[Event Bus] Error handling client: {e}", file=sys.stderr)
        finally:
            # Remove from all subscriptions
            for subscribers in self.subscribers.values():
                subscribers.discard(writer)
                
            writer.close()
            await writer.wait_closed()
            print(f"[Event Bus] Client disconnected: {addr}", file=sys.stderr)
            
    async def handle_subscribe(self, message: dict, writer: asyncio.StreamWriter):
        """Subscribe client to event type"""
        event_type = message.get("type")
        if not event_type:
            await self.send_error(writer, "Missing event type")
            return
            
        if event_type not in self.subscribers:
            self.subscribers[event_type] = set()
            
        self.subscribers[event_type].add(writer)
        
        # Send confirmation
        response = {
            "status": "subscribed",
            "type": event_type,
            "subscriber_count": len(self.subscribers[event_type])
        }
        writer.write(json.dumps(response).encode() + b'\n')
        await writer.drain()
        
        print(f"[Event Bus] Subscribed to {event_type} (total: {len(self.subscribers[event_type])})", file=sys.stderr)
        
    async def handle_publish(self, message: dict):
        """Publish event to subscribers"""
        event_type = message.get("type")
        if not event_type:
            return
            
        # Add to history
        self.event_history.append(message)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
            
        # Get subscribers for this event type
        subscribers = self.subscribers.get(event_type, set())
        if not subscribers:
            print(f"[Event Bus] No subscribers for {event_type}", file=sys.stderr)
            return
            
        # Broadcast to all subscribers
        dead_writers = set()
        delivered = 0
        
        for writer in subscribers:
            try:
                writer.write(json.dumps(message).encode() + b'\n')
                await writer.drain()
                delivered += 1
            except Exception as e:
                print(f"[Event Bus] Failed to deliver to subscriber: {e}", file=sys.stderr)
                dead_writers.add(writer)
                
        # Remove dead connections
        if dead_writers:
            self.subscribers[event_type] -= dead_writers
            print(f"[Event Bus] Removed {len(dead_writers)} dead subscribers", file=sys.stderr)
            
        print(f"[Event Bus] Published {event_type} to {delivered} subscribers", file=sys.stderr)
        
    async def handle_list(self, writer: asyncio.StreamWriter):
        """List all subscriptions"""
        response = {
            "status": "ok",
            "subscriptions": {
                event_type: len(subscribers)
                for event_type, subscribers in self.subscribers.items()
            }
        }
        writer.write(json.dumps(response).encode() + b'\n')
        await writer.drain()
        
    async def handle_history(self, message: dict, writer: asyncio.StreamWriter):
        """Return event history"""
        event_type = message.get("type")
        limit = message.get("limit", 100)
        
        # Filter by event type if specified
        if event_type:
            events = [e for e in self.event_history if e.get("type") == event_type]
        else:
            events = self.event_history
            
        # Limit results
        events = events[-limit:]
        
        response = {
            "status": "ok",
            "events": events,
            "count": len(events)
        }
        writer.write(json.dumps(response).encode() + b'\n')
        await writer.drain()
        
    async def send_error(self, writer: asyncio.StreamWriter, error: str):
        """Send error response to client"""
        response = {
            "status": "error",
            "error": error
        }
        writer.write(json.dumps(response).encode() + b'\n')
        await writer.drain()


async def main():
    """Main entry point"""
    # Get socket path from environment or use default
    user = os.environ.get("USER", "unknown")
    project = os.environ.get("NEXUS_PROJECT", "default")
    socket_path = f"/tmp/nexus_{user}/{project}/bus.sock"
    
    # Create event bus
    bus = EventBus(socket_path)
    
    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    
    def shutdown():
        print("[Event Bus] Shutdown signal received", file=sys.stderr)
        asyncio.create_task(bus.stop())
        
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown)
    
    # Start server
    try:
        await bus.start()
    except KeyboardInterrupt:
        await bus.stop()
    except Exception as e:
        print(f"[Event Bus] Fatal error: {e}", file=sys.stderr)
        await bus.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
