"""
Base client for YouTrack REST API.
"""

import logging
import time
from typing import Any, Dict, Optional
import json
import random

import httpx
from pydantic import BaseModel, ConfigDict

from youtrack_mcp.config import config

logger = logging.getLogger(__name__)


class YouTrackAPIError(Exception):
    """Base exception for YouTrack API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[httpx.Response] = None,
    ):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class RateLimitError(YouTrackAPIError):
    """Exception for API rate limiting errors."""

    pass


class ResourceNotFoundError(YouTrackAPIError):
    """Exception for 404 Not Found errors."""

    pass


class AuthenticationError(YouTrackAPIError):
    """Exception for authentication errors."""

    pass


class PermissionDeniedError(YouTrackAPIError):
    """Exception for permission-related errors."""

    pass


class ValidationError(YouTrackAPIError):
    """Exception for validation errors in API requests."""

    pass


class ServerError(YouTrackAPIError):
    """Exception for server-side errors."""

    pass


class YouTrackModel(BaseModel):
    """Base model for YouTrack API resources."""

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields in the model
        populate_by_name=True,  # Allow population by field name
    )

    id: str


class YouTrackClient:
    """Base client for YouTrack REST API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize YouTrack API client.

        Args:
            base_url: YouTrack instance URL, defaults to config.get_base_url()
            api_token: API token for authentication, defaults to config.YOUTRACK_API_TOKEN
            verify_ssl: Whether to verify SSL certificates, defaults to config.VERIFY_SSL
            max_retries: Maximum number of retries for transient errors
            retry_delay: Initial delay between retries in seconds (increases exponentially)
        """
        self.base_url = base_url or config.get_base_url()
        self._api_token = api_token  # Store provided token or None
        self._token_loaded = api_token is not None  # Track if token was provided
        self.verify_ssl = (
            verify_ssl if verify_ssl is not None else config.VERIFY_SSL
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize httpx client - will be created lazily
        self.client: Optional[httpx.AsyncClient] = None

    @property
    def api_token(self) -> str:
        """Get API token with lazy loading for security."""
        if not self._token_loaded:
            self._api_token = config.get_api_token()
            self._token_loaded = True
        if self._api_token is None:
            raise ValueError("API token is required")
        return self._api_token

        # Initialize httpx client - will be set in async context
        self.client = None

        logger.debug(
            f"YouTrack client initialized for {'YouTrack Cloud' if config.is_cloud_instance() else self.base_url}"
        )

    def _get_httpx_client(self) -> httpx.AsyncClient:
        """Get or create httpx async client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                verify=self.verify_ssl,
                timeout=30.0,  # Default timeout
            )
        return self.client

    def _get_api_url(self, endpoint: str) -> str:
        """
        Construct full API URL from endpoint.

        Args:
            endpoint: API endpoint (without leading slash)

        Returns:
            Full API URL
        """
        # Remove trailing slash from base_url for consistent URL construction
        base = self.base_url.rstrip('/')
        
        if base.endswith("/api"):
            return f"{base}/{endpoint}"
        else:
            return f"{base}/api/{endpoint}"

    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Handle API response, raising appropriate exceptions for errors.

        Args:
            response: Response from API

        Returns:
            Parsed JSON response

        Raises:
            Various exceptions based on response status
        """
        status_code = response.status_code

        # Handle success
        if 200 <= status_code < 300:
            # Some endpoints return empty responses
            if not response.content or response.content.strip() == b"":
                return {}

            try:
                return response.json()
            except json.JSONDecodeError:
                # Handle non-JSON responses
                logger.warning(
                    f"Non-JSON response received from API: {response.content[:100]}"
                )
                return {
                    "raw_content": response.content.decode(
                        "utf-8", errors="replace"
                    )
                }

        # Handle error responses
        error_message = f"API request failed with status {status_code}"

        # Try to extract error details from response
        try:
            error_data = response.json()
            if isinstance(error_data, dict) and "error" in error_data:
                error_message = f"{error_message}: {error_data['error']}"
        except (json.JSONDecodeError, KeyError):
            if response.content:
                error_message = f"{error_message}: {response.content.decode('utf-8', errors='replace')}"

        # Raise appropriate exception based on status code
        if status_code == 400:
            raise ValidationError(error_message, status_code, response)
        elif status_code == 401:
            raise AuthenticationError(error_message, status_code, response)
        elif status_code == 403:
            raise PermissionDeniedError(error_message, status_code, response)
        elif status_code == 404:
            raise ResourceNotFoundError(error_message, status_code, response)
        elif status_code == 429:
            raise RateLimitError(error_message, status_code, response)
        elif 500 <= status_code < 600:
            raise ServerError(error_message, status_code, response)
        else:
            raise YouTrackAPIError(error_message, status_code, response)

    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Make API request with retry logic for transient errors.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            **kwargs: Additional arguments to pass to httpx

        Returns:
            Parsed JSON response

        Raises:
            YouTrackAPIError: For non-transient errors or if all retries fail
        """
        import asyncio

        url = self._get_api_url(endpoint)
        retries = 0
        delay = self.retry_delay
        last_error = None

        # For debugging purposes, log essential request details
        if "json" in kwargs:
            logger.debug(
                f"{method} {url} with JSON: {json.dumps(kwargs['json'])}"
            )
        elif "data" in kwargs:
            logger.debug(f"{method} {url} with data: {kwargs['data']}")
        else:
            logger.debug(f"{method} {url}")

        while retries <= self.max_retries:
            try:
                client = self._get_httpx_client()
                response = await client.request(method, url, **kwargs)
                return self._handle_response(response)
            except (ServerError, RateLimitError) as e:
                # These are potentially transient, so we retry
                last_error = e
                retries += 1

                if retries > self.max_retries:
                    logger.error(f"Maximum retries reached for {method} {url}")
                    break

                # Calculate backoff delay (exponential with jitter)
                backoff = delay * (2**retries) * (0.5 + 0.5 * random.random())
                logger.warning(
                    f"Transient error, retrying in {backoff:.2f}s: {str(e)}"
                )
                await asyncio.sleep(backoff)
            except YouTrackAPIError as e:
                # Non-transient errors
                logger.error(f"API error for {method} {url}: {str(e)}")
                if hasattr(e, "response") and e.response is not None:
                    try:
                        error_content = e.response.content.decode(
                            "utf-8", errors="replace"
                        )
                        logger.error(f"Response content: {error_content}")
                    except Exception:
                        pass
                raise
            except Exception as e:
                # Unexpected errors
                logger.exception(
                    f"Unexpected error for {method} {url}: {str(e)}"
                )
                raise YouTrackAPIError(f"Unexpected error: {str(e)}")

        # If we got here, we've exceeded retries
        if last_error:
            raise last_error

        # This should never happen, but just in case
        raise YouTrackAPIError(f"Maximum retries exceeded for {method} {url}")

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Make GET request to API.

        Args:
            endpoint: API endpoint
            params: Query parameters
            **kwargs: Additional arguments to pass to httpx

        Returns:
            Parsed JSON response
        """
        return await self._make_request("GET", endpoint, params=params, **kwargs)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make POST request to API.

        Args:
            endpoint: API endpoint
            data: Form data
            json_data: JSON data
            **kwargs: Additional arguments to pass to httpx

        Returns:
            Parsed JSON response
        """
        # If data is provided but json_data is not, use data as json
        if data is not None and json_data is None:
            # Log the data being sent for debugging
            logger.debug(f"POST {endpoint} with data: {json.dumps(data)}")

            # Some endpoints expect parameters in different formats
            # YouTrack API usually expects data as JSON
            return await self._make_request("POST", endpoint, json=data, **kwargs)

        return await self._make_request(
            "POST", endpoint, data=data, json=json_data, **kwargs
        )

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make PUT request to API.

        Args:
            endpoint: API endpoint
            data: Form data
            json_data: JSON data
            **kwargs: Additional arguments to pass to httpx

        Returns:
            Parsed JSON response
        """
        return await self._make_request(
            "PUT", endpoint, data=data, json=json_data, **kwargs
        )

    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make DELETE request to API.

        Args:
            endpoint: API endpoint
            **kwargs: Additional arguments to pass to httpx

        Returns:
            Parsed JSON response
        """
        return await self._make_request("DELETE", endpoint, **kwargs)

    async def aclose(self) -> None:
        """Close the API client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def __aenter__(self):
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager, closing client."""
        await self.aclose()
