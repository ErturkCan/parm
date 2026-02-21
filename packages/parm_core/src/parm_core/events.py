"""Event system for PARM with pub/sub messaging."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
from uuid import uuid4

from .types import Event, EventType


@dataclass
class EventHistory:
    """Stores event history for debugging and auditing."""
    events: list[Event] = field(default_factory=list)
    max_size: int = 1000

    def add(self, event: Event) -> None:
        """Add an event to history."""
        self.events.append(event)
        # Keep only recent events to prevent unbounded growth
        if len(self.events) > self.max_size:
            self.events = self.events[-self.max_size:]

    def filter_by_type(self, event_type: EventType) -> list[Event]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.type == event_type]

    def filter_by_source(self, source: str) -> list[Event]:
        """Get all events from a specific source."""
        return [e for e in self.events if e.source == source]

    def filter_by_correlation(self, correlation_id: str) -> list[Event]:
        """Get all events with a specific correlation ID."""
        return [e for e in self.events if e.correlation_id == correlation_id]


class EventBus:
    """
    Topic-based pub/sub event bus.
    Supports async event dispatch and event history.
    """

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._subscribers: dict[str, list[Callable[[Event], Any]]] = defaultdict(list)
        self._async_subscribers: dict[str, list[Callable[[Event], Any]]] = defaultdict(list)
        self.history = EventHistory()
        self._lock = asyncio.Lock()

    def subscribe(self, topic: str, callback: Callable[[Event], Any]) -> None:
        """
        Subscribe to a topic with a synchronous callback.

        Args:
            topic: Topic name (can use wildcards like 'agent.*')
            callback: Function to call when event is emitted
        """
        self._subscribers[topic].append(callback)

    def subscribe_async(self, topic: str, callback: Callable[[Event], Any]) -> None:
        """
        Subscribe to a topic with an async callback.

        Args:
            topic: Topic name (can use wildcards like 'agent.*')
            callback: Async function to call when event is emitted
        """
        self._async_subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable[[Event], Any]) -> None:
        """Unsubscribe from a topic."""
        if topic in self._subscribers:
            self._subscribers[topic] = [
                cb for cb in self._subscribers[topic] if cb is not callback
            ]
        if topic in self._async_subscribers:
            self._async_subscribers[topic] = [
                cb for cb in self._async_subscribers[topic] if cb is not callback
            ]

    def emit(self, event: Event) -> None:
        """
        Emit an event synchronously.

        Args:
            event: Event to emit
        """
        self.history.add(event)
        self._dispatch_to_subscribers(event)

    async def emit_async(self, event: Event) -> None:
        """
        Emit an event asynchronously.

        Args:
            event: Event to emit
        """
        async with self._lock:
            self.history.add(event)
        await self._dispatch_to_async_subscribers(event)

    def _dispatch_to_subscribers(self, event: Event) -> None:
        """Dispatch event to matching synchronous subscribers."""
        # Convert event type enum to string for matching
        event_str = event.type.value

        # Direct topic match
        for callback in self._subscribers.get(event_str, []):
            try:
                callback(event)
            except Exception as e:
                # Log but don't crash on subscriber errors
                print(f"Error in event subscriber for {event_str}: {e}")

        # Wildcard matching (e.g., 'agent.*' matches 'agent.started')
        for topic, callbacks in self._subscribers.items():
            if self._matches_wildcard(topic, event_str):
                for callback in callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        print(f"Error in event subscriber for {topic}: {e}")

    async def _dispatch_to_async_subscribers(self, event: Event) -> None:
        """Dispatch event to matching async subscribers."""
        event_str = event.type.value

        # Direct topic match
        tasks = []
        for callback in self._async_subscribers.get(event_str, []):
            tasks.append(self._safe_async_call(callback, event))

        # Wildcard matching
        for topic, callbacks in self._async_subscribers.items():
            if self._matches_wildcard(topic, event_str):
                for callback in callbacks:
                    tasks.append(self._safe_async_call(callback, event))

        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_async_call(self, callback: Callable[[Event], Any], event: Event) -> None:
        """Safely call an async callback."""
        try:
            result = callback(event)
            if hasattr(result, "__await__"):
                await result
        except Exception as e:
            print(f"Error in async event subscriber: {e}")

    @staticmethod
    def _matches_wildcard(pattern: str, text: str) -> bool:
        """Check if text matches a wildcard pattern."""
        if "*" not in pattern:
            return False
        # Simple wildcard matching: "agent.*" matches "agent.started"
        parts = pattern.split("*")
        if len(parts) != 2:
            return False
        prefix, suffix = parts
        return text.startswith(prefix) and text.endswith(suffix)

    def get_history(self) -> EventHistory:
        """Get event history."""
        return self.history

    def clear_history(self) -> None:
        """Clear event history."""
        self.history = EventHistory()


# Global event bus instance
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def reset_event_bus() -> None:
    """Reset the global event bus (useful for testing)."""
    global _global_event_bus
    _global_event_bus = None
