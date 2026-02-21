"""PARM Core: Central infrastructure for the PARM platform."""

from .config import (
    ParmConfig,
    get_config,
    set_config,
    load_config,
    LoggingConfig,
    EventsConfig,
    AgentConfig,
    WorkflowConfig,
    ContextConfig,
    PrivacyConfig,
    IntegrationConfig,
)
from .engine import ParmEngine, ExecutionContext
from .events import Event, EventBus, EventHistory, get_event_bus, reset_event_bus
from .registry import ServiceRegistry, ServiceMetadata, ServiceHealth, get_registry, reset_registry
from .types import (
    Result,
    ResultStatus,
    Event as EventType,
    AgentCapability,
    CapabilityType,
    DataClassification,
    PrivacyPolicy,
    ContextFrame,
    WorkflowStep,
    WorkflowStatus,
    WorkflowExecution,
)

__all__ = [
    # Config
    "ParmConfig",
    "get_config",
    "set_config",
    "load_config",
    "LoggingConfig",
    "EventsConfig",
    "AgentConfig",
    "WorkflowConfig",
    "ContextConfig",
    "PrivacyConfig",
    "IntegrationConfig",
    # Engine
    "ParmEngine",
    "ExecutionContext",
    # Events
    "Event",
    "EventBus",
    "EventHistory",
    "get_event_bus",
    "reset_event_bus",
    # Registry
    "ServiceRegistry",
    "ServiceMetadata",
    "ServiceHealth",
    "get_registry",
    "reset_registry",
    # Types
    "Result",
    "ResultStatus",
    "AgentCapability",
    "CapabilityType",
    "DataClassification",
    "PrivacyPolicy",
    "ContextFrame",
    "WorkflowStep",
    "WorkflowStatus",
    "WorkflowExecution",
]

__version__ = "0.1.0"
