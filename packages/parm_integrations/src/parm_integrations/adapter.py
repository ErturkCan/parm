"""Base integration adapter for external services."""

from abc import ABC, abstractmethod
from enum import Enum
from time import time, sleep
from typing import Any, Optional

from parm_core import Result


class CircuitBreakerState(str, Enum):
    """States of the circuit breaker."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Simple circuit breaker pattern implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening
            timeout_seconds: Time to wait before half-opening
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitBreakerState.CLOSED

    def call(self, func: Any, *args: Any, **kwargs: Any) -> Result[Any]:
        """
        Call a function through the circuit breaker.

        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Result of function call or circuit breaker error
        """
        if self.state == CircuitBreakerState.OPEN:
            if self._should_half_open():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                return Result.failure("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
            raise e

    def _should_half_open(self) -> bool:
        """Check if circuit should transition to half-open."""
        if self.last_failure_time is None:
            return False
        return time() - self.last_failure_time >= self.timeout_seconds

    def reset(self) -> None:
        """Reset the circuit breaker."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED


class IntegrationAdapter(ABC):
    """
    Abstract base class for integration adapters.
    Provides standard interface for external services.
    """

    def __init__(
        self,
        name: str,
        base_url: str = "",
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the adapter.

        Args:
            name: Adapter name
            base_url: Base URL for service
            timeout_seconds: Request timeout
            max_retries: Maximum retry attempts
        """
        self.name = name
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._connected = False
        self._circuit_breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=60)

    def connect(self) -> Result[None]:
        """
        Connect to the external service.

        Returns:
            Result indicating success or failure
        """
        try:
            result = self._do_connect()
            if result.is_success():
                self._connected = True
            return result
        except Exception as e:
            return Result.failure(f"Connection failed: {str(e)}")

    def disconnect(self) -> Result[None]:
        """
        Disconnect from the external service.

        Returns:
            Result indicating success or failure
        """
        try:
            result = self._do_disconnect()
            self._connected = False
            return result
        except Exception as e:
            return Result.failure(f"Disconnection failed: {str(e)}")

    def health_check(self) -> Result[dict[str, Any]]:
        """
        Check health of the external service.

        Returns:
            Result with health status
        """
        try:
            if not self._connected:
                return Result.failure("Not connected")

            return self._do_health_check()
        except Exception as e:
            return Result.failure(f"Health check failed: {str(e)}")

    def execute(self, action: str, **kwargs: Any) -> Result[Any]:
        """
        Execute an action on the external service.

        Args:
            action: Action to perform
            **kwargs: Action parameters

        Returns:
            Result of action execution
        """
        if not self._connected:
            return Result.failure("Not connected to service")

        def do_execute() -> Result[Any]:
            return self._do_execute(action, **kwargs)

        # Use circuit breaker
        try:
            return self._circuit_breaker.call(do_execute)
        except Exception as e:
            return Result.failure(f"Execution failed: {str(e)}")

    def execute_with_retry(self, action: str, **kwargs: Any) -> Result[Any]:
        """
        Execute an action with automatic retries.

        Args:
            action: Action to perform
            **kwargs: Action parameters

        Returns:
            Result of action execution
        """
        last_error = None

        for attempt in range(self.max_retries):
            result = self.execute(action, **kwargs)
            if result.is_success():
                return result

            last_error = result.error
            if attempt < self.max_retries - 1:
                # Exponential backoff
                sleep_time = 2 ** attempt
                sleep(sleep_time)

        return Result.failure(f"Failed after {self.max_retries} retries: {last_error}")

    def is_connected(self) -> bool:
        """Check if adapter is connected."""
        return self._connected

    @abstractmethod
    def _do_connect(self) -> Result[None]:
        """Implement connection logic."""
        pass

    @abstractmethod
    def _do_disconnect(self) -> Result[None]:
        """Implement disconnection logic."""
        pass

    @abstractmethod
    def _do_health_check(self) -> Result[dict[str, Any]]:
        """Implement health check logic."""
        pass

    @abstractmethod
    def _do_execute(self, action: str, **kwargs: Any) -> Result[Any]:
        """Implement action execution logic."""
        pass
