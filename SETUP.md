# PARM Setup Guide

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/your-org/parm.git
cd parm

# Install in development mode
pip install -e .

# Install with dev dependencies (for testing)
pip install -e ".[dev]"

# Install with documentation tools
pip install -e ".[docs]"
```

### Verify Installation

```bash
python -c "import parm_core; print(f'PARM {parm_core.__version__} installed')"
```

## Quick Start

### 1. Basic Engine Setup

```python
from parm_core import ParmEngine, ParmConfig

# Create engine with default config
engine = ParmEngine()

# Or with custom config
config = ParmConfig(environment="production", debug=False)
engine = ParmEngine(config=config)
```

### 2. Register and Execute a Handler

```python
from parm_core import Result

def my_handler(data):
    return Result.success({"processed": data})

engine.register_handler("my_handler", my_handler)
result = engine.execute("my_handler", {"input": "test"})
print(result.data)  # {"processed": {"input": "test"}}
```

### 3. Create a Simple Agent

```python
from parm_agents import BaseAgent, AgentCapability, CapabilityType
from parm_core import Result, ContextFrame

class MyAgent(BaseAgent):
    def get_capabilities(self):
        return [
            AgentCapability(
                type=CapabilityType.ANALYSIS,
                name="analyze",
                description="Analyze input data",
                tags=["analysis"]
            )
        ]

    def execute(self, context=None, **kwargs):
        data = kwargs.get("data")
        return Result.success({"analysis": f"Analyzed {data}"})

# Register and use
agent = MyAgent("my_agent")
engine.register_agent("my_agent", agent)

result = agent.execute(data="test_data")
```

### 4. Build a Workflow

```python
from parm_workflows import WorkflowBuilder, WorkflowExecutor
from datetime import timedelta

# Define workflow
workflow = (
    WorkflowBuilder("my_workflow")
    .add_step("step1", "action1", timeout=timedelta(seconds=30))
    .add_step("step2", "action2", depends_on=["step1"])
    .build()
)

# Execute workflow
executor = WorkflowExecutor()
executor.register_step_handler("action1", lambda inputs: Result.success({"step": 1}))
executor.register_step_handler("action2", lambda inputs: Result.success({"step": 2}))

execution = executor.run(workflow)
print(f"Workflow status: {execution.status}")
```

### 5. Add Context Providers

```python
from parm_context import TimeProvider, ContextResolver

# Create resolver
resolver = ContextResolver()

# Register provider
time_provider = TimeProvider()
resolver.register_provider(time_provider)

# Resolve context for an entity
context = resolver.resolve(entity_id="user123", entity_type="user")
print(f"Current time: {context.temporal_info['current_time']}")
```

### 6. Protect Sensitive Data

```python
from parm_privacy import DataVault, create_sensitive_policy

# Create vault
vault = DataVault(master_password="secure_password")

# Create policy
policy = create_sensitive_policy("user_emails")

# Store data
vault.store(
    key="user123_email",
    data={"email": "user@example.com"},
    policy=policy
)

# Retrieve data
result = vault.retrieve(
    key="user123_email",
    accessor="admin_service",
    accessor_level="admin"
)

if result.is_success():
    print(f"Email: {result.data['email']}")

# Check audit log
audit = vault.audit_log()
print(f"Access attempts: {len(audit)}")
```

### 7. Listen to Events

```python
# Subscribe to events
def on_completion(event):
    print(f"Event: {event.type.value} from {event.source}")

engine.on_event("agent.*", on_completion)

# Execute something that generates events
engine.execute("my_handler", {})
```

## Running Examples

The `examples/` directory contains complete working examples:

### CanDelivers (Bulky Delivery)

```bash
cd examples
python -c "
from candelivers_connector import setup_candelivers_on_parm
from parm_core import ParmEngine

engine = ParmEngine()
setup_candelivers_on_parm(engine)

# Execute delivery routing
result = engine.execute('candelivers_router', {
    'order_id': 'order_123',
    'items': ['sofa', 'table'],
    'delivery_location': {'lat': 37.7749, 'lng': -122.4194}
})
print(result.data)
"
```

### Clueat (Allergen Intelligence)

```bash
python -c "
from clueat_connector import setup_clueat_on_parm
from parm_core import ParmEngine

engine = ParmEngine()
setup_clueat_on_parm(engine)

# Analyze ingredients
result = engine.execute('clueat_analyzer', {
    'dish_name': 'Caesar Salad',
    'ingredients': ['croutons', 'parmesan', 'anchovies']
})
print(result.data)
"
```

### KeepClos (Relationship Intelligence)

```bash
python -c "
from keepclos_connector import setup_keepclos_on_parm
from parm_core import ParmEngine

engine = ParmEngine()
setup_keepclos_on_parm(engine)

# Score relationship
result = engine.execute('keepclos_analyzer', {
    'person_id': 'contact_123',
    'relationship_history': ['meeting_1', 'call_1', 'email_1']
})
print(result.data)
"
```

### Full Ecosystem

```bash
python full_ecosystem.py
```

This runs all three products simultaneously on a single PARM instance.

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_engine.py -v

# Run with coverage
pytest --cov=parm_core tests/

# Run specific test
pytest tests/test_engine.py::TestParmEngine::test_handler_execution -v
```

## Configuration

### Environment Variables

PARM reads configuration from environment variables with `PARM_` prefix:

```bash
# Set environment
export PARM_ENVIRONMENT=production
export PARM_DEBUG=false

# Set subsystem configs (use __ for nesting)
export PARM_AGENTS__MAX_CONCURRENT_AGENTS=20
export PARM_AGENTS__DEFAULT_TIMEOUT_SECONDS=60
export PARM_PRIVACY__ENABLE_ENCRYPTION=true
export PARM_WORKFLOWS__DEFAULT_STEP_TIMEOUT_SECONDS=30
```

### TOML Configuration File

Create `config.toml`:

```toml
environment = "development"
debug = true

[logging]
level = "DEBUG"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

[events]
enabled = true
max_history_size = 1000
async_dispatch = true

[agents]
max_concurrent_agents = 10
default_timeout_seconds = 60
retry_max_attempts = 3
retry_backoff_factor = 2.0

[workflows]
max_concurrent_workflows = 5
default_step_timeout_seconds = 30
enable_step_caching = false
enable_parallel_steps = true

[context]
default_ttl_seconds = 3600
enable_caching = true
max_cache_size = 1000

[privacy]
enable_encryption = true
encryption_algorithm = "AES-256-GCM"
enable_audit_logging = true
audit_log_retention_days = 365
enable_anonymization = true

[integrations]
http_timeout_seconds = 30
http_max_retries = 3
enable_circuit_breaker = true
```

Load it:

```python
from parm_core import load_config

config = load_config("config.toml")
engine = ParmEngine(config=config)
```

### Programmatic Configuration

```python
from parm_core import ParmConfig

config = ParmConfig(
    environment="production",
    debug=False,
    events={"enabled": True, "max_history_size": 5000},
    agents={"max_concurrent_agents": 20},
    privacy={"enable_encryption": True}
)

engine = ParmEngine(config=config)
```

## Integration with Products

To integrate a product with PARM:

1. **Define agents** that implement product logic
2. **Create context providers** for domain-specific state
3. **Build workflows** orchestrating agent chains
4. **Subscribe to events** for cross-product communication

Example structure:

```python
# my_product/connector.py
from parm_core import ParmEngine, Result
from parm_agents import BaseAgent, AgentCapability, CapabilityType
from parm_context import ContextProvider

class MyProductAgent(BaseAgent):
    def get_capabilities(self):
        return [AgentCapability(...)]

    def execute(self, context=None, **kwargs):
        # Product logic here
        return Result.success({"result": "..."})

class MyProductContextProvider(ContextProvider):
    def get_context(self, entity_id, entity_type):
        # Product context here
        return ContextFrame(...)

def setup_my_product_on_parm(engine: ParmEngine):
    agent = MyProductAgent()
    engine.register_agent("my_product", agent)

    provider = MyProductContextProvider()
    engine.register_context_provider("my_product", provider)

    # Listen to events from other products
    engine.on_event("workflow.completed", handle_workflow_complete)
```

## Development Workflow

1. **Set up environment**:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Run tests before committing**:
   ```bash
   pytest tests/ -v
   ```

3. **Format code**:
   ```bash
   black packages/ examples/ tests/
   ruff check packages/ examples/ tests/
   ```

4. **Type checking**:
   ```bash
   mypy packages/parm_core/src/
   ```

5. **Build documentation**:
   ```bash
   cd docs
   sphinx-build -b html . _build
   ```

## Troubleshooting

### Import Errors

If you get import errors, ensure the package is installed:
```bash
pip install -e .
```

### Event Bus Not Working

Make sure to use the global instance:
```python
from parm_core import get_event_bus
bus = get_event_bus()
```

### Workflow Validation Errors

Workflows validate on build. Common issues:
- Circular dependencies
- Missing step dependencies
- Invalid condition syntax

Debug with:
```python
is_valid, error = workflow.validate()
if not is_valid:
    print(f"Invalid: {error}")
```

### Privacy Policy Evaluation

Ensure policies are registered before evaluating:
```python
policy = create_sensitive_policy("my_policy")
engine.register_policy(policy)
result = engine.evaluate("my_policy", "read", "user")
```

## Next Steps

1. **Read the Architecture Guide**: `docs/architecture.md`
2. **Review Privacy Model**: `docs/privacy-model.md`
3. **Explore Examples**: `examples/full_ecosystem.py`
4. **Run Tests**: `pytest tests/ -v`
5. **Check API Docs**: Each module has docstrings and type hints

## Support

- Issues: GitHub Issues
- Documentation: README.md, docs/
- Examples: examples/
- Tests: tests/ (good examples of usage)
