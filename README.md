# PARM: Shared Intelligence Layer

**PARM is a shared intelligence layer for building context-aware, privacy-first applications.**

Rather than reinventing infrastructure in each product, PARM provides the core platform that powers multiple real-world ventures: **CanDelivers** (bulky delivery logistics), **Clueat** (food/allergen intelligence), and **KeepClos** (relationship intelligence).

## Why PARM?

Modern AI applications need more than just agents. They need:

- **Agent Orchestration**: Route tasks to the right agents, compose them into chains, execute in parallel
- **Workflow Automation**: Build complex DAGs of steps with retry, timeout, and error handling
- **Context Handling**: Unified access to temporal, spatial, relational, and domain-specific context
- **Privacy Enforcement**: Encrypted vaults, access policies, and audit logs at the platform level
- **Event Coordination**: Products communicate through shared event bus, not direct calls
- **Integration**: HTTP adapters, webhooks, circuit breakers for external services

Instead of each product building these independently, they all plug into PARM.

## Architecture

```
┌─────────────────────────────────────────────────┐
│          Products (Proof of concept)            │
│  ┌──────────────┬──────────────┬──────────────┐ │
│  │  CanDelivers │    Clueat    │   KeepClos   │ │
│  │   (Bulky)    │ (Allergens)  │  (Contacts)  │ │
│  └──────────────┴──────────────┴──────────────┘ │
├─────────────────────────────────────────────────┤
│         PARM Shared Intelligence Layer          │
│  ┌─────────────────────────────────────────┐   │
│  │  Agents  │ Workflows │ Context │Privacy │   │
│  │Integrations │ Events │Registry │Config │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Design Principles

1. **Everything is Event-Driven**
   - Products communicate through the event bus, not direct calls
   - Enables loose coupling and independent scaling
   - Pub/sub with wildcard topic matching

2. **Context is First-Class**
   - Every decision has access to a unified ContextFrame
   - Temporal (when), Spatial (where), Relational (who), Domain (what)
   - Multiple providers, single resolver with conflict resolution

3. **Privacy by Default**
   - Encrypted vaults for sensitive data (AES-256-GCM)
   - Policy-based access control at platform level
   - Audit logs for all operations
   - Anonymization strategies built-in

4. **Agents are Composable**
   - Small, focused agents that do one thing well
   - Chain agents together with AgentChain
   - Fan out to parallel agents with AgentOrchestrator
   - Automatic retry with exponential backoff

5. **The Platform is the Product**
   - PARM itself is valuable—products are proof it works
   - Unified telemetry, logging, and observability
   - Single point for compliance and governance

## Quick Start

### Installation

```bash
pip install -e .
```

### Basic Usage

```python
from parm_core import ParmEngine
from parm_agents import BaseAgent, AgentCapability, CapabilityType
from parm_context import ContextResolver, TimeProvider

# Create engine
engine = ParmEngine()

# Define an agent
class AnalysisAgent(BaseAgent):
    def get_capabilities(self):
        return [AgentCapability(
            type=CapabilityType.ANALYSIS,
            name="analyze",
            description="Analyze data"
        )]

    def execute(self, context=None, **kwargs):
        # Your logic here
        return Result.success({"result": "analysis complete"})

# Register agent
agent = AnalysisAgent("my_agent")
engine.register_agent("my_agent", agent)

# Register context providers
time_provider = TimeProvider()
engine.register_context_provider("time", time_provider)

# Execute
result = engine.execute("my_agent", input_data)
```

## Core Modules

### parm-core
Central infrastructure: engine, config, events, registry, types

- `ParmEngine`: Central orchestrator
- `EventBus`: Pub/sub messaging
- `ServiceRegistry`: Service discovery
- `ParmConfig`: Configuration management

### parm-agents
Agent orchestration and composition

- `BaseAgent`: Abstract agent class
- `AgentOrchestrator`: Route tasks to agents, parallel execution
- `AgentChain`: Compose agents sequentially
- `AgentPool`: Manage multiple agent instances

### parm-workflows
Workflow automation and scheduling

- `Workflow`: DAG-based workflow definition
- `WorkflowBuilder`: Fluent workflow construction
- `WorkflowExecutor`: Execute workflows with retry/timeout
- `WorkflowScheduler`: Cron and event-triggered execution

### parm-context
Unified context handling

- `ContextFrame`: Immutable context snapshot
- `ContextProvider`: Abstract provider
- `TimeProvider`, `LocationProvider`, `RelationshipProvider`: Built-in providers
- `ContextResolver`: Merge frames from multiple providers

### parm-privacy
Privacy enforcement and data protection

- `PolicyEngine`: Evaluate access policies
- `DataVault`: Encrypted storage with audit logs
- `Anonymizer`: Data anonymization strategies
- `AnonymizationRule`: Reusable anonymization rules

### parm-integrations
External service integration

- `IntegrationAdapter`: Abstract adapter with circuit breaker
- `HTTPAdapter`: HTTP integration with retries and caching
- `WebhookManager`: Incoming webhook handling and routing

## How Products Plug In

Each product:

1. **Defines agents** that implement their core logic
2. **Registers context providers** for domain-specific state
3. **Creates workflows** that compose agents into processes
4. **Subscribes to events** to coordinate with other products
5. **Uses shared privacy/context/integration** infrastructure

Example:

```python
from parm_core import ParmEngine
from my_product import MyAgent, MyContextProvider

def setup_my_product(engine: ParmEngine):
    # Register agents
    agent = MyAgent()
    engine.register_agent("my_agent", agent)

    # Register context providers
    provider = MyContextProvider()
    engine.register_context_provider("my_provider", provider)

    # Listen to events
    engine.on_event("workflow.completed", handle_completion)
```

See `examples/` for complete working examples:
- `candelivers_connector.py`: Delivery routing workflow
- `clueat_connector.py`: Allergen detection workflow
- `keepclos_connector.py`: Relationship reminder workflow
- `full_ecosystem.py`: All three products running together

## Configuration

Configure via:

1. **TOML file**:
   ```toml
   [events]
   enabled = true
   max_history_size = 1000

   [agents]
   max_concurrent_agents = 10
   default_timeout_seconds = 60
   ```

2. **Environment variables** (with `PARM_` prefix):
   ```bash
   PARM_ENVIRONMENT=production
   PARM_AGENTS__MAX_CONCURRENT_AGENTS=20
   ```

3. **Python API**:
   ```python
   config = ParmConfig(environment="production", debug=False)
   engine = ParmEngine(config=config)
   ```

## Performance Considerations

- **Event Bus**: O(1) dispatch for registered topics, O(n) for wildcards
- **Registry**: O(1) lookups by name, O(n) for filtered queries
- **Context Resolution**: Parallel provider queries with configurable caching
- **Workflow Execution**: Parallel step execution where possible
- **Data Vault**: Encrypted operations scale with data size (not record count)

## Testing

```bash
pytest tests/ -v
pytest tests/test_engine.py::test_agent_registration
pytest tests/ -cov parm_core/
```

## Project Structure

```
parm/
├── pyproject.toml                 # Monorepo config
├── packages/
│   ├── parm_core/                # Core infrastructure
│   ├── parm_agents/              # Agent orchestration
│   ├── parm_workflows/           # Workflow automation
│   ├── parm_context/             # Context handling
│   ├── parm_privacy/             # Privacy enforcement
│   └── parm_integrations/        # External integrations
├── examples/
│   ├── candelivers_connector.py  # CanDelivers product
│   ├── clueat_connector.py       # Clueat product
│   ├── keepclos_connector.py     # KeepClos product
│   └── full_ecosystem.py         # All three together
├── tests/                         # Test suite
└── docs/                          # Documentation
```

## Key Features

### 🔄 Event-Driven
- Pub/sub message bus with wildcard topic matching
- Event history for debugging and auditing
- Async event dispatch with coroutines

### 🎯 Agent Orchestration
- Capability-based agent routing
- Sequential chaining with fluent API
- Parallel execution with fan-out
- Automatic retry with exponential backoff

### 📊 Workflow Automation
- DAG-based workflow definition
- Step retry, timeout, and conditional execution
- Cron-based and event-triggered scheduling
- Full execution tracking and pause/resume

### 🌍 Context Resolution
- Multiple context providers (Time, Location, Relationship)
- Frame merging with conflict resolution
- Immutable, composable context objects
- TTL-based frame expiration

### 🔐 Privacy by Default
- AES-256-GCM encrypted data vault
- Declarative privacy policies
- Role-based access control
- Audit logging of all access
- Data anonymization strategies

### 🔌 Integration Framework
- HTTP adapter with retries and caching
- Circuit breaker pattern for resilience
- Webhook management with signature verification
- Extensible adapter interface

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest`)
5. Submit a pull request

## License

MIT

## Contact

For questions or feedback, contact team@parm.ai
