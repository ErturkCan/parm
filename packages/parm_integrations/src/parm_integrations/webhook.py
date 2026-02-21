"""Webhook management for incoming events."""

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Callable, Optional

from parm_core import Result


@dataclass
class WebhookEndpoint:
    """Configuration for a webhook endpoint."""
    id: str
    url: str
    event_type: str
    secret: Optional[str] = None
    active: bool = True
    custom_headers: dict[str, str] = None

    def __post_init__(self) -> None:
        if self.custom_headers is None:
            self.custom_headers = {}


class WebhookManager:
    """
    Register webhook endpoints, validate signatures, route webhooks.
    """

    def __init__(self) -> None:
        """Initialize the webhook manager."""
        self._endpoints: dict[str, WebhookEndpoint] = {}
        self._handlers: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
        self._event_log: list[dict[str, Any]] = []

    def register_endpoint(
        self,
        endpoint_id: str,
        url: str,
        event_type: str,
        secret: Optional[str] = None,
    ) -> Result[WebhookEndpoint]:
        """
        Register a webhook endpoint.

        Args:
            endpoint_id: Unique endpoint ID
            url: Webhook URL
            event_type: Event type to listen for
            secret: Optional secret for signature verification

        Returns:
            Result with endpoint configuration
        """
        try:
            endpoint = WebhookEndpoint(
                id=endpoint_id,
                url=url,
                event_type=event_type,
                secret=secret,
            )
            self._endpoints[endpoint_id] = endpoint
            return Result.success(endpoint)
        except Exception as e:
            return Result.failure(str(e))

    def unregister_endpoint(self, endpoint_id: str) -> bool:
        """
        Unregister a webhook endpoint.

        Args:
            endpoint_id: Endpoint ID

        Returns:
            True if unregistered, False if not found
        """
        return self._endpoints.pop(endpoint_id, None) is not None

    def activate_endpoint(self, endpoint_id: str) -> bool:
        """Activate a webhook endpoint."""
        if endpoint_id in self._endpoints:
            self._endpoints[endpoint_id].active = True
            return True
        return False

    def deactivate_endpoint(self, endpoint_id: str) -> bool:
        """Deactivate a webhook endpoint."""
        if endpoint_id in self._endpoints:
            self._endpoints[endpoint_id].active = False
            return True
        return False

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[dict[str, Any]], None],
    ) -> None:
        """
        Register a handler for an event type.

        Args:
            event_type: Event type
            handler: Handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unregister_handler(
        self,
        event_type: str,
        handler: Callable[[dict[str, Any]], None],
    ) -> bool:
        """
        Unregister a handler.

        Args:
            event_type: Event type
            handler: Handler function

        Returns:
            True if unregistered, False if not found
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                return True
            except ValueError:
                pass
        return False

    def handle_webhook(
        self,
        event_type: str,
        payload: dict[str, Any],
        signature: Optional[str] = None,
        endpoint_id: Optional[str] = None,
    ) -> Result[None]:
        """
        Handle an incoming webhook.

        Args:
            event_type: Event type
            payload: Webhook payload
            signature: Optional signature for verification
            endpoint_id: Optional endpoint ID that received this

        Returns:
            Result indicating success or failure
        """
        try:
            # Verify signature if endpoint requires it
            if endpoint_id:
                endpoint = self._endpoints.get(endpoint_id)
                if endpoint and endpoint.secret and signature:
                    if not self._verify_signature(signature, payload, endpoint.secret):
                        return Result.failure("Signature verification failed")

            # Log the event
            self._event_log.append({
                "event_type": event_type,
                "payload": payload,
                "endpoint_id": endpoint_id,
            })

            # Route to handlers
            handlers = self._handlers.get(event_type, [])
            for handler in handlers:
                try:
                    handler(payload)
                except Exception as e:
                    # Log handler error but don't stop other handlers
                    pass

            return Result.success(None)
        except Exception as e:
            return Result.failure(str(e))

    def get_endpoint(self, endpoint_id: str) -> Optional[WebhookEndpoint]:
        """Get an endpoint by ID."""
        return self._endpoints.get(endpoint_id)

    def get_endpoints_for_event(self, event_type: str) -> list[WebhookEndpoint]:
        """Get all active endpoints for an event type."""
        return [
            ep for ep in self._endpoints.values()
            if ep.event_type == event_type and ep.active
        ]

    def list_endpoints(self) -> list[WebhookEndpoint]:
        """List all registered endpoints."""
        return list(self._endpoints.values())

    def get_event_log(self) -> list[dict[str, Any]]:
        """Get the event log."""
        return self._event_log.copy()

    def clear_event_log(self) -> None:
        """Clear the event log."""
        self._event_log.clear()

    @staticmethod
    def _verify_signature(signature: str, payload: dict[str, Any], secret: str) -> bool:
        """
        Verify a webhook signature.

        Args:
            signature: Received signature
            payload: Webhook payload
            secret: Secret key

        Returns:
            True if signature is valid
        """
        try:
            import json
            payload_str = json.dumps(payload, sort_keys=True)
            expected_signature = hmac.new(
                secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False
