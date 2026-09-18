"""
backend/ws.py
-------------
Simple WebSocket broadcast hub for CoNDA.

Usage (inside a FastAPI WebSocket route):

    from backend.ws import hub

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        await hub.connect(websocket)
        try:
            while True:
                await websocket.receive_text()   # keep alive / drain
        except Exception:
            pass
        finally:
            hub.disconnect(websocket)

The orchestrator then calls:
    await hub.broadcast({"type": "tick", "payload": tick})
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConnectionHub:
    """Manages a set of connected WebSocket clients and broadcasts messages.

    Resilience guarantees:
    - A slow or broken client does not block other clients.
    - A send failure removes the offending client and is logged; it does
      not propagate an exception to the caller.
    """

    def __init__(self) -> None:
        self._clients: set = set()

    async def connect(self, websocket: Any) -> None:
        """Accept and register a new WebSocket client."""
        await websocket.accept()
        self._clients.add(websocket)
        logger.debug("WS client connected. total=%d", len(self._clients))

    def disconnect(self, websocket: Any) -> None:
        """Remove a client from the hub (idempotent)."""
        self._clients.discard(websocket)
        logger.debug("WS client disconnected. total=%d", len(self._clients))

    async def broadcast(self, message: dict) -> None:
        """Send *message* (JSON-serialisable dict) to all connected clients.

        Failed sends are caught, logged, and the offending client is removed.
        Other clients always receive the message regardless.
        """
        if not self._clients:
            return

        text = json.dumps(message)
        dead: list = []

        for ws in list(self._clients):
            try:
                await ws.send_text(text)
            except Exception as exc:
                logger.warning(
                    "WS send failed for client %s (%s). Removing.", ws, exc
                )
                dead.append(ws)

        for ws in dead:
            self._clients.discard(ws)

    @property
    def client_count(self) -> int:
        """Number of currently connected clients."""
        return len(self._clients)


# Module-level singleton used by both the orchestrator and the FastAPI routes.
hub = ConnectionHub()
