"""Agent chaining for sequential composition."""

from typing import Any, Callable, Optional

from parm_core import ContextFrame, Result, ResultStatus

from .base import BaseAgent


class AgentChain:
    """
    Compose agents sequentially where output of one feeds input of next.
    """

    def __init__(self) -> None:
        """Initialize the chain."""
        self.agents: list[BaseAgent] = []
        self._input_transformer: Optional[Callable[[Any], Any]] = None
        self._output_transformer: Optional[Callable[[Any], Any]] = None

    def add_agent(self, agent: BaseAgent) -> "AgentChain":
        """
        Add an agent to the chain.

        Args:
            agent: Agent to add

        Returns:
            Self for fluent API
        """
        self.agents.append(agent)
        return self

    def set_input_transformer(self, transformer: Callable[[Any], Any]) -> "AgentChain":
        """
        Set a transformer for input data before first agent.

        Args:
            transformer: Function to transform input

        Returns:
            Self for fluent API
        """
        self._input_transformer = transformer
        return self

    def set_output_transformer(self, transformer: Callable[[Any], Any]) -> "AgentChain":
        """
        Set a transformer for output data after last agent.

        Args:
            transformer: Function to transform output

        Returns:
            Self for fluent API
        """
        self._output_transformer = transformer
        return self

    def execute(
        self,
        input_data: Any,
        context: Optional[ContextFrame] = None,
        stop_on_error: bool = True,
    ) -> Result[Any]:
        """
        Execute all agents in sequence.

        Args:
            input_data: Input to first agent
            context: Optional context frame (passed to all agents)
            stop_on_error: If True, stop chain on first error

        Returns:
            Result from final agent or accumulated data if stop_on_error is False
        """
        if not self.agents:
            return Result.failure("No agents in chain")

        # Transform input if needed
        current_data = input_data
        if self._input_transformer:
            try:
                current_data = self._input_transformer(current_data)
            except Exception as e:
                return Result.failure(f"Input transformation failed: {str(e)}")

        # Execute agents in sequence
        results = []
        for agent in self.agents:
            try:
                result = agent.execute(context=context, **{"data": current_data})

                if not result.is_success():
                    results.append(result)
                    if stop_on_error:
                        return Result.partial(
                            data=current_data,
                            error=f"Agent {agent.name} failed: {result.error}",
                            metadata={"failed_at": agent.name, "results": results},
                        )
                    else:
                        # Continue with previous output
                        continue

                results.append(result)
                current_data = result.data
            except Exception as e:
                results.append(Result.failure(str(e)))
                if stop_on_error:
                    return Result.partial(
                        data=current_data,
                        error=f"Exception in agent {agent.name}: {str(e)}",
                        metadata={"failed_at": agent.name, "results": results},
                    )

        # Transform output if needed
        if self._output_transformer:
            try:
                current_data = self._output_transformer(current_data)
            except Exception as e:
                return Result.failure(f"Output transformation failed: {str(e)}")

        return Result.success(current_data, metadata={"results": results})

    def get_agents(self) -> list[BaseAgent]:
        """Get all agents in the chain."""
        return self.agents.copy()

    def size(self) -> int:
        """Get the number of agents in the chain."""
        return len(self.agents)

    def __repr__(self) -> str:
        """String representation of the chain."""
        agent_names = " -> ".join(agent.name for agent in self.agents)
        return f"AgentChain({agent_names})"


class ChainBuilder:
    """Fluent builder for creating agent chains."""

    def __init__(self) -> None:
        """Initialize the builder."""
        self._chain = AgentChain()

    def add(self, agent: BaseAgent) -> "ChainBuilder":
        """
        Add an agent to the chain.

        Args:
            agent: Agent to add

        Returns:
            Self for fluent API
        """
        self._chain.add_agent(agent)
        return self

    def add_multiple(self, agents: list[BaseAgent]) -> "ChainBuilder":
        """
        Add multiple agents to the chain.

        Args:
            agents: Agents to add

        Returns:
            Self for fluent API
        """
        for agent in agents:
            self._chain.add_agent(agent)
        return self

    def with_input_transformer(self, transformer: Callable[[Any], Any]) -> "ChainBuilder":
        """
        Set input transformer.

        Args:
            transformer: Function to transform input

        Returns:
            Self for fluent API
        """
        self._chain.set_input_transformer(transformer)
        return self

    def with_output_transformer(self, transformer: Callable[[Any], Any]) -> "ChainBuilder":
        """
        Set output transformer.

        Args:
            transformer: Function to transform output

        Returns:
            Self for fluent API
        """
        self._chain.set_output_transformer(transformer)
        return self

    def build(self) -> AgentChain:
        """
        Build and return the chain.

        Returns:
            AgentChain instance
        """
        if not self._chain.agents:
            raise ValueError("Chain must contain at least one agent")
        return self._chain
