"""
Order Management Event Manager
Manages Server-Sent Events (SSE) for real-time pending order/update notifications
"""
import asyncio
from typing import Dict, Any, Set
from datetime import datetime

from shared.logging import get_logger

logger = get_logger(__name__)


class OrderEventManager:
    """
    Singleton event manager for broadcasting order management updates via SSE.

    Maintains a registry of connected SSE clients (asyncio queues) and
    broadcasts events to all connected clients when pending orders/updates change.

    Event Types:
    - pending_order_created: New pending order created
    - pending_order_updated: Pending order status, fields, or conflicts changed
    - pending_order_deleted: Pending order deleted
    - pending_update_created: New pending update created (for existing HTC order)
    - pending_update_updated: Pending update fields or status changed
    - pending_update_resolved: Pending update approved or rejected

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
        logger.info("OrderEventManager initialized")

    def register_client(self, queue: asyncio.Queue) -> None:
        """
        Register a new SSE client connection.

        Args:
            queue: Asyncio queue for this client's event stream
        """
        self._clients.add(queue)
        logger.debug(f"Order SSE client registered - total clients: {len(self._clients)}")

    def unregister_client(self, queue: asyncio.Queue) -> None:
        """
        Unregister an SSE client connection.

        Args:
            queue: Asyncio queue to remove
        """
        self._clients.discard(queue)
        logger.debug(f"Order SSE client unregistered - total clients: {len(self._clients)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Broadcast an event to all connected SSE clients.

        Args:
            event_type: Type of event (pending_order_created, pending_update_resolved, etc.)
            data: Event payload (will be JSON serialized)
        """
        if not self._clients:
            logger.debug(f"No order SSE clients connected - skipping broadcast: {event_type}")
            return

        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.debug(f"Broadcasting {event_type} to {len(self._clients)} clients: {data}")

        # Send to all connected clients
        dead_clients = set()
        for client_queue in self._clients:
            try:
                # Non-blocking put - if queue is full, skip this client
                client_queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Order SSE client queue full - skipping event")
            except Exception as e:
                logger.error(f"Error sending order event to client: {e}")
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
                logger.error(f"Failed to broadcast order event synchronously: {e}")

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

        logger.info(f"Shutting down {len(self._clients)} order SSE client(s)")

        shutdown_event = {"type": "shutdown", "data": {}}

        for client_queue in list(self._clients):
            try:
                client_queue.put_nowait(shutdown_event)
            except asyncio.QueueFull:
                pass
            except Exception as e:
                logger.warning(f"Error sending shutdown to order client: {e}")


# Global singleton instance
order_event_manager = OrderEventManager()
