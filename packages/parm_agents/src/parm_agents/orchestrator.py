"""Agent orchestration for routing tasks to appropriate agents."""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional

from parm_core import AgentCapability, CapabilityType, ContextFrame, Result, ResultStatus

from .base import BaseAgent


@dataclass
class RoutingRule:
    """A rule for routing tasks to agents."""
    capability_type: CapabilityType
    required_tags: list[str] = None
    priority: int = 0

    def __post_init__(self) -> None:
        if self.required_tags is None:
            self.required_tags = []


class AgentOrchestrator:
    """
    Routes tasks to agents based on capability matching.
    Supports sequential chains, parallel fan-out, and conditional routing.
    """

    def __init__(self) -> None:
        """Initialize the orchestrator."""
        self._agents: dict[str, BaseAgent] = {}
        self._routing_rules: list[RoutingRule] = []
        self._retry_config = {
            "max_attempts": 3,
            "backoff_factor": 2.0,
            "initial_delay": 1.0,
        }

    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the orchestrator.

        Args:
            agent: Agent to register
        """
        self._agents[agent.name] = agent

    def unregister_agent(self, agent_name: str) -> None:
        """Unregister an agent."""
        self._agents.pop(agent_name, None)

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self._agents.get(name)

    def find_agents_by_capability(
        self, capability_type: CapabilityType, tags: Optional[list[str]] = None
    ) -> list[BaseAgent]:
        """
        Find agents that provide a specific capability.

        Args:
            capability_type: Type of capability needed
            tags: Optional tags that agents must have

        Returns:
            List of matching agents
        """
        tags = tags or []
        matching = []

        for agent in self._agents.values():
            if not agent.is_ready():
                continue

            capabilities = agent.get_capabilities()
            for cap in capabilities:
                if cap.type == capability_type:
                    # Check if agent has all required tags
                    agent_tags = set(cap.tags)
                    if all(tag in agent_tags for tag in tags):
                        matching.append(agent)
                        break

        return matching

    def add_routing_rule(self, rule: RoutingRule) -> None:
        """
        Add a routing rule.

        Args:
            rule: Routing rule to add
        """
        self._routing_rules.append(rule)
        # Sort by priority (higher priority first)
        self._routing_rules.sort(key=lambda r: r.priority, reverse=True)

    def route(
        self, capability_type: CapabilityType, tags: Optional[list[str]] = None
    ) -> Optional[BaseAgent]:
        """
        Route to the best agent for a given capability.

        Args:
            capability_type: Type of capability needed
            tags: Optional tags for filtering

        Returns:
            Best matching agent or None if none found
        """
        agents = self.find_agents_by_capability(capability_type, tags)
        return agents[0] if agents else None

    def execute_with_retry(
        self,
        agent: BaseAgent,
        context: Optional[ContextFrame] = None,
        **kwargs: Any,
    ) -> Result[Any]:
        """
        Execute an agent with automatic retry on failure.

        Args:
            agent: Agent to execute
            context: Optional context frame
            **kwargs: Additional arguments

        Returns:
            Result of execution
        """
        max_attempts = self._retry_config["max_attempts"]
        backoff_factor = self._retry_config["backoff_factor"]
        initial_delay = self._retry_config["initial_delay"]

        last_error = None
        for attempt in range(max_attempts):
            try:
                result = agent.execute(context=context, **kwargs)
                if result.is_success():
                    return result

                last_error = result.error
                if attempt < max_attempts - 1:
                    # Calculate backoff delay
                    delay = initial_delay * (backoff_factor ** attempt)
                    time.sleep(delay)
            except Exception as e:
                last_error = str(e)
                if attempt < max_attempts - 1:
                    delay = initial_delay * (backoff_factor ** attempt)
                    time.sleep(delay)

        return Result.failure(f"Failed after {max_attempts} attempts: {last_error}")

    async def execute_parallel(
        self,
        agents: list[BaseAgent],
        context: Optional[ContextFrame] = None,
        **kwargs: Any,
    ) -> Result[dict[str, Any]]:
        """
        Execute multiple agents in parallel.

        Args:
            agents: List of agents to execute
            context: Optional context frame
            **kwargs: Additional arguments

        Returns:
            Result with dictionary mapping agent names to their results
        """
        tasks = []
        for agent in agents:
            tasks.append(self._execute_async_wrapper(agent, context, **kwargs))

        try:
            results = await asyncio.gather(*tasks)
            return Result.success({
                agents[i].name: results[i] for i in range(len(agents))
            })
        except Exception as e:
            return Result.failure(f"Parallel execution failed: {str(e)}")

    async def _execute_async_wrapper(
        self,
        agent: BaseAgent,
        context: Optional[ContextFrame] = None,
        **kwargs: Any,
    ) -> Any:
        """Wrapper to execute agent in async context."""
        return agent.execute(context=context, **kwargs)

    def set_retry_config(
        self,
        max_attempts: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
    ) -> None:
        """
        Configure retry behavior.

        Args:
            max_attempts: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier
            initial_delay: Initial delay in seconds
        """
        self._retry_config = {
            "max_attempts": max_attempts,
            "backoff_factor": backoff_factor,
            "initial_delay": initial_delay,
        }

    def get_all_agents(self) -> list[BaseAgent]:
        """Get all registered agents."""
        return list(self._agents.values())

    def health_check(self) -> dict[str, bool]:
        """Get health status of all agents."""
        return {name: agent.is_healthy() for name, agent in self._agents.items()}
