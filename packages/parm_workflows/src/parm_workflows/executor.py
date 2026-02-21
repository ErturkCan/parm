"""Workflow execution engine."""

import time
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
from uuid import uuid4

from parm_core import ContextFrame, Result, ResultStatus, WorkflowExecution, WorkflowStatus

from .workflow import Workflow


class WorkflowExecutor:
    """
    Executes workflow DAGs.
    Tracks step status, handles timeouts, retries failed steps.
    Emits events for state transitions.
    """

    def __init__(self) -> None:
        """Initialize the executor."""
        self._executions: dict[str, WorkflowExecution] = {}
        self._step_handlers: dict[str, Callable[[Any], Result[Any]]] = {}
        self._event_callbacks: list[Callable[[str, WorkflowExecution], None]] = []

    def register_step_handler(self, action: str, handler: Callable[[Any], Result[Any]]) -> None:
        """
        Register a handler for a workflow step action.

        Args:
            action: Action name
            handler: Handler function
        """
        self._step_handlers[action] = handler

    def on_status_change(self, callback: Callable[[str, WorkflowExecution], None]) -> None:
        """
        Register a callback for workflow status changes.

        Args:
            callback: Callback function (execution_id, execution)
        """
        self._event_callbacks.append(callback)

    def run(
        self,
        workflow: Workflow,
        context: Optional[ContextFrame] = None,
        variables: Optional[dict[str, Any]] = None,
    ) -> WorkflowExecution:
        """
        Run a workflow.

        Args:
            workflow: Workflow to execute
            context: Optional context frame
            variables: Optional variables for the workflow

        Returns:
            WorkflowExecution with results
        """
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            execution_id=str(uuid4()),
            status=WorkflowStatus.PENDING,
        )

        self._executions[execution.execution_id] = execution
        self._emit_status_change(execution)

        # Start execution
        execution.started_at = datetime.now()
        execution.status = WorkflowStatus.RUNNING
        self._emit_status_change(execution)

        variables = variables or {}

        # Get root steps (no dependencies)
        root_steps = workflow.get_root_steps()
        executed_steps = set()

        # Execute workflow in topological order
        while executed_steps != set(workflow.steps.keys()):
            # Find steps ready to execute (all dependencies satisfied)
            ready_steps = []
            for step_id in workflow.steps.keys():
                if step_id in executed_steps:
                    continue

                deps = workflow.get_dependencies(step_id)
                if all(dep in executed_steps for dep in deps):
                    ready_steps.append(step_id)

            if not ready_steps:
                # No more steps can execute, but not all executed = error
                if executed_steps != set(workflow.steps.keys()):
                    execution.status = WorkflowStatus.FAILED
                    execution.error = "Workflow deadlocked or has unexecuted steps"
                    self._emit_status_change(execution)
                    return execution

            # Execute ready steps
            for step_id in ready_steps:
                step = workflow.get_step(step_id)
                if not step:
                    continue

                # Check condition if present
                if step.condition:
                    if not self._evaluate_condition(step.condition, variables):
                        executed_steps.add(step_id)
                        execution.step_results[step_id] = Result.success(None)
                        continue

                # Execute with retries
                result = self._execute_step_with_retry(
                    step_id, step, context, variables
                )
                execution.step_results[step_id] = result

                if not result.is_success():
                    execution.status = WorkflowStatus.FAILED
                    execution.current_step = step_id
                    execution.error = result.error
                    self._emit_status_change(execution)
                    return execution

                # Store step output in variables for use in downstream steps
                if result.data:
                    variables[f"step_{step_id}_output"] = result.data

                executed_steps.add(step_id)
                execution.current_step = step_id
                self._emit_status_change(execution)

        # All steps completed successfully
        execution.status = WorkflowStatus.COMPLETED
        execution.completed_at = datetime.now()
        self._emit_status_change(execution)

        return execution

    def pause(self, execution_id: str) -> bool:
        """
        Pause a running workflow.

        Args:
            execution_id: Execution ID to pause

        Returns:
            True if paused, False if not found
        """
        execution = self._executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.PAUSED
            self._emit_status_change(execution)
            return True
        return False

    def resume(self, execution_id: str) -> bool:
        """
        Resume a paused workflow.

        Args:
            execution_id: Execution ID to resume

        Returns:
            True if resumed, False if not found
        """
        execution = self._executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.PAUSED:
            execution.status = WorkflowStatus.RUNNING
            self._emit_status_change(execution)
            return True
        return False

    def cancel(self, execution_id: str) -> bool:
        """
        Cancel a workflow execution.

        Args:
            execution_id: Execution ID to cancel

        Returns:
            True if cancelled, False if not found
        """
        execution = self._executions.get(execution_id)
        if execution and execution.status in (
            WorkflowStatus.PENDING,
            WorkflowStatus.RUNNING,
            WorkflowStatus.PAUSED,
        ):
            execution.status = WorkflowStatus.CANCELLED
            execution.completed_at = datetime.now()
            self._emit_status_change(execution)
            return True
        return False

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution by ID."""
        return self._executions.get(execution_id)

    def _execute_step_with_retry(
        self,
        step_id: str,
        step: Any,  # WorkflowStep
        context: Optional[ContextFrame],
        variables: dict[str, Any],
    ) -> Result[Any]:
        """Execute a step with retry logic."""
        handler = self._step_handlers.get(step.action)
        if not handler:
            return Result.failure(f"No handler for action '{step.action}'")

        last_error = None
        for attempt in range(step.retry_count):
            try:
                # Prepare inputs
                inputs = step.inputs.copy()
                for key, value in inputs.items():
                    if isinstance(value, str) and value.startswith("$"):
                        var_name = value[1:]
                        inputs[key] = variables.get(var_name)

                # Execute with timeout
                start_time = datetime.now()
                result = handler(inputs)

                if step.timeout:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed > step.timeout.total_seconds():
                        return Result.failure(
                            f"Step {step_id} timed out after {elapsed:.1f}s"
                        )

                if result.is_success():
                    return result

                last_error = result.error
                if attempt < step.retry_count - 1:
                    time.sleep(1)  # Simple delay between retries
            except Exception as e:
                last_error = str(e)
                if attempt < step.retry_count - 1:
                    time.sleep(1)

        return Result.failure(f"Step {step_id} failed: {last_error}")

    def _evaluate_condition(self, condition: str, variables: dict[str, Any]) -> bool:
        """Evaluate a step condition."""
        try:
            return bool(eval(condition, {"__builtins__": {}}, variables))
        except Exception:
            return True  # If condition evaluation fails, execute step anyway

    def _emit_status_change(self, execution: WorkflowExecution) -> None:
        """Emit status change callbacks."""
        for callback in self._event_callbacks:
            try:
                callback(execution.execution_id, execution)
            except Exception:
                pass  # Ignore callback errors
