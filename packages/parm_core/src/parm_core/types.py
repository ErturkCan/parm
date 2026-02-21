"""Shared types and data structures for the PARM platform."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, Optional, TypeVar, Union
from datetime import datetime, timedelta

T = TypeVar("T")


class ResultStatus(str, Enum):
    """Status of an operation result."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class Result(Generic[T]):
    """Generic result container for operations."""
    status: ResultStatus
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, data: T, metadata: Optional[dict[str, Any]] = None) -> "Result[T]":
        """Create a successful result."""
        return cls(
            status=ResultStatus.SUCCESS,
            data=data,
            metadata=metadata or {}
        )

    @classmethod
    def failure(cls, error: str, metadata: Optional[dict[str, Any]] = None) -> "Result[T]":
        """Create a failed result."""
        return cls(
            status=ResultStatus.FAILURE,
            error=error,
            metadata=metadata or {}
        )

    @classmethod
    def partial(cls, data: T, error: str, metadata: Optional[dict[str, Any]] = None) -> "Result[T]":
        """Create a partial result (partial success with error)."""
        return cls(
            status=ResultStatus.PARTIAL,
            data=data,
            error=error,
            metadata=metadata or {}
        )

    def is_success(self) -> bool:
        """Check if result is successful."""
        return self.status == ResultStatus.SUCCESS

    def is_failure(self) -> bool:
        """Check if result is a failure."""
        return self.status == ResultStatus.FAILURE


class CapabilityType(str, Enum):
    """Types of agent capabilities."""
    DECISION = "decision"
    ANALYSIS = "analysis"
    ORCHESTRATION = "orchestration"
    TRANSFORMATION = "transformation"
    INTEGRATION = "integration"
    PERSISTENCE = "persistence"


@dataclass
class AgentCapability:
    """Describes what an agent can do."""
    type: CapabilityType
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    required_context: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class DataClassification(str, Enum):
    """Data sensitivity classification."""
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


@dataclass
class PrivacyPolicy:
    """Declarative privacy rules for data handling."""
    name: str
    data_classification: DataClassification
    retention_period: Optional[timedelta] = None
    allowed_operations: list[str] = field(default_factory=list)
    requires_consent: bool = False
    anonymization_rules: dict[str, str] = field(default_factory=dict)
    min_access_level: str = "user"


@dataclass
class ContextFrame:
    """
    A snapshot of relevant state at a point in time.
    Immutable and composable.
    """
    entity_id: str
    entity_type: str
    timestamp: datetime
    temporal_info: dict[str, Any] = field(default_factory=dict)  # when-related data
    spatial_info: dict[str, Any] = field(default_factory=dict)   # where-related data
    relational_info: dict[str, Any] = field(default_factory=dict)  # who-related data
    domain_data: dict[str, Any] = field(default_factory=dict)    # domain-specific data
    source: str = "unknown"
    ttl: Optional[timedelta] = None

    def is_expired(self) -> bool:
        """Check if context frame has expired."""
        if self.ttl is None:
            return False
        return datetime.now() - self.timestamp > self.ttl

    def merge(self, other: "ContextFrame") -> "ContextFrame":
        """Merge two context frames (most recent wins)."""
        if other.timestamp > self.timestamp:
            newer, older = other, self
        else:
            newer, older = self, other

        return ContextFrame(
            entity_id=newer.entity_id,
            entity_type=newer.entity_type,
            timestamp=newer.timestamp,
            temporal_info={**older.temporal_info, **newer.temporal_info},
            spatial_info={**older.spatial_info, **newer.spatial_info},
            relational_info={**older.relational_info, **newer.relational_info},
            domain_data={**older.domain_data, **newer.domain_data},
            source=newer.source,
            ttl=newer.ttl,
        )


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    id: str
    action: str
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None
    timeout: Optional[timedelta] = None
    retry_count: int = 3
    retry_delay: timedelta = field(default_factory=lambda: timedelta(seconds=1))
    depends_on: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowStatus(str, Enum):
    """Status of workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowExecution:
    """Execution state of a workflow."""
    workflow_id: str
    execution_id: str
    status: WorkflowStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    step_results: dict[str, Result[Any]] = field(default_factory=dict)
    current_step: Optional[str] = None
    error: Optional[str] = None


class EventType(str, Enum):
    """Types of events in the system."""
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_STEP_COMPLETED = "workflow.step_completed"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    CONTEXT_UPDATED = "context.updated"
    DATA_ACCESSED = "data.accessed"
    DATA_STORED = "data.stored"
    ERROR_OCCURRED = "error.occurred"


@dataclass
class Event:
    """Base event class."""
    type: EventType
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
