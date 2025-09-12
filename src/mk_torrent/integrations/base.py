"""
Base integration infrastructure for external services

This module provides common patterns for all integration modules including:
- Standardized error handling and exception hierarchy
- Common configuration management
- Retry logic and timeout strategies
- Connection health checks
- Response validation patterns

Part of Phase 3B.2: Upload Workflow Unification
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol
from urllib.parse import urlparse

import requests
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


class IntegrationError(Exception):
    """Base exception for all integration errors"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ConnectionError(IntegrationError):
    """Connection-related errors (network, timeout, etc.)"""

    pass


class AuthenticationError(IntegrationError):
    """Authentication/authorization errors"""

    pass


class ValidationError(IntegrationError):
    """Request/response validation errors"""

    pass


class RateLimitError(IntegrationError):
    """Rate limiting errors"""

    def __init__(self, message: str, retry_after: int | None = None, **kwargs: Any):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class ServiceUnavailableError(IntegrationError):
    """Service temporarily unavailable"""

    pass


class IntegrationStatus(Enum):
    """Standard status codes for integration operations"""

    SUCCESS = "success"
    FAILED = "failed"
    RETRY_NEEDED = "retry_needed"
    RATE_LIMITED = "rate_limited"
    AUTHENTICATION_REQUIRED = "auth_required"
    VALIDATION_FAILED = "validation_failed"
    SERVICE_UNAVAILABLE = "service_unavailable"


@dataclass
class IntegrationResponse:
    """Standardized response format for all integration operations"""

    status: IntegrationStatus
    data: dict[str, Any] | None = None
    message: str | None = None
    error_details: dict[str, Any] | None = None
    retry_after: int | None = None
    execution_time: float = 0.0

    @property
    def success(self) -> bool:
        """Check if operation was successful"""
        return self.status == IntegrationStatus.SUCCESS

    @property
    def should_retry(self) -> bool:
        """Check if operation should be retried"""
        return self.status in [
            IntegrationStatus.RETRY_NEEDED,
            IntegrationStatus.RATE_LIMITED,
        ]


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    retry_on_status: list[IntegrationStatus] = field(
        default_factory=lambda: [
            IntegrationStatus.RETRY_NEEDED,
            IntegrationStatus.RATE_LIMITED,
            IntegrationStatus.SERVICE_UNAVAILABLE,
        ]
    )


@dataclass
class IntegrationConfig:
    """Base configuration for integration clients"""

    base_url: str
    timeout: float = 30.0
    verify_ssl: bool = True
    max_retries: int = 3
    retry_config: RetryConfig | None = None
    user_agent: str = "mk_torrent/1.0"

    def __post_init__(self):
        if self.retry_config is None:
            self.retry_config = RetryConfig(max_attempts=self.max_retries)

        # Validate URL
        parsed = urlparse(self.base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid base_url: {self.base_url}")


class HealthCheckProtocol(Protocol):
    """Protocol for health check implementations"""

    def health_check(self) -> IntegrationResponse:
        """Perform health check on the integration"""
        ...


class AuthenticationProtocol(Protocol):
    """Protocol for authentication implementations"""

    def authenticate(self) -> IntegrationResponse:
        """Authenticate with the external service"""
        ...

    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        ...


class BaseIntegrationClient(ABC):
    """Base class for all external service integration clients"""

    def __init__(self, config: IntegrationConfig, **kwargs: Any):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": config.user_agent,
                "Accept": "application/json",
            }
        )
        self._authenticated = False
        self._last_request_time = 0.0

        # Configure session defaults
        self.session.verify = config.verify_ssl

        # Allow subclasses to customize session
        self._configure_session(**kwargs)

    def _configure_session(self, **kwargs: Any) -> None:
        """Override in subclasses to customize session configuration"""
        pass

    @abstractmethod
    def health_check(self) -> IntegrationResponse:
        """Perform comprehensive health check"""
        pass

    def _make_request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> IntegrationResponse:
        """Make HTTP request with standardized error handling and retry logic"""
        url = self._build_url(endpoint)
        start_time = time.time()

        # Apply retry logic
        retry_config = self.config.retry_config
        if retry_config is None:
            retry_config = RetryConfig()

        for attempt in range(retry_config.max_attempts):
            try:
                # Rate limiting check
                self._handle_rate_limiting()

                # Make the request
                response = self.session.request(
                    method=method, url=url, timeout=self.config.timeout, **kwargs
                )

                execution_time = time.time() - start_time

                # Handle response
                return self._handle_response(response, execution_time)

            except requests.exceptions.ConnectionError as e:
                if attempt == retry_config.max_attempts - 1:
                    return IntegrationResponse(
                        status=IntegrationStatus.FAILED,
                        message=f"Connection failed: {e}",
                        error_details={"exception": str(e)},
                        execution_time=time.time() - start_time,
                    )
                self._handle_retry_delay(attempt)

            except requests.exceptions.Timeout as e:
                if attempt == retry_config.max_attempts - 1:
                    return IntegrationResponse(
                        status=IntegrationStatus.FAILED,
                        message=f"Request timeout: {e}",
                        error_details={"exception": str(e)},
                        execution_time=time.time() - start_time,
                    )
                self._handle_retry_delay(attempt)

            except Exception as e:
                return IntegrationResponse(
                    status=IntegrationStatus.FAILED,
                    message=f"Unexpected error: {e}",
                    error_details={"exception": str(e)},
                    execution_time=time.time() - start_time,
                )

        # Should not reach here due to loop logic, but safety fallback
        return IntegrationResponse(
            status=IntegrationStatus.FAILED,
            message="Max retries exceeded",
            execution_time=time.time() - start_time,
        )

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint"""
        base = self.config.base_url.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return f"{base}/{endpoint}"

    def _handle_response(
        self, response: requests.Response, execution_time: float
    ) -> IntegrationResponse:
        """Handle HTTP response and return standardized response"""

        # Handle different status codes
        if response.status_code == 200:
            try:
                data = (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else {"raw": response.text}
                )
                return IntegrationResponse(
                    status=IntegrationStatus.SUCCESS,
                    data=data,
                    execution_time=execution_time,
                )
            except ValueError:
                # JSON parsing failed, return text
                return IntegrationResponse(
                    status=IntegrationStatus.SUCCESS,
                    data={"raw": response.text},
                    execution_time=execution_time,
                )

        elif response.status_code == 401:
            return IntegrationResponse(
                status=IntegrationStatus.AUTHENTICATION_REQUIRED,
                message="Authentication required",
                error_details={
                    "status_code": response.status_code,
                    "response": response.text,
                },
                execution_time=execution_time,
            )

        elif response.status_code == 403:
            return IntegrationResponse(
                status=IntegrationStatus.AUTHENTICATION_REQUIRED,
                message="Access forbidden",
                error_details={
                    "status_code": response.status_code,
                    "response": response.text,
                },
                execution_time=execution_time,
            )

        elif response.status_code == 429:
            # Rate limiting
            retry_after = None
            if "Retry-After" in response.headers:
                try:
                    retry_after = int(response.headers["Retry-After"])
                except ValueError:
                    pass

            return IntegrationResponse(
                status=IntegrationStatus.RATE_LIMITED,
                message="Rate limited",
                retry_after=retry_after,
                error_details={
                    "status_code": response.status_code,
                    "response": response.text,
                },
                execution_time=execution_time,
            )

        elif response.status_code >= 500:
            return IntegrationResponse(
                status=IntegrationStatus.SERVICE_UNAVAILABLE,
                message=f"Server error: {response.status_code}",
                error_details={
                    "status_code": response.status_code,
                    "response": response.text,
                },
                execution_time=execution_time,
            )

        else:
            return IntegrationResponse(
                status=IntegrationStatus.FAILED,
                message=f"HTTP {response.status_code}",
                error_details={
                    "status_code": response.status_code,
                    "response": response.text,
                },
                execution_time=execution_time,
            )

    def _handle_rate_limiting(self):
        """Handle rate limiting logic"""
        # Basic rate limiting - can be overridden by subclasses
        current_time = time.time()
        min_interval = 0.1  # 100ms between requests by default

        if self._last_request_time > 0:
            elapsed = current_time - self._last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

        self._last_request_time = time.time()

    def _handle_retry_delay(self, attempt: int):
        """Handle delay between retry attempts"""
        retry_config = self.config.retry_config
        if retry_config is None:
            retry_config = RetryConfig()

        if not retry_config.exponential_backoff:
            delay = retry_config.base_delay
        else:
            delay = min(retry_config.base_delay * (2**attempt), retry_config.max_delay)

        logger.info(f"Retrying in {delay:.1f}s (attempt {attempt + 1})")
        time.sleep(delay)

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        if hasattr(self.session, "close"):
            self.session.close()


__all__ = [
    # Exceptions
    "IntegrationError",
    "ConnectionError",
    "AuthenticationError",
    "ValidationError",
    "RateLimitError",
    "ServiceUnavailableError",
    # Status and Response
    "IntegrationStatus",
    "IntegrationResponse",
    # Configuration
    "RetryConfig",
    "IntegrationConfig",
    # Protocols
    "HealthCheckProtocol",
    "AuthenticationProtocol",
    # Base Classes
    "BaseIntegrationClient",
]
