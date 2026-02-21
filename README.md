# PARM - Shared AI Platform & Intelligence Layer

PARM (Platform for Autonomous Resource Management) is the shared AI infrastructure powering [CanDelivers](https://github.com/ErturkCan/candelivers), [Clueat](https://github.com/ErturkCan/clueat), and [KeepClos](https://github.com/ErturkCan/keepclos). It provides agent orchestration, workflow automation, context handling, and privacy-aware data processing as reusable building blocks.

## Architecture

```
PARM Platform
├── parm-core/          # Core runtime, configuration, plugin system
├── parm-agents/        # Agent orchestration (registry, lifecycle, communication)
├── parm-workflows/     # Workflow engine (DAG execution, scheduling, triggers)
├── parm-context/       # Context pipeline (ingestion, enrichment, retrieval)
├── parm-privacy/       # Privacy module (classification, encryption, consent)
└── parm-integrations/  # Product connectors (CanDelivers, Clueat, KeepClos)
```

## Packages

### parm-core
Core runtime providing configuration management, plugin system, event bus, and shared utilities. All other packages depend on parm-core.

### parm-agents
Agent orchestration framework with agent registry, lifecycle management, inter-agent messaging, and capability-based routing. Agents are the primary compute units in PARM.

### parm-workflows
DAG-based workflow engine supporting sequential, parallel, and conditional execution. Includes scheduling, retry policies, and trigger-based activation.

### parm-context
Context pipeline for ingesting, enriching, and retrieving contextual data. Supports multiple context sources, vector-based retrieval, and real-time context updates.

### parm-privacy
Privacy-aware data processing with automatic PII classification, field-level encryption (AES-256-GCM), consent management, and audit logging.

### parm-integrations
Product-specific connectors that bridge PARM's capabilities to each product:
- **CanDelivers**: Route optimization agents, delivery workflow automation
- **Clueat**: Ingredient analysis agents, allergen detection workflows
- **KeepClos**: Relationship timing agents, communication scheduling workflows

## How Products Use PARM

```python
from parm.agents import AgentRegistry, Agent
from parm.workflows import Workflow, Step
from parm.context import ContextPipeline
from parm.privacy import PrivacyClassifier

# Register a product-specific agent
registry = AgentRegistry()
registry.register(Agent(
    name="route_optimizer",
    capabilities=["routing", "optimization"],
    handler=optimize_routes
))

# Define a workflow
workflow = Workflow("delivery_planning")
workflow.add_step(Step("ingest_orders", ingest_fn))
workflow.add_step(Step("optimize_routes", optimize_fn))
workflow.add_step(Step("dispatch", dispatch_fn))

# Process with privacy awareness
classifier = PrivacyClassifier()
classified = classifier.classify(customer_data)
# Automatically encrypts PII fields before storage
```

## Design Principles

1. **Product-Agnostic Core**: PARM knows nothing about specific products. All product logic lives in parm-integrations connectors.
2. **Privacy by Default**: All data flows through the privacy module. PII is classified and encrypted automatically.
3. **Agent-First Architecture**: Business logic is encapsulated in agents that communicate via the event bus.
4. **Workflow-Driven Execution**: Complex multi-step operations are modeled as DAG workflows with retry and error handling.
5. **Context-Aware Decisions**: Agents access enriched context for better decision-making.

## Getting Started

```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run specific package tests
pytest tests/test_agents.py -v
pytest tests/test_workflows.py -v
pytest tests/test_privacy.py -v
```

## Tech Stack

- **Language**: Python 3.11+
- **Async**: asyncio for agent communication
- **Encryption**: cryptography (AES-256-GCM)
- **Testing**: pytest
- **Architecture**: Event-driven, plugin-based

## License

MIT License - See LICENSE file
