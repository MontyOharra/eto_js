"""
ETO Run Event Manager
Manages Server-Sent Events (SSE) for real-time ETO run updates
"""
import asyncio
import json

from typing import Dict, Any, Set
from datetime import datetime

from shared.logging import get_logger

logger = get_logger(__name__)


class EtoEventManager:
    """
    Singleton event manager for broadcasting ETO run updates via SSE.

    Maintains a registry of connected SSE clients (asyncio queues) and
    broadcasts events to all connected clients when ETO runs are created,
    updated, or deleted.

    Event Types:
    - run_created: New run created
    - run_updated: Run status or processing_step changed
    - run_deleted: Run deleted

    Note: This manager is stateless regarding shutdown. When the server shuts
    down, uvicorn cancels active tasks and the SSE generators handle
    CancelledError gracefully. Clients are responsible for reconnection.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._clients: Set[asyncio.Queue] = set()
        self._initialized = True
        logger.info("EtoEventManager initialized")

    def register_client(self, queue: asyncio.Queue) -> None:
        """
        Register a new SSE client connection.

        Args:
            queue: Asyncio queue for this client's event stream
        """
        self._clients.add(queue)
        logger.debug(f"SSE client registered - total clients: {len(self._clients)}")

    def unregister_client(self, queue: asyncio.Queue) -> None:
        """
        Unregister an SSE client connection.

        Args:
            queue: Asyncio queue to remove
        """
        self._clients.discard(queue)
        logger.debug(f"SSE client unregistered - total clients: {len(self._clients)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Broadcast an event to all connected SSE clients.

        Args:
            event_type: Type of event (run_created, run_updated, run_deleted)
            data: Event payload (will be JSON serialized)
        """
        if not self._clients:
            logger.monitor(f"No SSE clients connected - skipping broadcast: {event_type}")  # type: ignore
            return

        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.monitor(f"Broadcasting {event_type} to {len(self._clients)} clients: {data}")  # type: ignore

        # Send to all connected clients
        dead_clients = set()
        for client_queue in self._clients:
            try:
                # Non-blocking put - if queue is full, skip this client
                client_queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Client queue full - skipping event")
            except Exception as e:
                logger.error(f"Error sending event to client: {e}")
                dead_clients.add(client_queue)

        # Remove dead clients
        for dead_client in dead_clients:
            self.unregister_client(dead_client)

    def broadcast_sync(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Synchronous wrapper for broadcast (creates async task).
        Use this when calling from synchronous code.

        Args:
            event_type: Type of event
            data: Event payload
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create task to broadcast in background
                asyncio.create_task(self.broadcast(event_type, data))
            else:
                # Run directly if loop is not running
                loop.run_until_complete(self.broadcast(event_type, data))
        except RuntimeError:
            # No event loop - try to create one
            try:
                asyncio.run(self.broadcast(event_type, data))
            except Exception as e:
                logger.error(f"Failed to broadcast event synchronously: {e}")

    def get_client_count(self) -> int:
        """Get number of connected SSE clients"""
        return len(self._clients)

    async def shutdown(self) -> None:
        """
        Signal all SSE clients to disconnect gracefully.
        Sends a special shutdown event that tells generators to exit.
        """
        if not self._clients:
            return

        logger.info(f"Shutting down {len(self._clients)} SSE client(s)")

        shutdown_event = {"type": "shutdown", "data": {}}

        for client_queue in list(self._clients):
            try:
                client_queue.put_nowait(shutdown_event)
            except asyncio.QueueFull:
                pass
            except Exception as e:
                logger.warning(f"Error sending shutdown to client: {e}")


# Global singleton instance
eto_event_manager = EtoEventManager()
