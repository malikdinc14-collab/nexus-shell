import asyncio
import os
import json
import uuid
import datetime
import argparse
import logging
from typing import Dict, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("px-bus")

class ParallaxEventBus:
    def __init__(self, socket_path: str):
        self.socket_path = socket_path
        self.clients: Set[asyncio.StreamWriter] = set()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handles a new client connection."""
        addr = writer.get_extra_info('peername')
        logger.info(f"New connection from {addr}")
        self.clients.add(writer)

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                try:
                    message_str = data.decode().strip()
                    if not message_str:
                        continue
                    
                    message = json.loads(message_str)
                    logger.debug(f"Received: {message}")
                    
                    # Validate basic envelope (optional but good practice)
                    if not isinstance(message, dict) or "type" not in message:
                         logger.warning(f"Invalid message format: {message_str}")
                         continue

                    # Enrich if needed (e.g. server timestamp)
                    # For now, we trust the publisher to follow protocol or just forward raw
                    
                    # Broadcast to ALL other clients (except sender? No, usually all subscribers want it)
                    # Actually, publishers might be one-off scripts, subscribers are persistent.
                    # A robust bus usually broadcasts to everyone subscribed.
                    # Here we implement a simple broadcast to all connected clients.
                    await self.broadcast(message_str)
                    
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON: {data}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except asyncio.CancelledError:
            pass
        finally:
            logger.info(f"Closing connection {addr}")
            self.clients.discard(writer)
            writer.close()
            await writer.wait_closed()

    async def broadcast(self, message: str):
        """Sends a message to all connected clients."""
        if not message.endswith('\n'):
            message += '\n'
            
        encoded = message.encode()
        to_remove = set()
        
        for client in self.clients:
            try:
                client.write(encoded)
                await client.drain()
            except Exception as e:
                logger.warning(f"Failed to write to client: {e}")
                to_remove.add(client)
        
        for client in to_remove:
            self.clients.discard(client)

    async def start(self):
        """Starts the Unix Domain Socket server."""
        # Clean up old socket
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.socket_path), exist_ok=True)

        server = await asyncio.start_unix_server(
            self.handle_client, 
            path=self.socket_path
        )

        addr = server.sockets[0].getsockname()
        logger.info(f"Serving on {addr}")

        async with server:
            await server.serve_forever()

def main():
    parser = argparse.ArgumentParser(description="Parallax Event Bus Server")
    parser.add_argument("--socket", required=True, help="Path to the Unix socket")
    args = parser.parse_args()

    bus = ParallaxEventBus(args.socket)
    
    try:
        asyncio.run(bus.start())
    except KeyboardInterrupt:
        logger.info("Server stopping...")
    finally:
        if os.path.exists(args.socket):
            os.remove(args.socket)

if __name__ == "__main__":
    main()
