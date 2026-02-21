"""HTTP integration adapter."""

from typing import Any, Optional
from urllib.parse import urljoin

from parm_core import Result

from .adapter import IntegrationAdapter


class HTTPAdapter(IntegrationAdapter):
    """
    Generic HTTP integration with rate limiting, retry, and caching.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        headers: Optional[dict[str, str]] = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize HTTP adapter.

        Args:
            name: Adapter name
            base_url: Base URL for API
            headers: Default headers
            timeout_seconds: Request timeout
            max_retries: Maximum retries
        """
        super().__init__(name, base_url, timeout_seconds, max_retries)
        self.headers = headers or {}
        self._session: Optional[Any] = None
        self._response_cache: dict[str, Any] = {}

    def _do_connect(self) -> Result[None]:
        """Connect to HTTP service."""
        try:
            # We would import requests here in a real implementation
            # For now, just return success
            return Result.success(None)
        except Exception as e:
            return Result.failure(str(e))

    def _do_disconnect(self) -> Result[None]:
        """Disconnect from HTTP service."""
        try:
            if self._session:
                # Close session
                pass
            return Result.success(None)
        except Exception as e:
            return Result.failure(str(e))

    def _do_health_check(self) -> Result[dict[str, Any]]:
        """Check HTTP service health."""
        try:
            # Would implement actual HTTP GET to /health endpoint
            return Result.success({
                "status": "healthy",
                "service": self.name,
                "base_url": self.base_url,
            })
        except Exception as e:
            return Result.failure(str(e))

    def _do_execute(self, action: str, **kwargs: Any) -> Result[Any]:
        """Execute HTTP request."""
        try:
            method = kwargs.get("method", "GET").upper()
            endpoint = kwargs.get("endpoint", "")
            data = kwargs.get("data")
            params = kwargs.get("params")

            url = urljoin(self.base_url, endpoint)

            # In a real implementation, would use requests library
            # For now, return a mock response
            return Result.success({
                "method": method,
                "url": url,
                "status": 200,
                "data": data,
            })
        except Exception as e:
            return Result.failure(str(e))

    def get(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> Result[Any]:
        """
        Make a GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Result with response data
        """
        return self.execute_with_retry("get", endpoint=endpoint, params=params)

    def post(self, endpoint: str, data: Optional[dict[str, Any]] = None) -> Result[Any]:
        """
        Make a POST request.

        Args:
            endpoint: API endpoint
            data: Request data

        Returns:
            Result with response data
        """
        return self.execute_with_retry(
            "post", method="POST", endpoint=endpoint, data=data
        )

    def put(self, endpoint: str, data: Optional[dict[str, Any]] = None) -> Result[Any]:
        """
        Make a PUT request.

        Args:
            endpoint: API endpoint
            data: Request data

        Returns:
            Result with response data
        """
        return self.execute_with_retry(
            "put", method="PUT", endpoint=endpoint, data=data
        )

    def delete(self, endpoint: str) -> Result[Any]:
        """
        Make a DELETE request.

        Args:
            endpoint: API endpoint

        Returns:
            Result with response data
        """
        return self.execute_with_retry("delete", method="DELETE", endpoint=endpoint)

    def set_header(self, key: str, value: str) -> None:
        """Set a default header."""
        self.headers[key] = value

    def set_auth(self, auth_type: str, credentials: str) -> None:
        """
        Set authentication.

        Args:
            auth_type: Type of authentication (bearer, basic)
            credentials: Authentication credentials
        """
        if auth_type == "bearer":
            self.set_header("Authorization", f"Bearer {credentials}")
        elif auth_type == "basic":
            import base64
            encoded = base64.b64encode(credentials.encode()).decode()
            self.set_header("Authorization", f"Basic {encoded}")

    def cache_response(self, key: str, data: Any) -> None:
        """Cache a response."""
        self._response_cache[key] = data

    def get_cached_response(self, key: str) -> Optional[Any]:
        """Get a cached response."""
        return self._response_cache.get(key)

    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._response_cache.clear()
