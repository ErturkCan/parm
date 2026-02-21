"""Workflow definition and building."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
from uuid import uuid4

from parm_core import WorkflowStep, WorkflowStatus, WorkflowExecution, Result


@dataclass
class Workflow:
    """
    A directed acyclic graph (DAG) of workflow steps.
    Each step has inputs, outputs, conditions, and timeouts.
    """
    id: str
    name: str
    description: str = ""
    steps: dict[str, WorkflowStep] = field(default_factory=dict)
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_step(
        self,
        step_id: str,
        action: str,
        inputs: Optional[dict[str, Any]] = None,
        depends_on: Optional[list[str]] = None,
        timeout: Optional[timedelta] = None,
        condition: Optional[str] = None,
        retry_count: int = 3,
    ) -> "Workflow":
        """
        Add a step to the workflow.

        Args:
            step_id: Unique step identifier
            action: Action to perform (agent name or handler name)
            inputs: Step inputs
            depends_on: List of step IDs this depends on
            timeout: Step timeout
            condition: Conditional expression for step execution
            retry_count: Number of retries on failure

        Returns:
            Self for fluent API
        """
        step = WorkflowStep(
            id=step_id,
            action=action,
            inputs=inputs or {},
            depends_on=depends_on or [],
            timeout=timeout,
            condition=condition,
            retry_count=retry_count,
        )
        self.steps[step_id] = step
        return self

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by ID."""
        return self.steps.get(step_id)

    def get_all_steps(self) -> list[WorkflowStep]:
        """Get all steps in the workflow."""
        return list(self.steps.values())

    def get_dependencies(self, step_id: str) -> list[str]:
        """Get the dependencies of a step."""
        step = self.steps.get(step_id)
        return step.depends_on if step else []

    def get_downstream_steps(self, step_id: str) -> list[str]:
        """Get all steps that depend on a given step."""
        downstream = []
        for sid, step in self.steps.items():
            if step_id in step.depends_on:
                downstream.append(sid)
        return downstream

    def get_root_steps(self) -> list[str]:
        """Get steps with no dependencies (entry points)."""
        return [sid for sid, step in self.steps.items() if not step.depends_on]

    def get_leaf_steps(self) -> list[str]:
        """Get steps with no downstream dependencies (exit points)."""
        return [sid for sid in self.steps if not self.get_downstream_steps(sid)]

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate the workflow for structural integrity.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.steps:
            return False, "Workflow must have at least one step"

        # Check for circular dependencies
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            step = self.steps.get(node)
            if step:
                for dep in step.depends_on:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(node)
            return False

        for step_id in self.steps:
            if step_id not in visited:
                if has_cycle(step_id):
                    return False, "Workflow contains circular dependencies"

        # Check that all dependencies exist
        for step in self.steps.values():
            for dep in step.depends_on:
                if dep not in self.steps:
                    return False, f"Step '{step.id}' depends on non-existent step '{dep}'"

        return True, None


class WorkflowBuilder:
    """Fluent builder for creating workflows."""

    def __init__(self, name: str, description: str = "") -> None:
        """
        Initialize the builder.

        Args:
            name: Workflow name
            description: Workflow description
        """
        self._workflow = Workflow(
            id=str(uuid4()),
            name=name,
            description=description,
        )

    def add_step(
        self,
        step_id: str,
        action: str,
        inputs: Optional[dict[str, Any]] = None,
        depends_on: Optional[list[str]] = None,
        timeout: Optional[timedelta] = None,
        condition: Optional[str] = None,
        retry_count: int = 3,
    ) -> "WorkflowBuilder":
        """
        Add a step to the workflow.

        Args:
            step_id: Unique step identifier
            action: Action to perform
            inputs: Step inputs
            depends_on: Dependencies
            timeout: Step timeout
            condition: Execution condition
            retry_count: Retry count

        Returns:
            Self for fluent API
        """
        self._workflow.add_step(
            step_id=step_id,
            action=action,
            inputs=inputs,
            depends_on=depends_on,
            timeout=timeout,
            condition=condition,
            retry_count=retry_count,
        )
        return self

    def with_metadata(self, key: str, value: Any) -> "WorkflowBuilder":
        """
        Add metadata to the workflow.

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            Self for fluent API
        """
        self._workflow.metadata[key] = value
        return self

    def set_version(self, version: str) -> "WorkflowBuilder":
        """
        Set workflow version.

        Args:
            version: Version string

        Returns:
            Self for fluent API
        """
        self._workflow.version = version
        return self

    def build(self) -> Workflow:
        """
        Build and return the workflow.

        Returns:
            Workflow instance

        Raises:
            ValueError: If workflow is invalid
        """
        is_valid, error = self._workflow.validate()
        if not is_valid:
            raise ValueError(f"Invalid workflow: {error}")
        return self._workflow
