"""Central PARM engine for orchestrating agents, workflows, and services."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional
from uuid import uuid4

from .config import ParmConfig, get_config
from .events import EventBus, get_event_bus
from .registry import ServiceRegistry, get_registry
from .types import Event, EventType, Result, ResultStatus


@dataclass
class ExecutionContext:
    """Context for a single execution."""
    execution_id: str
    correlation_id: str
    started_at: datetime
    metadata: dict[str, Any]


class ParmEngine:
    """
    Central orchestrator for the PARM platform.
    Manages agent registration, workflow execution, and event coordination.
    """

    def __init__(
        self,
        config: Optional[ParmConfig] = None,
        event_bus: Optional[EventBus] = None,
        registry: Optional[ServiceRegistry] = None,
    ) -> None:
        """
        Initialize PARM engine.

        Args:
            config: Configuration (uses global if not provided)
            event_bus: Event bus (creates new if not provided)
            registry: Service registry (creates new if not provided)
        """
        self.config = config or get_config()
        self.event_bus = event_bus or get_event_bus()
        self.registry = registry or get_registry()
        self._handlers: dict[str, Callable[[Any], Result[Any]]] = {}
        self._current_execution: Optional[ExecutionContext] = None

    def register_handler(self, name: str, handler: Callable[[Any], Result[Any]]) -> None:
        """
        Register a handler for a named action.

        Args:
            name: Handler name
            handler: Handler function
        """
        self._handlers[name] = handler

    def get_handler(self, name: str) -> Optional[Callable[[Any], Result[Any]]]:
        """Get a registered handler by name."""
        return self._handlers.get(name)

    def register_agent(
        self,
        name: str,
        agent: Any,
        description: str = "",
        tags: Optional[list[str]] = None,
        capabilities: Optional[list[str]] = None,
    ) -> None:
        """
        Register an agent with the platform.

        Args:
            name: Agent name
            agent: Agent instance
            description: Agent description
            tags: Search tags
            capabilities: Agent capabilities
        """
        self.registry.register(
            name=name,
            service_type="agent",
            description=description,
            tags=tags or [],
            capabilities=capabilities or [],
            config={"agent": agent},
        )

        # Emit registration event
        self.emit_event(
            Event(
                type=EventType.AGENT_STARTED,
                source=name,
                data={"action": "registered", "name": name},
            )
        )

    def register_workflow(
        self,
        name: str,
        workflow: Any,
        description: str = "",
        tags: Optional[list[str]] = None,
    ) -> None:
        """
        Register a workflow with the platform.

        Args:
            name: Workflow name
            workflow: Workflow instance
            description: Workflow description
            tags: Search tags
        """
        self.registry.register(
            name=name,
            service_type="workflow",
            description=description,
            tags=tags or [],
            config={"workflow": workflow},
        )

    def register_context_provider(
        self,
        name: str,
        provider: Any,
        description: str = "",
        tags: Optional[list[str]] = None,
    ) -> None:
        """
        Register a context provider.

        Args:
            name: Provider name
            provider: Provider instance
            description: Provider description
            tags: Search tags
        """
        self.registry.register(
            name=name,
            service_type="context_provider",
            description=description,
            tags=tags or [],
            config={"provider": provider},
        )

    def get_agent(self, name: str) -> Optional[Any]:
        """Get a registered agent by name."""
        metadata = self.registry.get(name)
        if metadata and metadata.service_type == "agent":
            return metadata.config.get("agent")
        return None

    def get_workflow(self, name: str) -> Optional[Any]:
        """Get a registered workflow by name."""
        metadata = self.registry.get(name)
        if metadata and metadata.service_type == "workflow":
            return metadata.config.get("workflow")
        return None

    def get_context_provider(self, name: str) -> Optional[Any]:
        """Get a registered context provider by name."""
        metadata = self.registry.get(name)
        if metadata and metadata.service_type == "context_provider":
            return metadata.config.get("provider")
        return None

    def find_agents_by_capability(self, capability: str) -> list[Any]:
        """Find agents that provide a specific capability."""
        services = self.registry.find_by_capability(capability)
        return [s.config.get("agent") for s in services if s.config.get("agent")]

    def find_agents_by_tag(self, tag: str) -> list[Any]:
        """Find agents with a specific tag."""
        services = self.registry.find_by_tag(tag)
        return [
            s.config.get("agent")
            for s in services
            if s.service_type == "agent" and s.config.get("agent")
        ]

    def emit_event(self, event: Event) -> None:
        """
        Emit an event to the event bus.

        Args:
            event: Event to emit
        """
        if not event.correlation_id and self._current_execution:
            event.correlation_id = self._current_execution.correlation_id
        self.event_bus.emit(event)

    async def emit_event_async(self, event: Event) -> None:
        """
        Emit an event asynchronously.

        Args:
            event: Event to emit
        """
        if not event.correlation_id and self._current_execution:
            event.correlation_id = self._current_execution.correlation_id
        await self.event_bus.emit_async(event)

    def on_event(self, topic: str, callback: Callable[[Event], Any]) -> None:
        """
        Subscribe to events.

        Args:
            topic: Event topic (can use wildcards like 'agent.*')
            callback: Callback function
        """
        self.event_bus.subscribe(topic, callback)

    def on_event_async(self, topic: str, callback: Callable[[Event], Any]) -> None:
        """
        Subscribe to events with async callback.

        Args:
            topic: Event topic
            callback: Async callback function
        """
        self.event_bus.subscribe_async(topic, callback)

    def execute(
        self,
        handler_name: str,
        input_data: Any,
        correlation_id: Optional[str] = None,
    ) -> Result[Any]:
        """
        Execute a named handler.

        Args:
            handler_name: Name of registered handler
            input_data: Input data for handler
            correlation_id: Optional correlation ID for tracing

        Returns:
            Result of execution
        """
        handler = self.get_handler(handler_name)
        if not handler:
            return Result.failure(f"Handler '{handler_name}' not found")

        # Set up execution context
        execution_id = str(uuid4())
        correlation_id = correlation_id or str(uuid4())
        old_execution = self._current_execution
        self._current_execution = ExecutionContext(
            execution_id=execution_id,
            correlation_id=correlation_id,
            started_at=datetime.now(),
            metadata={},
        )

        try:
            result = handler(input_data)

            # Emit completion event
            self.emit_event(
                Event(
                    type=EventType.AGENT_COMPLETED,
                    source=handler_name,
                    correlation_id=correlation_id,
                    data={"execution_id": execution_id, "success": result.is_success()},
                )
            )

            return result
        except Exception as e:
            # Emit error event
            self.emit_event(
                Event(
                    type=EventType.ERROR_OCCURRED,
                    source=handler_name,
                    correlation_id=correlation_id,
                    data={"execution_id": execution_id, "error": str(e)},
                )
            )
            return Result.failure(str(e))
        finally:
            self._current_execution = old_execution

    async def execute_async(
        self,
        handler_name: str,
        input_data: Any,
        correlation_id: Optional[str] = None,
    ) -> Result[Any]:
        """
        Execute a named handler asynchronously.

        Args:
            handler_name: Name of registered handler
            input_data: Input data for handler
            correlation_id: Optional correlation ID for tracing

        Returns:
            Result of execution
        """
        handler = self.get_handler(handler_name)
        if not handler:
            return Result.failure(f"Handler '{handler_name}' not found")

        execution_id = str(uuid4())
        correlation_id = correlation_id or str(uuid4())

        try:
            # Check if handler is async
            if asyncio.iscoroutinefunction(handler):
                result = await handler(input_data)
            else:
                result = handler(input_data)

            await self.emit_event_async(
                Event(
                    type=EventType.AGENT_COMPLETED,
                    source=handler_name,
                    correlation_id=correlation_id,
                    data={"execution_id": execution_id, "success": result.is_success()},
                )
            )

            return result
        except Exception as e:
            await self.emit_event_async(
                Event(
                    type=EventType.ERROR_OCCURRED,
                    source=handler_name,
                    correlation_id=correlation_id,
                    data={"execution_id": execution_id, "error": str(e)},
                )
            )
            return Result.failure(str(e))

    def get_execution_context(self) -> Optional[ExecutionContext]:
        """Get the current execution context."""
        return self._current_execution

    def health_check(self) -> Result[dict[str, Any]]:
        """
        Perform a health check on the engine and registered services.

        Returns:
            Result containing health status
        """
        health_status = {
            "engine": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {},
        }

        for service in self.registry.list_all():
            status = "healthy"
            if service.health and not service.health.is_healthy:
                status = "unhealthy"

            health_status["services"][service.name] = {
                "type": service.service_type,
                "status": status,
                "response_time_ms": service.health.response_time_ms if service.health else 0,
            }

        return Result.success(health_status)
