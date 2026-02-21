"""Full ecosystem demo - All three products running on PARM."""

from parm_core import ParmEngine, ParmConfig
from parm_context import ContextResolver

from candelivers_connector import setup_candelivers_on_parm
from clueat_connector import setup_clueat_on_parm
from keepclos_connector import setup_keepclos_on_parm


def main() -> None:
    """Demonstrate all three products on a single PARM instance."""

    # Initialize PARM
    config = ParmConfig(
        environment="demo",
        debug=True,
        events={"enabled": True, "max_history_size": 1000},
    )

    engine = ParmEngine(config=config)

    print("=" * 70)
    print("PARM ECOSYSTEM DEMO")
    print("=" * 70)
    print()
    print("Initializing PARM with all product connectors...")
    print()

    # Setup each product
    setup_candelivers_on_parm(engine)
    print()

    setup_clueat_on_parm(engine)
    print()

    setup_keepclos_on_parm(engine)
    print()

    # Show what's registered
    print("=" * 70)
    print("PLATFORM OVERVIEW")
    print("=" * 70)
    print()

    # List all services
    all_services = engine.registry.list_all()
    print(f"Total Services Registered: {len(all_services)}")
    print()

    # Group by type
    agents = [s for s in all_services if s.service_type == "agent"]
    workflows = [s for s in all_services if s.service_type == "workflow"]
    providers = [s for s in all_services if s.service_type == "context_provider"]

    print(f"Agents ({len(agents)}):")
    for agent in agents:
        print(f"  - {agent.name}: {agent.description}")

    print()
    print(f"Workflows ({len(workflows)}):")
    for workflow in workflows:
        print(f"  - {workflow.name}: {workflow.description}")

    print()
    print(f"Context Providers ({len(providers)}):")
    for provider in providers:
        print(f"  - {provider.name}: {provider.description}")

    print()
    print("=" * 70)
    print("EVENT BUS")
    print("=" * 70)
    print()

    # Setup event monitoring
    def log_event(event):
        print(f"[EVENT] {event.type.value} from {event.source}")

    engine.event_bus.subscribe("agent.*", log_event)

    print("Event logging enabled for agent events")
    print()

    # Demonstrate cross-product coordination
    print("=" * 70)
    print("CROSS-PRODUCT WORKFLOW")
    print("=" * 70)
    print()

    print("Scenario: Customer orders bulky furniture with food allergy")
    print()

    # 1. CanDelivers processes the delivery
    print("1. CANDELIVERS - Processing delivery order")
    delivery_result = engine.execute(
        "candelivers_router",
        {
            "order_id": "order_12345",
            "items": ["sofa", "coffee_table"],
            "delivery_location": {"lat": 37.7749, "lng": -122.4194},
        },
    )
    print(f"   Result: {delivery_result.data}")
    print()

    # 2. Clueat checks if any food items have allergen concerns
    print("2. CLUEAT - Checking allergen profile for customer")
    allergen_result = engine.execute(
        "clueat_analyzer",
        {
            "dish_name": "catered_event_check",
            "ingredients": ["peanut_oil", "tree_nuts", "gluten"],
        },
    )
    print(f"   Result: Allergens found: {allergen_result.data['allergens']}")
    print()

    # 3. KeepClos suggests when to check in with customer
    print("3. KEEPCLOS - Scheduling follow-up contact")
    reminder_result = engine.execute(
        "keepclos_analyzer",
        {
            "person_id": "customer_12345",
            "relationship_history": ["order_1", "order_2", "order_3"],
        },
    )
    print(f"   Result: Relationship score {reminder_result.data['relationship_score']}, "
          f"action: {reminder_result.data['recommended_action']}")
    print()

    # Show event history
    print("=" * 70)
    print("EVENT HISTORY")
    print("=" * 70)
    print()

    history = engine.event_bus.get_history()
    print(f"Total events: {len(history.events)}")
    print("Recent events:")
    for event in history.events[-5:]:
        print(f"  - {event.type.value} @ {event.timestamp}")

    print()
    print("=" * 70)
    print("SHARED INTELLIGENCE LAYER")
    print("=" * 70)
    print()

    print("What makes PARM powerful:")
    print()
    print("1. Event-Driven Communication")
    print("   - All products publish events to shared event bus")
    print("   - No direct coupling between products")
    print("   - Easy to add new products without modifying existing ones")
    print()

    print("2. Unified Context")
    print("   - All products access shared context (time, location, relationships)")
    print("   - Consistent decision-making across all products")
    print("   - Context providers pluggable and composable")
    print()

    print("3. Privacy Enforcement")
    print("   - Single privacy policy engine for all products")
    print("   - Encrypted data vault for sensitive information")
    print("   - Audit log across entire platform")
    print()

    print("4. Workflow Orchestration")
    print("   - Products can compose complex workflows")
    print("   - Shared retry, timeout, and error handling")
    print("   - Full workflow visibility and control")
    print()

    print("5. Composable Agents")
    print("   - Small, focused agents that chain together")
    print("   - Reuse across products")
    print("   - Parallel execution support")
    print()

    print("=" * 70)
    print("ECOSYSTEM ARCHITECTURE")
    print("=" * 70)
    print()

    print("""
    ┌─────────────────────────────────────────────────┐
    │          Products (Proof of concept)            │
    │  ┌──────────────┬──────────────┬──────────────┐ │
    │  │  CanDelivers │    Clueat    │   KeepClos   │ │
    │  │   (Bulky)    │ (Allergens)  │  (Contacts)  │ │
    │  └──────────────┴──────────────┴──────────────┘ │
    ├─────────────────────────────────────────────────┤
    │         PARM Shared Intelligence Layer          │
    │  ┌─────────────────────────────────────────┐   │
    │  │       Agent Orchestration                │   │
    │  │   (Route, Chain, Parallelize)           │   │
    │  ├─────────────────────────────────────────┤   │
    │  │       Workflow Automation                │   │
    │  │   (DAG execution, retry, timeout)       │   │
    │  ├─────────────────────────────────────────┤   │
    │  │       Context Resolution                 │   │
    │  │   (Time, Location, Relationships)       │   │
    │  ├─────────────────────────────────────────┤   │
    │  │       Privacy & Compliance                │   │
    │  │   (Vault, Policies, Audit)              │   │
    │  ├─────────────────────────────────────────┤   │
    │  │       Integration Framework               │   │
    │  │   (HTTP, Webhooks, Circuit Breaker)     │   │
    │  ├─────────────────────────────────────────┤   │
    │  │       Event Bus & Registry                │   │
    │  │   (Pub/Sub, Service Discovery)          │   │
    │  └─────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────┘
    """)

    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
