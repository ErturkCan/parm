"""Context providers for sourcing context frames."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from parm_core import ContextFrame, Result


class ContextProvider(ABC):
    """Abstract base class for context providers."""

    def __init__(self, name: str) -> None:
        """
        Initialize a context provider.

        Args:
            name: Provider name
        """
        self.name = name

    @abstractmethod
    def get_context(self, entity_id: str, entity_type: str) -> Optional[ContextFrame]:
        """
        Get context for an entity.

        Args:
            entity_id: Entity ID
            entity_type: Entity type

        Returns:
            ContextFrame or None if no context available
        """
        pass


class TimeProvider(ContextProvider):
    """Provides temporal context (current time, timezone, business hours)."""

    def __init__(self, timezone_str: str = "UTC") -> None:
        """
        Initialize time provider.

        Args:
            timezone_str: Timezone string (e.g., "UTC", "America/New_York")
        """
        super().__init__("time_provider")
        self.timezone_str = timezone_str
        self.business_hours = {
            "start": 9,  # 9 AM
            "end": 17,   # 5 PM
            "days": [0, 1, 2, 3, 4],  # Monday-Friday
        }

    def get_context(self, entity_id: str, entity_type: str) -> Optional[ContextFrame]:
        """Get temporal context."""
        now = datetime.now(timezone.utc)

        temporal_info = {
            "current_time": now.isoformat(),
            "timestamp": now.timestamp(),
            "hour": now.hour,
            "day_of_week": now.weekday(),
            "date": now.date().isoformat(),
            "timezone": self.timezone_str,
            "is_business_hours": self._is_business_hours(now),
            "is_weekend": now.weekday() >= 5,
        }

        return ContextFrame(
            entity_id=entity_id,
            entity_type=entity_type,
            timestamp=now,
            temporal_info=temporal_info,
            spatial_info={},
            relational_info={},
            domain_data={},
            source="time_provider",
            ttl=timedelta(minutes=1),  # Refresh every minute
        )

    def _is_business_hours(self, dt: datetime) -> bool:
        """Check if current time is within business hours."""
        return (
            self.business_hours["start"] <= dt.hour < self.business_hours["end"]
            and dt.weekday() in self.business_hours["days"]
        )

    def set_business_hours(self, start: int, end: int, days: list[int]) -> None:
        """Set business hours."""
        self.business_hours = {"start": start, "end": end, "days": days}


class LocationProvider(ContextProvider):
    """Provides spatial context (location-based data)."""

    def __init__(self, name: str = "location_provider") -> None:
        """
        Initialize location provider.

        Args:
            name: Provider name
        """
        super().__init__(name)
        self._locations: dict[str, dict[str, Any]] = {}

    def set_location(self, entity_id: str, latitude: float, longitude: float, **kwargs: Any) -> None:
        """
        Set location for an entity.

        Args:
            entity_id: Entity ID
            latitude: Latitude
            longitude: Longitude
            **kwargs: Additional location data
        """
        self._locations[entity_id] = {
            "latitude": latitude,
            "longitude": longitude,
            **kwargs
        }

    def get_context(self, entity_id: str, entity_type: str) -> Optional[ContextFrame]:
        """Get spatial context."""
        if entity_id not in self._locations:
            return None

        location_data = self._locations[entity_id]

        return ContextFrame(
            entity_id=entity_id,
            entity_type=entity_type,
            timestamp=datetime.now(timezone.utc),
            temporal_info={},
            spatial_info=location_data,
            relational_info={},
            domain_data={},
            source="location_provider",
            ttl=timedelta(hours=1),
        )


class RelationshipProvider(ContextProvider):
    """Provides relational context (relationships, connections)."""

    def __init__(self, name: str = "relationship_provider") -> None:
        """
        Initialize relationship provider.

        Args:
            name: Provider name
        """
        super().__init__(name)
        self._relationships: dict[str, dict[str, Any]] = {}

    def add_relationship(
        self,
        entity_id: str,
        related_id: str,
        relationship_type: str,
        **metadata: Any
    ) -> None:
        """
        Add a relationship.

        Args:
            entity_id: Entity ID
            related_id: Related entity ID
            relationship_type: Type of relationship
            **metadata: Additional relationship metadata
        """
        if entity_id not in self._relationships:
            self._relationships[entity_id] = {}

        self._relationships[entity_id][related_id] = {
            "type": relationship_type,
            "metadata": metadata,
        }

    def get_context(self, entity_id: str, entity_type: str) -> Optional[ContextFrame]:
        """Get relational context."""
        relationships = self._relationships.get(entity_id, {})

        relational_info = {
            "relationships": relationships,
            "relationship_count": len(relationships),
            "connected_entities": list(relationships.keys()),
        }

        return ContextFrame(
            entity_id=entity_id,
            entity_type=entity_type,
            timestamp=datetime.now(timezone.utc),
            temporal_info={},
            spatial_info={},
            relational_info=relational_info,
            domain_data={},
            source="relationship_provider",
            ttl=timedelta(hours=1),
        )


class ContextProviderRegistry:
    """Registry for context providers."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._providers: dict[str, ContextProvider] = {}

    def register(self, provider: ContextProvider) -> None:
        """
        Register a context provider.

        Args:
            provider: Provider to register
        """
        self._providers[provider.name] = provider

    def unregister(self, name: str) -> bool:
        """
        Unregister a provider.

        Args:
            name: Provider name

        Returns:
            True if unregistered, False if not found
        """
        return self._providers.pop(name, None) is not None

    def get_provider(self, name: str) -> Optional[ContextProvider]:
        """Get a provider by name."""
        return self._providers.get(name)

    def get_all_providers(self) -> list[ContextProvider]:
        """Get all registered providers."""
        return list(self._providers.values())

    def clear(self) -> None:
        """Clear all providers."""
        self._providers.clear()
