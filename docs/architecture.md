# PARM Architecture

## Overview

PARM is a layered platform where each layer provides specific functionality, building on lower layers. The architecture is designed for:

- **Separation of Concerns**: Each module has a clear responsibility
- **Composability**: Layers build on each other without tight coupling
- **Extensibility**: Products plug in at the top without modifying core layers
- **Scalability**: Asynchronous event dispatch, parallel agent execution

## Layer Stack

```
┌────────────────────────────────────────┐
│   Products (CanDelivers, Clueat, etc) │
├────────────────────────────────────────┤
│       Application Integration           │
│   (Connectors, Custom Agents/Workflows)│
├────────────────────────────────────────┤
│      Orchestration Layer (Agents)       │
│   (AgentOrchestrator, Chains, Pools)   │
├────────────────────────────────────────┤
│       Automation Layer (Workflows)      │
│    (WorkflowBuilder, Executor, Scheduler)
├────────────────────────────────────────┤
│      Context Layer (Resolution)         │
│   (ContextResolver, Providers, Frames) │
├────────────────────────────────────────┤
│      Privacy Layer (Security)           │
│  (Policies, Vault, Anonymization)      │
├────────────────────────────────────────┤
│    Integration Layer (External)         │
│   (HTTPAdapter, Webhooks, CircuitBreaker)
├────────────────────────────────────────┤
│   Core Infrastructure Layer             │
│ (Engine, EventBus, Registry, Config)   │
└────────────────────────────────────────┘
```

## Core Infrastructure (parm_core)

**Responsibility**: Provide the foundational platform primitives

### ParmEngine
The central orchestrator that:
- Registers and discovers agents, workflows, context providers
- Routes handler execution with event coordination
- Maintains execution context for correlation tracing
- Provides health checks for registered services

```python
engine = ParmEngine()
engine.register_agent("my_agent", agent)
engine.on_event("agent.completed", callback)
result = engine.execute("my_agent", input_data)
```

### EventBus
Topic-based pub/sub messaging that:
- Supports wildcard subscriptions ("agent.*" matches "agent.completed")
- Maintains event history for debugging
- Dispatches synchronously and asynchronously
- Provides event filtering and correlation

```python
bus = EventBus()
bus.subscribe("workflow.*", handler)
bus.emit(Event(type=EventType.WORKFLOW_STARTED, ...))
```

### ServiceRegistry
Service discovery that:
- Registers services by name, type, tags, capabilities
- Supports health checks and status tracking
- Enables capability-based service lookup
- Maintains service metadata and configuration

```python
registry = ServiceRegistry()
registry.register("agent_name", "agent", tags=["analysis"], capabilities=["analyze"])
services = registry.find_by_capability("analyze")
```

### Configuration
Environment-aware configuration that:
- Loads from TOML files, environment variables, or programmatically
- Validates configuration values
- Provides defaults for all subsystems
- Merges configurations with proper precedence

## Orchestration Layer (parm_agents)

**Responsibility**: Manage agent execution and composition

### BaseAgent
Abstract base class that defines:
- Agent capabilities with input/output schemas
- Execute method for core logic
- Lifecycle: init, ready, busy, error, shutdown
- Metrics collection

### AgentOrchestrator
Routes tasks to appropriate agents based on:
- Capability type matching
- Tag-based filtering
- Priority-based selection
- Automatic retry with exponential backoff

### AgentChain
Composes agents sequentially where:
- Output of one agent feeds input to next
- Transformers can modify input/output at boundaries
- Error propagation with partial result support
- Fluent builder API for construction

```python
chain = (ChainBuilder()
    .add(agent1)
    .add(agent2)
    .with_input_transformer(transform_input)
    .with_output_transformer(transform_output)
    .build())
```

### AgentPool
Manages multiple agent instances:
- Round-robin scheduling for load balancing
- Health checking
- Bulk initialization/shutdown
- Pool-wide metrics

## Automation Layer (parm_workflows)

**Responsibility**: Execute complex multi-step processes

### Workflow
DAG-based workflow definition where each step:
- Has unique ID, action, inputs, outputs
- Can have dependencies and conditions
- Can have timeout and retry settings
- Supports parameter substitution

Workflows are validated for:
- Circular dependencies
- Missing dependency references
- At least one root step

### WorkflowBuilder
Fluent API for constructing workflows:
- Add steps with dependencies
- Set conditions and timeouts
- Add metadata
- Build with validation

```python
workflow = (WorkflowBuilder("name")
    .add_step("step1", "action1", timeout=timedelta(seconds=30))
    .add_step("step2", "action2", depends_on=["step1"])
    .build())
```

### WorkflowExecutor
Executes workflows by:
- Topologically sorting steps
- Executing ready steps (all dependencies satisfied)
- Handling timeouts and retries
- Calling registered handlers for each step
- Emitting status change events

Supports pause/resume/cancel operations.

### WorkflowScheduler
Schedules workflows:
- Cron-based execution (simplified: "*/5 * * * *")
- Event-triggered execution
- Activate/deactivate schedules
- Track execution history

## Context Layer (parm_context)

**Responsibility**: Provide unified, consistent state for decisions

### ContextFrame
Immutable snapshot containing:
- Entity ID and type
- Timestamp and TTL for expiration
- Temporal info (when): time, timezone, business hours
- Spatial info (where): location, coordinates
- Relational info (who): relationships, connections
- Domain data (what): domain-specific state
- Source and expiration tracking

Frames are composable with merge:
```python
merged_frame = frame1.merge(frame2)  # Most recent wins
```

### ContextProvider
Abstract provider that sources context. Built-in providers:

**TimeProvider**
- Current time and timezone
- Business hours checking
- Day of week, time of day

**LocationProvider**
- Latitude, longitude
- Custom location metadata
- Distance calculations

**RelationshipProvider**
- Relationship graphs
- Connection metadata
- Relationship scoring

### ContextResolver
Gathers and merges context from multiple providers:
- Queries all registered providers in parallel
- Filters by provider name if needed
- Merges frames with conflict resolution
- Returns combined ContextFrame

```python
resolver = ContextResolver()
resolver.register_provider(time_provider)
resolver.register_provider(location_provider)
frame = resolver.resolve(entity_id, entity_type)
```

## Privacy Layer (parm_privacy)

**Responsibility**: Enforce data protection and compliance

### PrivacyPolicy
Declarative rules for data classification and handling:
- Data classification (PUBLIC, INTERNAL, SENSITIVE, RESTRICTED)
- Retention period
- Allowed operations
- Consent requirements
- Anonymization rules
- Minimum access level

### PolicyEngine
Evaluates policies against access requests:
- Check if operation is allowed
- Verify access level is sufficient
- Check consent requirements
- Get restrictions for classification

```python
policy = create_sensitive_policy("user_data")
engine.register_policy(policy)
result = engine.evaluate("user_data", "read", accessor="admin")
```

### DataVault
Encrypted storage with:
- AES-256-GCM encryption (AEAD cipher)
- Key derivation from master password
- IV generation for each encrypt operation
- Access policy enforcement
- Comprehensive audit logging

```python
vault = DataVault(master_password="secret")
vault.store(key="user_123", data=sensitive_data, policy=policy)
result = vault.retrieve(key="user_123", accessor="admin", accessor_level="admin")
```

### Anonymizer
Data transformation with strategies:
- **Hash**: SHA-256 hash (one-way)
- **Mask**: Show first and last char only
- **Generalize**: Ranges (e.g., ages 20-29)
- **Suppress**: Replace with ***

Supports nested fields and reversible pseudonymization:
```python
anonymizer = Anonymizer()
anonymized = anonymizer.anonymize(data, {"email": "hash", "phone": "mask"})
pseudonymized, mapping = anonymizer.pseudonymize(data, rules)
```

## Integration Layer (parm_integrations)

**Responsibility**: Connect to external services safely

### IntegrationAdapter
Abstract base with standard interface:
- Connect/disconnect lifecycle
- Health checks
- Execute with circuit breaker
- Automatic retry with backoff

### CircuitBreaker
Resilience pattern:
- CLOSED (normal operation)
- OPEN (failing, reject requests)
- HALF_OPEN (testing if recovered)
- Configurable failure threshold and timeout

### HTTPAdapter
HTTP integration with:
- Configurable headers and authentication
- GET, POST, PUT, DELETE methods
- Response caching
- Rate limiting ready (framework provided)

### WebhookManager
Incoming webhook handling:
- Register endpoints with event types
- HMAC-SHA256 signature verification
- Route webhooks to handlers
- Event logging

## Product Integration Pattern

Products integrate by:

1. **Defining Agents** implementing core business logic
2. **Registering Context Providers** for domain-specific state
3. **Creating Workflows** orchestrating agent chains
4. **Publishing Events** for system-wide coordination
5. **Listening to Events** from other products

Example (CanDelivers):
- Agent: DeliveryRoutingAgent (routes to vehicles)
- Provider: LocationProvider (coordinates, addresses)
- Workflow: validate → optimize → assign → track → complete
- Events: delivery.started, delivery.completed
- Context: uses time (business hours), location (addresses)

Example (Clueat):
- Agent: IngredientAnalysisAgent (detects allergens)
- Provider: FoodContextProvider (user allergies)
- Workflow: scan → parse → detect → score → notify
- Events: allergen.detected, customer.notified
- Context: uses temporal (meal time), relational (customer allergies)

Example (KeepClos):
- Agent: RelationshipAgent (scores relationship strength)
- Provider: RelationshipContextProvider (contact history)
- Workflow: load context → score → decide → send reminder
- Events: reminder.sent, contact.recorded
- Context: uses temporal (last contact time), relational (connections)

## Execution Flow

### Synchronous Execution
```
Request → ParmEngine.execute() → Handler lookup
  → Handler execution → Event emission → Response
```

### Agent Execution
```
Request → AgentOrchestrator.route() → Capability match
  → BaseAgent.execute() with ContextFrame
  → Result with status, data, metadata
```

### Workflow Execution
```
Request → WorkflowExecutor.run()
  → Topological sort of DAG
  → For each step: execute handlers, check conditions, retry on failure
  → Emit status changes
  → Return WorkflowExecution with step results
```

### Context Resolution
```
Request for context → ContextResolver
  → Query all providers in parallel
  → Collect ContextFrames
  → Merge with conflict resolution (most recent wins)
  → Return unified ContextFrame
```

## Performance Characteristics

| Component | Operation | Complexity |
|-----------|-----------|------------|
| EventBus | Subscribe | O(1) |
| EventBus | Emit (direct) | O(n) subscribers |
| EventBus | Emit (wildcard) | O(m*n) m=patterns, n=subscribers |
| Registry | Register | O(1) + O(k) for k indices |
| Registry | Lookup by name | O(1) |
| Registry | Lookup by tag/capability | O(n) for filtering |
| ContextResolver | Resolve | O(p) parallel, p=providers |
| DataVault | Store | O(d) for data size d |
| DataVault | Retrieve | O(d) for decryption |
| Workflow | Execute | O(s + e) s=steps, e=edges |
| AgentChain | Execute | O(a) sequential, a=agents |

## Extensibility Points

1. **Custom Agents**: Extend BaseAgent
2. **Custom Context Providers**: Extend ContextProvider
3. **Custom Adapters**: Extend IntegrationAdapter
4. **Custom Anonymization**: Extend Anonymizer strategies
5. **Custom Event Handlers**: Subscribe to EventBus topics
6. **Custom Workflows**: WorkflowBuilder API
7. **Custom Policies**: PolicyEngine registration

## Thread Safety

- EventBus uses asyncio.Lock for async dispatch
- Registry is thread-safe for read-only operations
- Mutable state (executions, history) uses locks where needed
- ContextFrame is immutable

## Future Enhancements

- Distributed event bus (message queue backend)
- Workflow visualization UI
- Advanced workflow scheduling (full croniter support)
- ML-based agent routing
- Performance optimization (caching, lazy loading)
- Streaming context updates
- Distributed tracing (OpenTelemetry)
