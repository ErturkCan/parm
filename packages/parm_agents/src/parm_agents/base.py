"""Base agent classes for PARM."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from parm_core import AgentCapability, ContextFrame, Result


class AgentState(str, Enum):
    """States an agent can be in."""
    INIT = "init"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class AgentMetrics:
    """Metrics for an agent instance."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_execution_time_ms: float = 0.0


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Agents are focused, reusable components that perform specific tasks.
    """

    def __init__(self, name: str, description: str = "") -> None:
        """
        Initialize a base agent.

        Args:
            name: Agent name
            description: Agent description
        """
        self.name = name
        self.description = description
        self.state = AgentState.INIT
        self.metrics = AgentMetrics()
        self._error: Optional[str] = None

    @abstractmethod
    def get_capabilities(self) -> list[AgentCapability]:
        """
        Define what this agent can do.

        Returns:
            List of capabilities
        """
        pass

    @abstractmethod
    def execute(self, context: Optional[ContextFrame] = None, **kwargs: Any) -> Result[Any]:
        """
        Execute the agent's primary task.

        Args:
            context: Optional context frame with relevant state
            **kwargs: Additional keyword arguments

        Returns:
            Result of execution
        """
        pass

    def initialize(self) -> Result[None]:
        """
        Initialize the agent (setup, validation, etc.).

        Returns:
            Result indicating success or failure
        """
        try:
            self.state = AgentState.READY
            return Result.success(None)
        except Exception as e:
            self.state = AgentState.ERROR
            self._error = str(e)
            return Result.failure(str(e))

    def shutdown(self) -> Result[None]:
        """
        Shutdown the agent and cleanup resources.

        Returns:
            Result indicating success or failure
        """
        try:
            self.state = AgentState.SHUTDOWN
            return Result.success(None)
        except Exception as e:
            return Result.failure(str(e))

    def get_state(self) -> AgentState:
        """Get the agent's current state."""
        return self.state

    def get_metrics(self) -> AgentMetrics:
        """Get the agent's execution metrics."""
        return self.metrics

    def get_error(self) -> Optional[str]:
        """Get the last error message if any."""
        return self._error

    def is_ready(self) -> bool:
        """Check if agent is ready for execution."""
        return self.state == AgentState.READY

    def is_healthy(self) -> bool:
        """Check if agent is healthy."""
        return self.state in (AgentState.INIT, AgentState.READY)


class AgentPool:
    """
    Manages a pool of agent instances.
    Useful for load balancing and parallelization.
    """

    def __init__(self, agent_class: type, count: int = 1, **init_kwargs: Any) -> None:
        """
        Initialize an agent pool.

        Args:
            agent_class: Agent class to instantiate
            count: Number of instances to create
            **init_kwargs: Arguments to pass to agent constructor
        """
        self.agent_class = agent_class
        self.agents: list[BaseAgent] = []
        self._next_index = 0

        for i in range(count):
            # Create unique names for each instance
            agent_name = f"{init_kwargs.get('name', agent_class.__name__)}_{i}"
            agent = agent_class(name=agent_name, **{k: v for k, v in init_kwargs.items() if k != "name"})
            self.agents.append(agent)

    def get_next_ready(self) -> Optional[BaseAgent]:
        """
        Get the next ready agent in round-robin fashion.

        Returns:
            Next ready agent or None if none available
        """
        start_index = self._next_index
        while True:
            agent = self.agents[self._next_index]
            self._next_index = (self._next_index + 1) % len(self.agents)

            if agent.is_ready():
                return agent

            # If we've checked all agents, return None
            if self._next_index == start_index:
                return None

    def get_all_ready(self) -> list[BaseAgent]:
        """Get all ready agents."""
        return [a for a in self.agents if a.is_ready()]

    def get_all(self) -> list[BaseAgent]:
        """Get all agents."""
        return self.agents.copy()

    def initialize_all(self) -> list[Result[None]]:
        """Initialize all agents in the pool."""
        return [agent.initialize() for agent in self.agents]

    def shutdown_all(self) -> list[Result[None]]:
        """Shutdown all agents in the pool."""
        return [agent.shutdown() for agent in self.agents]

    def health_check(self) -> dict[str, bool]:
        """Get health status of all agents."""
        return {agent.name: agent.is_healthy() for agent in self.agents}

    def size(self) -> int:
        """Get the pool size."""
        return len(self.agents)
