"""Service registry for discovering agents, workflows, and context providers."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional


@dataclass
class ServiceHealth:
    """Health status of a service."""
    is_healthy: bool
    last_check: datetime
    message: str = ""
    response_time_ms: float = 0.0


@dataclass
class ServiceMetadata:
    """Metadata about a registered service."""
    name: str
    service_type: str  # agent, workflow, context_provider, integration
    description: str = ""
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.now)
    health: Optional[ServiceHealth] = None
    config: dict[str, Any] = field(default_factory=dict)


class ServiceRegistry:
    """
    Registry for service discovery.
    Supports registration, discovery, and health checking.
    """

    def __init__(self) -> None:
        """Initialize the service registry."""
        self._services: dict[str, ServiceMetadata] = {}
        self._type_index: dict[str, list[str]] = {}  # service_type -> [names]
        self._tag_index: dict[str, list[str]] = {}   # tag -> [names]
        self._capability_index: dict[str, list[str]] = {}  # capability -> [names]

    def register(
        self,
        name: str,
        service_type: str,
        description: str = "",
        version: str = "1.0.0",
        tags: Optional[list[str]] = None,
        capabilities: Optional[list[str]] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> ServiceMetadata:
        """
        Register a new service.

        Args:
            name: Unique service name
            service_type: Type of service (agent, workflow, context_provider, integration)
            description: Service description
            version: Service version
            tags: List of tags for discovery
            capabilities: List of capabilities this service provides
            config: Service configuration

        Returns:
            ServiceMetadata for the registered service
        """
        metadata = ServiceMetadata(
            name=name,
            service_type=service_type,
            description=description,
            version=version,
            tags=tags or [],
            capabilities=capabilities or [],
            config=config or {},
        )

        self._services[name] = metadata

        # Update indices
        if service_type not in self._type_index:
            self._type_index[service_type] = []
        self._type_index[service_type].append(name)

        for tag in (tags or []):
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(name)

        for capability in (capabilities or []):
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            self._capability_index[capability].append(name)

        return metadata

    def unregister(self, name: str) -> bool:
        """
        Unregister a service.

        Args:
            name: Name of the service to unregister

        Returns:
            True if service was unregistered, False if not found
        """
        if name not in self._services:
            return False

        metadata = self._services.pop(name)

        # Update indices
        if metadata.service_type in self._type_index:
            self._type_index[metadata.service_type].remove(name)

        for tag in metadata.tags:
            if tag in self._tag_index:
                self._tag_index[tag].remove(name)

        for capability in metadata.capabilities:
            if capability in self._capability_index:
                self._capability_index[capability].remove(name)

        return True

    def get(self, name: str) -> Optional[ServiceMetadata]:
        """
        Get a service by name.

        Args:
            name: Service name

        Returns:
            ServiceMetadata or None if not found
        """
        return self._services.get(name)

    def find_by_type(self, service_type: str) -> list[ServiceMetadata]:
        """
        Find all services of a specific type.

        Args:
            service_type: Type of service to find

        Returns:
            List of matching services
        """
        names = self._type_index.get(service_type, [])
        return [self._services[name] for name in names if name in self._services]

    def find_by_tag(self, tag: str) -> list[ServiceMetadata]:
        """
        Find all services with a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of matching services
        """
        names = self._tag_index.get(tag, [])
        return [self._services[name] for name in names if name in self._services]

    def find_by_capability(self, capability: str) -> list[ServiceMetadata]:
        """
        Find all services with a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of matching services
        """
        names = self._capability_index.get(capability, [])
        return [self._services[name] for name in names if name in self._services]

    def find_by_tags(self, tags: list[str]) -> list[ServiceMetadata]:
        """
        Find services that have ALL of the specified tags.

        Args:
            tags: List of tags that must all be present

        Returns:
            List of services with all tags
        """
        if not tags:
            return list(self._services.values())

        # Find services that have all tags
        candidates = set(self._services.keys())
        for tag in tags:
            tag_services = set(self._tag_index.get(tag, []))
            candidates = candidates.intersection(tag_services)

        return [self._services[name] for name in candidates if name in self._services]

    def update_health(
        self,
        name: str,
        is_healthy: bool,
        message: str = "",
        response_time_ms: float = 0.0,
    ) -> bool:
        """
        Update the health status of a service.

        Args:
            name: Service name
            is_healthy: Whether the service is healthy
            message: Health check message
            response_time_ms: Response time in milliseconds

        Returns:
            True if health was updated, False if service not found
        """
        if name not in self._services:
            return False

        self._services[name].health = ServiceHealth(
            is_healthy=is_healthy,
            last_check=datetime.now(),
            message=message,
            response_time_ms=response_time_ms,
        )
        return True

    def get_healthy_services(self, service_type: Optional[str] = None) -> list[ServiceMetadata]:
        """
        Get all healthy services, optionally filtered by type.

        Args:
            service_type: Optional service type filter

        Returns:
            List of healthy services
        """
        services = self.find_by_type(service_type) if service_type else list(self._services.values())
        return [s for s in services if s.health is None or s.health.is_healthy]

    def list_all(self) -> list[ServiceMetadata]:
        """Get all registered services."""
        return list(self._services.values())

    def clear(self) -> None:
        """Clear all registrations (useful for testing)."""
        self._services.clear()
        self._type_index.clear()
        self._tag_index.clear()
        self._capability_index.clear()


# Global registry instance
_global_registry: Optional[ServiceRegistry] = None


def get_registry() -> ServiceRegistry:
    """Get or create the global service registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ServiceRegistry()
    return _global_registry


def reset_registry() -> None:
    """Reset the global registry (useful for testing)."""
    global _global_registry
    _global_registry = None
