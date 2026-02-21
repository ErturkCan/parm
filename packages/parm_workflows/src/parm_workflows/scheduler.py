"""Workflow scheduling for cron-based and event-triggered execution."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from .workflow import Workflow


@dataclass
class ScheduledWorkflow:
    """A workflow scheduled for execution."""
    workflow: Workflow
    cron_expression: Optional[str] = None
    event_trigger: Optional[str] = None
    next_execution: Optional[datetime] = None
    last_execution: Optional[datetime] = None
    is_active: bool = True


class WorkflowScheduler:
    """
    Schedules workflow execution based on cron expressions and events.
    """

    def __init__(self) -> None:
        """Initialize the scheduler."""
        self._scheduled_workflows: dict[str, ScheduledWorkflow] = {}
        self._event_triggers: dict[str, list[str]] = {}  # event -> [workflow_ids]
        self._execution_callbacks: list[Callable[[Workflow], None]] = []

    def schedule_cron(
        self,
        workflow: Workflow,
        cron_expression: str,
    ) -> str:
        """
        Schedule a workflow to run on a cron schedule.

        Args:
            workflow: Workflow to schedule
            cron_expression: Cron expression (simplified: "*/5 * * * *" means every 5 minutes)

        Returns:
            Scheduled workflow ID
        """
        scheduled = ScheduledWorkflow(
            workflow=workflow,
            cron_expression=cron_expression,
            next_execution=self._calculate_next_execution(cron_expression),
        )
        workflow_id = f"{workflow.id}_cron"
        self._scheduled_workflows[workflow_id] = scheduled
        return workflow_id

    def schedule_event(
        self,
        workflow: Workflow,
        event_type: str,
    ) -> str:
        """
        Schedule a workflow to run on event trigger.

        Args:
            workflow: Workflow to schedule
            event_type: Event type to trigger on

        Returns:
            Scheduled workflow ID
        """
        scheduled = ScheduledWorkflow(
            workflow=workflow,
            event_trigger=event_type,
        )
        workflow_id = f"{workflow.id}_event_{event_type}"
        self._scheduled_workflows[workflow_id] = scheduled

        if event_type not in self._event_triggers:
            self._event_triggers[event_type] = []
        self._event_triggers[event_type].append(workflow_id)

        return workflow_id

    def unschedule(self, scheduled_id: str) -> bool:
        """
        Unschedule a workflow.

        Args:
            scheduled_id: Scheduled workflow ID

        Returns:
            True if unscheduled, False if not found
        """
        if scheduled_id not in self._scheduled_workflows:
            return False

        scheduled = self._scheduled_workflows.pop(scheduled_id)

        # Remove from event triggers if applicable
        if scheduled.event_trigger and scheduled.event_trigger in self._event_triggers:
            self._event_triggers[scheduled.event_trigger].remove(scheduled_id)

        return True

    def trigger_event(self, event_type: str) -> list[Workflow]:
        """
        Trigger event-based workflows.

        Args:
            event_type: Event type that occurred

        Returns:
            List of workflows triggered
        """
        triggered_workflows = []

        for workflow_id in self._event_triggers.get(event_type, []):
            scheduled = self._scheduled_workflows.get(workflow_id)
            if scheduled and scheduled.is_active:
                triggered_workflows.append(scheduled.workflow)
                scheduled.last_execution = datetime.now()
                self._execute_workflow(scheduled.workflow)

        return triggered_workflows

    def get_due_workflows(self) -> list[Workflow]:
        """
        Get workflows that are due for execution based on cron schedule.

        Returns:
            List of due workflows
        """
        due_workflows = []
        now = datetime.now()

        for scheduled in self._scheduled_workflows.values():
            if (
                scheduled.is_active
                and scheduled.cron_expression
                and scheduled.next_execution
                and scheduled.next_execution <= now
            ):
                due_workflows.append(scheduled.workflow)
                scheduled.last_execution = now
                scheduled.next_execution = self._calculate_next_execution(scheduled.cron_expression)
                self._execute_workflow(scheduled.workflow)

        return due_workflows

    def on_execution(self, callback: Callable[[Workflow], None]) -> None:
        """
        Register a callback when a workflow is executed.

        Args:
            callback: Callback function
        """
        self._execution_callbacks.append(callback)

    def activate(self, scheduled_id: str) -> bool:
        """Activate a scheduled workflow."""
        if scheduled_id in self._scheduled_workflows:
            self._scheduled_workflows[scheduled_id].is_active = True
            return True
        return False

    def deactivate(self, scheduled_id: str) -> bool:
        """Deactivate a scheduled workflow."""
        if scheduled_id in self._scheduled_workflows:
            self._scheduled_workflows[scheduled_id].is_active = False
            return True
        return False

    def get_scheduled(self) -> list[ScheduledWorkflow]:
        """Get all scheduled workflows."""
        return list(self._scheduled_workflows.values())

    def _execute_workflow(self, workflow: Workflow) -> None:
        """Execute a workflow via callbacks."""
        for callback in self._execution_callbacks:
            try:
                callback(workflow)
            except Exception:
                pass  # Ignore callback errors

    @staticmethod
    def _calculate_next_execution(cron_expression: str) -> datetime:
        """
        Calculate next execution time based on cron expression.
        Simplified implementation - in production, use croniter library.

        Args:
            cron_expression: Cron expression

        Returns:
            Next execution time
        """
        # Very simplified parsing: assume "*/N * * * *" format for "every N minutes"
        try:
            parts = cron_expression.split()
            if parts[0].startswith("*/"):
                minutes = int(parts[0][2:])
                now = datetime.now()
                next_time = now + timedelta(minutes=minutes)
                return next_time
        except (ValueError, IndexError):
            pass

        # Default: next execution in 1 hour
        return datetime.now() + timedelta(hours=1)
