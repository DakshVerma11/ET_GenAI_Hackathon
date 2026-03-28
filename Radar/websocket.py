"""
WebSocket Broadcaster — manages all active WS connections and broadcasts signals.

Clients connect to: ws://host:8000/ws/feed
Each new signal is pushed immediately to all connected clients.
"""
import asyncio
import json
import logging
from typing import Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class SignalBroadcaster:
    """Thread-safe manager for active WebSocket connections."""

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        logger.info(f"WS client connected. Total: {len(self._connections)}")

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._connections.discard(ws)
        logger.info(f"WS client disconnected. Total: {len(self._connections)}")

    async def broadcast(self, data: dict):
        """Push a signal dict to all connected clients."""
        if not self._connections:
            return

        message = json.dumps({"type": "signal", "data": data})
        dead = set()

        async with self._lock:
            connections_snapshot = set(self._connections)

        for ws in connections_snapshot:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        if dead:
            async with self._lock:
                self._connections -= dead
            logger.info(f"Removed {len(dead)} dead WS connections")

    async def send_ping(self):
        """Keep-alive ping to all connections."""
        await self.broadcast({"type": "ping", "ts": asyncio.get_event_loop().time()})

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Singleton
broadcaster = SignalBroadcaster()