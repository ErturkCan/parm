"""KeepClos connector - Shows how relationship intelligence plugs into PARM."""

from datetime import timedelta, datetime, timezone
from typing import Any, Optional

from parm_agents import BaseAgent, AgentCapability, CapabilityType
from parm_context import RelationshipProvider, ContextResolver
from parm_core import ContextFrame, Result, ParmEngine, CapabilityType as CapType
from parm_workflows import WorkflowBuilder, WorkflowExecutor


class RelationshipAgent(BaseAgent):
    """
    KeepClos agent: Analyzes and manages relationships.
    """

    def __init__(self) -> None:
        super().__init__("relationship_analyzer", "Analyzes relationships")

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                type=CapabilityType.DECISION,
                name="relationship_scoring",
                description="Score relationship strength and predict engagement",
                input_schema={
                    "person_id": "string",
                    "relationship_history": "list",
                },
                output_schema={
                    "relationship_score": "int",
                    "engagement_likelihood": "float",
                    "recommended_action": "string",
                },
                required_context=["temporal", "relational"],
                tags=["relationships", "intelligence"],
            )
        ]

    def execute(
        self,
        context: Optional[ContextFrame] = None,
        **kwargs: Any
    ) -> Result[Any]:
        """Execute relationship analysis."""
        person_id = kwargs.get("person_id")
        relationship_history = kwargs.get("relationship_history", [])

        if not person_id:
            return Result.failure("Missing person_id")

        # Calculate relationship score based on history
        score = min(100, len(relationship_history) * 10)
        likelihood = len(relationship_history) / 100.0

        action = "maintain_contact" if score > 50 else "re_engage"

        return Result.success({
            "person_id": person_id,
            "relationship_score": score,
            "engagement_likelihood": likelihood,
            "recommended_action": action,
            "interactions_count": len(relationship_history),
        })


class ReminderDecisionAgent(BaseAgent):
    """KeepClos agent: Decides when to send reminders."""

    def __init__(self) -> None:
        super().__init__("reminder_decider", "Decides reminder timing")

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                type=CapabilityType.DECISION,
                name="reminder_decision",
                description="Decide if reminder should be sent",
                tags=["relationships", "reminders"],
            )
        ]

    def execute(
        self,
        context: Optional[ContextFrame] = None,
        **kwargs: Any
    ) -> Result[Any]:
        """Execute reminder decision logic."""
        person_id = kwargs.get("person_id")
        days_since_contact = kwargs.get("days_since_contact", 0)

        should_remind = days_since_contact > 30  # Remind if more than 30 days

        return Result.success({
            "person_id": person_id,
            "should_send_reminder": should_remind,
            "days_since_contact": days_since_contact,
            "reminder_type": "check_in" if should_remind else "none",
        })


class RelationshipContextProvider(RelationshipProvider):
    """Provides relationship context with enhanced tracking."""

    def __init__(self) -> None:
        super().__init__("keepclos_relationship_provider")
        self._last_contact: dict[str, datetime] = {}

    def record_contact(self, user_id: str, contact_id: str) -> None:
        """Record a contact event."""
        self._last_contact[f"{user_id}_{contact_id}"] = datetime.now(timezone.utc)

    def get_context(self, entity_id: str, entity_type: str) -> Optional[ContextFrame]:
        """Get relationship context for a user."""
        if entity_type != "user":
            return None

        relationships = self._relationships.get(entity_id, {})

        # Calculate days since last contact for each relationship
        contacts_info = {}
        for contact_id, rel_data in relationships.items():
            key = f"{entity_id}_{contact_id}"
            last_contact = self._last_contact.get(key, datetime.now(timezone.utc))
            days_since = (datetime.now(timezone.utc) - last_contact).days
            contacts_info[contact_id] = {
                **rel_data,
                "days_since_contact": days_since,
            }

        relational_info = {
            "relationships": contacts_info,
            "relationship_count": len(relationships),
            "connected_entities": list(relationships.keys()),
            "stale_relationships": [
                cid for cid, info in contacts_info.items()
                if info.get("days_since_contact", 0) > 60
            ],
        }

        return ContextFrame(
            entity_id=entity_id,
            entity_type=entity_type,
            timestamp=datetime.now(timezone.utc),
            temporal_info={},
            spatial_info={},
            relational_info=relational_info,
            domain_data={},
            source="keepclos_relationship_provider",
            ttl=timedelta(hours=1),
        )


def setup_keepclos_on_parm(engine: ParmEngine) -> None:
    """
    Set up KeepClos on the PARM platform.

    Args:
        engine: ParmEngine instance
    """
    # 1. Register agents
    analyzer_agent = RelationshipAgent()
    reminder_agent = ReminderDecisionAgent()

    engine.register_agent(
        "keepclos_analyzer",
        analyzer_agent,
        description="Analyzes relationships",
        tags=["relationships", "keepclos"],
        capabilities=["relationship_scoring"],
    )

    engine.register_agent(
        "keepclos_reminder",
        reminder_agent,
        description="Decides reminder timing",
        tags=["relationships", "keepclos"],
        capabilities=["reminder_decision"],
    )

    # 2. Register relationship context provider
    relationship_provider = RelationshipContextProvider()
    engine.register_context_provider(
        "keepclos_relationship_provider",
        relationship_provider,
        description="Provides relationship intelligence",
        tags=["relationships", "contacts"],
    )

    # 3. Create reminder workflow
    reminder_workflow = (
        WorkflowBuilder("reminder_workflow", "Relationship reminder workflow")
        .add_step(
            "load_context",
            "load_relationship_context",
            inputs={"user_id": "$user_id"},
            timeout=timedelta(seconds=10),
        )
        .add_step(
            "score_relationship",
            "score_relationship",
            depends_on=["load_context"],
            inputs={"user_id": "$user_id"},
            timeout=timedelta(seconds=10),
        )
        .add_step(
            "decide_reminder",
            "decide_reminder",
            depends_on=["score_relationship"],
            timeout=timedelta(seconds=5),
        )
        .add_step(
            "send_reminder",
            "send_reminder",
            depends_on=["decide_reminder"],
            condition="decide_reminder_output['should_send_reminder']",
            timeout=timedelta(seconds=10),
        )
        .build()
    )

    engine.register_workflow(
        "keepclos_reminder_workflow",
        reminder_workflow,
        description="Proactive relationship reminder",
        tags=["relationships", "keepclos"],
    )

    # 4. Register workflow handlers
    executor = WorkflowExecutor()

    executor.register_step_handler("load_relationship_context", lambda inputs: load_context(inputs))
    executor.register_step_handler("score_relationship", lambda inputs: score_relationship(inputs))
    executor.register_step_handler("decide_reminder", lambda inputs: decide_reminder(inputs))
    executor.register_step_handler("send_reminder", lambda inputs: send_reminder(inputs))

    print("[KeepClos] Connected to PARM")
    print("  - Agents: RelationshipAnalyzer, ReminderDecider")
    print("  - Workflow: Reminder (load context → score → decide → send)")
    print("  - Context: RelationshipContextProvider")


# Handler functions for workflow steps
def load_context(inputs: dict[str, Any]) -> Result[Any]:
    """Load relationship context."""
    user_id = inputs.get("user_id")
    return Result.success({
        "user_id": user_id,
        "relationships": ["contact_1", "contact_2", "contact_3"],
    })


def score_relationship(inputs: dict[str, Any]) -> Result[Any]:
    """Score relationship."""
    user_id = inputs.get("user_id")
    return Result.success({
        "user_id": user_id,
        "score": 75,
        "strength": "strong",
    })


def decide_reminder(inputs: dict[str, Any]) -> Result[Any]:
    """Decide if reminder should be sent."""
    score = inputs.get("score", 50)
    should_remind = score < 70
    return Result.success({
        "should_send_reminder": should_remind,
        "reason": "relationship_needs_attention" if should_remind else "recently_contacted",
    })


def send_reminder(inputs: dict[str, Any]) -> Result[Any]:
    """Send reminder notification."""
    return Result.success({
        "reminder_sent": True,
        "message_type": "check_in_suggestion",
    })
