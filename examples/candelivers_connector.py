"""CanDelivers connector - Shows how products plug into PARM."""

from datetime import timedelta
from typing import Any, Optional

from parm_agents import BaseAgent, AgentCapability, CapabilityType
from parm_context import LocationProvider, ContextResolver
from parm_core import ContextFrame, Result, ParmEngine, CapabilityType as CapType
from parm_workflows import WorkflowBuilder, WorkflowExecutor


class DeliveryRoutingAgent(BaseAgent):
    """
    CanDelivers agent: Routes delivery orders to optimal vehicles/locations.
    """

    def __init__(self) -> None:
        super().__init__("delivery_router", "Routes bulky deliveries")

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                type=CapabilityType.ORCHESTRATION,
                name="route_optimization",
                description="Optimize delivery routes based on location and constraints",
                input_schema={
                    "order_id": "string",
                    "items": "list",
                    "delivery_location": {"lat": "float", "lng": "float"},
                },
                output_schema={
                    "route_id": "string",
                    "vehicle_id": "string",
                    "estimated_time": "int",
                },
                required_context=["location", "time"],
                tags=["delivery", "optimization"],
            )
        ]

    def execute(
        self,
        context: Optional[ContextFrame] = None,
        **kwargs: Any
    ) -> Result[Any]:
        """Execute delivery routing."""
        order_id = kwargs.get("order_id")
        delivery_location = kwargs.get("delivery_location")

        if not order_id or not delivery_location:
            return Result.failure("Missing required parameters")

        # Simulate routing logic
        route_id = f"route_{order_id}"
        vehicle_id = f"truck_001"
        estimated_minutes = 45

        return Result.success({
            "route_id": route_id,
            "vehicle_id": vehicle_id,
            "estimated_time_minutes": estimated_minutes,
            "delivery_location": delivery_location,
        })


class DeliveryTrackingAgent(BaseAgent):
    """CanDelivers agent: Tracks delivery status."""

    def __init__(self) -> None:
        super().__init__("delivery_tracker", "Tracks delivery status")

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                type=CapabilityType.PERSISTENCE,
                name="track_delivery",
                description="Track and update delivery status",
                tags=["delivery", "tracking"],
            )
        ]

    def execute(
        self,
        context: Optional[ContextFrame] = None,
        **kwargs: Any
    ) -> Result[Any]:
        """Execute delivery tracking."""
        route_id = kwargs.get("route_id")
        status = kwargs.get("status", "in_transit")

        return Result.success({
            "route_id": route_id,
            "status": status,
            "location": "updated",
        })


def setup_candelivers_on_parm(engine: ParmEngine) -> None:
    """
    Set up CanDelivers on the PARM platform.

    Args:
        engine: ParmEngine instance
    """
    # 1. Register agents
    routing_agent = DeliveryRoutingAgent()
    tracking_agent = DeliveryTrackingAgent()

    engine.register_agent(
        "candelivers_router",
        routing_agent,
        description="Routes bulky deliveries",
        tags=["delivery", "candelivers"],
        capabilities=["route_optimization"],
    )

    engine.register_agent(
        "candelivers_tracker",
        tracking_agent,
        description="Tracks delivery status",
        tags=["delivery", "candelivers"],
        capabilities=["track_delivery"],
    )

    # 2. Register location context provider
    location_provider = LocationProvider("candelivers_location_provider")
    engine.register_context_provider(
        "candelivers_location_provider",
        location_provider,
        description="Provides location context for deliveries",
        tags=["location", "delivery"],
    )

    # 3. Create and register delivery workflow
    delivery_workflow = (
        WorkflowBuilder("delivery_workflow", "Complete delivery process")
        .add_step(
            "validate_order",
            "validate_delivery_order",
            inputs={"order_id": "$order_id"},
            timeout=timedelta(seconds=10),
        )
        .add_step(
            "optimize_route",
            "route_delivery",
            depends_on=["validate_order"],
            inputs={"order_id": "$order_id"},
            timeout=timedelta(seconds=30),
        )
        .add_step(
            "assign_vehicle",
            "assign_vehicle",
            depends_on=["optimize_route"],
            timeout=timedelta(seconds=10),
        )
        .add_step(
            "track_delivery",
            "track_delivery",
            depends_on=["assign_vehicle"],
            timeout=timedelta(minutes=2),
        )
        .add_step(
            "complete_delivery",
            "complete_delivery",
            depends_on=["track_delivery"],
            timeout=timedelta(seconds=10),
        )
        .build()
    )

    engine.register_workflow(
        "candelivers_delivery_workflow",
        delivery_workflow,
        description="End-to-end delivery workflow",
        tags=["delivery", "candelivers"],
    )

    # 4. Register workflow handlers
    executor = WorkflowExecutor()

    executor.register_step_handler("validate_delivery_order", lambda inputs: validate_order(inputs))
    executor.register_step_handler("route_delivery", lambda inputs: route_delivery(inputs))
    executor.register_step_handler("assign_vehicle", lambda inputs: assign_vehicle(inputs))
    executor.register_step_handler("track_delivery", lambda inputs: track_delivery(inputs))
    executor.register_step_handler("complete_delivery", lambda inputs: complete_delivery(inputs))

    print("[CanDelivers] Connected to PARM")
    print("  - Agents: DeliveryRouter, DeliveryTracker")
    print("  - Workflow: Delivery (validate → optimize → assign → track → complete)")
    print("  - Context: LocationProvider")


# Handler functions for workflow steps
def validate_order(inputs: dict[str, Any]) -> Result[Any]:
    """Validate a delivery order."""
    order_id = inputs.get("order_id")
    return Result.success({"order_id": order_id, "valid": True})


def route_delivery(inputs: dict[str, Any]) -> Result[Any]:
    """Route a delivery."""
    order_id = inputs.get("order_id")
    return Result.success({"order_id": order_id, "route_id": f"route_{order_id}"})


def assign_vehicle(inputs: dict[str, Any]) -> Result[Any]:
    """Assign a vehicle."""
    return Result.success({"vehicle_id": "truck_001", "assigned": True})


def track_delivery(inputs: dict[str, Any]) -> Result[Any]:
    """Track delivery in progress."""
    return Result.success({"status": "in_transit", "eta_minutes": 45})


def complete_delivery(inputs: dict[str, Any]) -> Result[Any]:
    """Mark delivery as complete."""
    return Result.success({"status": "completed", "timestamp": "2024-01-01T12:00:00Z"})
