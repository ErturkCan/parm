"""PARM Integrations: External service integration layer."""

from .adapter import IntegrationAdapter, CircuitBreaker, CircuitBreakerState
from .http import HTTPAdapter
from .webhook import WebhookManager, WebhookEndpoint

__all__ = [
    "IntegrationAdapter",
    "CircuitBreaker",
    "CircuitBreakerState",
    "HTTPAdapter",
    "WebhookManager",
    "WebhookEndpoint",
]

__version__ = "0.1.0"
