"""Tests for ParmEngine."""

import pytest
from parm_core import (
    ParmEngine,
    ParmConfig,
    Result,
    ResultStatus,
)


class TestParmEngine:
    """Test suite for ParmEngine."""

    def test_engine_initialization(self):
        """Test engine can be created."""
        engine = ParmEngine()
        assert engine is not None
        assert engine.config is not None
        assert engine.registry is not None
        assert engine.event_bus is not None

    def test_handler_registration(self):
        """Test handlers can be registered."""
        engine = ParmEngine()

        def dummy_handler(data):
            return Result.success({"processed": True})

        engine.register_handler("dummy", dummy_handler)
        assert engine.get_handler("dummy") is not None

    def test_handler_execution(self):
        """Test handlers can be executed."""
        engine = ParmEngine()

        def dummy_handler(data):
            return Result.success({"input": data, "result": "success"})

        engine.register_handler("dummy", dummy_handler)
        result = engine.execute("dummy", {"test": "data"})

        assert result.is_success()
        assert result.data["input"] == {"test": "data"}

    def test_handler_not_found(self):
        """Test executing non-existent handler."""
        engine = ParmEngine()
        result = engine.execute("nonexistent", {})

        assert result.is_failure()
        assert "not found" in result.error.lower()

    def test_handler_with_exception(self):
        """Test exception handling in handlers."""
        engine = ParmEngine()

        def failing_handler(data):
            raise ValueError("Test error")

        engine.register_handler("failing", failing_handler)
        result = engine.execute("failing", {})

        assert result.is_failure()
        assert "Test error" in result.error

    def test_event_subscription(self):
        """Test event subscriptions."""
        engine = ParmEngine()

        events = []

        def capture_event(event):
            events.append(event)

        engine.on_event("test.*", capture_event)

        def dummy_handler(data):
            return Result.success(data)

        engine.register_handler("dummy", dummy_handler)
        engine.execute("dummy", {})

        # Should have captured agent completion event
        assert len(events) > 0

    def test_health_check(self):
        """Test health check."""
        engine = ParmEngine()
        result = engine.health_check()

        assert result.is_success()
        assert "engine" in result.data
        assert "timestamp" in result.data
        assert "services" in result.data

    def test_execution_context(self):
        """Test execution context is maintained."""
        engine = ParmEngine()

        def context_aware_handler(data):
            context = engine.get_execution_context()
            assert context is not None
            assert context.execution_id is not None
            assert context.correlation_id is not None
            return Result.success({"context_id": context.execution_id})

        engine.register_handler("context_aware", context_aware_handler)
        result = engine.execute("context_aware", {})

        assert result.is_success()
        assert "context_id" in result.data

    def test_correlation_id_tracking(self):
        """Test correlation ID is maintained across calls."""
        engine = ParmEngine()
        correlation_id = "test_correlation_123"

        events = []

        def capture_event(event):
            events.append(event)

        engine.on_event("agent.*", capture_event)

        def dummy_handler(data):
            return Result.success(data)

        engine.register_handler("dummy", dummy_handler)
        engine.execute("dummy", {}, correlation_id=correlation_id)

        # Check that events have the correlation ID
        assert any(e.correlation_id == correlation_id for e in events)

    def test_config_propagation(self):
        """Test that config is available in engine."""
        config = ParmConfig(environment="test", debug=True)
        engine = ParmEngine(config=config)

        assert engine.config.environment == "test"
        assert engine.config.debug is True

    def test_registry_integration(self):
        """Test that registry is accessible from engine."""
        engine = ParmEngine()

        # Register a service directly via registry
        engine.registry.register(
            name="test_service",
            service_type="agent",
            description="Test service",
            tags=["test"],
        )

        # Find it back
        metadata = engine.registry.get("test_service")
        assert metadata is not None
        assert metadata.name == "test_service"
        assert "test" in metadata.tags

    def test_event_bus_integration(self):
        """Test that event bus is accessible from engine."""
        engine = ParmEngine()
        history = engine.event_bus.get_history()

        assert history is not None
        assert len(history.events) >= 0

    def test_multiple_handlers(self):
        """Test multiple handlers can be registered and executed."""
        engine = ParmEngine()

        def handler_1(data):
            return Result.success({"handler": "1", "data": data})

        def handler_2(data):
            return Result.success({"handler": "2", "data": data})

        engine.register_handler("handler1", handler_1)
        engine.register_handler("handler2", handler_2)

        result1 = engine.execute("handler1", {"test": "data1"})
        result2 = engine.execute("handler2", {"test": "data2"})

        assert result1.is_success()
        assert result2.is_success()
        assert result1.data["handler"] == "1"
        assert result2.data["handler"] == "2"

    def test_handler_override(self):
        """Test that handlers can be overridden."""
        engine = ParmEngine()

        def handler_v1(data):
            return Result.success({"version": "1"})

        def handler_v2(data):
            return Result.success({"version": "2"})

        engine.register_handler("handler", handler_v1)
        result1 = engine.execute("handler", {})
        assert result1.data["version"] == "1"

        engine.register_handler("handler", handler_v2)
        result2 = engine.execute("handler", {})
        assert result2.data["version"] == "2"


class TestParmEngineAsync:
    """Test async operations."""

    @pytest.mark.asyncio
    async def test_async_handler_execution(self):
        """Test async handlers can be executed."""
        engine = ParmEngine()

        async def async_handler(data):
            return Result.success({"async": True, "data": data})

        engine.register_handler("async_handler", async_handler)
        result = await engine.execute_async("async_handler", {"test": "data"})

        assert result.is_success()
        assert result.data["async"] is True

    @pytest.mark.asyncio
    async def test_async_event_emission(self):
        """Test async event emission."""
        engine = ParmEngine()

        events = []

        async def capture_event(event):
            events.append(event)

        engine.on_event_async("test.*", capture_event)

        from parm_core import Event, EventType

        await engine.emit_event_async(Event(
            type=EventType.AGENT_COMPLETED,
            source="test_source",
            data={"test": "data"}
        ))

        # Give async tasks time to complete
        import asyncio
        await asyncio.sleep(0.1)

        assert len(events) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
