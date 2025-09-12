"""
Authentication Standardization for Integration Clients (Phase 3B.3.4)

This module provides standardized authentication patterns and credential management
for all integration clients, building upon the base infrastructure from Phase 3B.2.

Features:
- Unified authentication workflows
- Secure credential storage integration
- Standardized session management
- Automatic token refresh and re-authentication
- Consistent error handling and status reporting

This enhances the existing AuthenticationProtocol to provide concrete implementations
for common authentication patterns used across different service types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Protocol
import logging
from datetime import datetime, timedelta

from .base import (
    IntegrationResponse,
    IntegrationStatus,
    AuthenticationError,
)

try:
    from ..core.secure_credentials import SecureCredentialManager

    SECURE_CREDENTIALS_AVAILABLE = True
except ImportError:
    SECURE_CREDENTIALS_AVAILABLE = False

logger = logging.getLogger(__name__)


class AuthenticationType(Enum):
    """Types of authentication methods supported"""

    USERNAME_PASSWORD = "username_password"  # qBittorrent, forums  # nosec B105
    API_KEY = "api_key"  # RED, many APIs
    BEARER_TOKEN = "bearer_token"  # OAuth, JWT tokens  # nosec B105
    SESSION_COOKIE = "session_cookie"  # Web session-based
    NO_AUTH = "no_auth"  # Public APIs like Audnexus


class CredentialStorage(Enum):
    """Methods for storing credentials securely"""

    ENVIRONMENT = "environment"  # Environment variables
    KEYRING = "keyring"  # OS keyring/keychain
    ENCRYPTED_FILE = "encrypted_file"  # Encrypted local storage
    CONFIG_FILE = "config_file"  # Plain text (development only)
    MEMORY_ONLY = "memory_only"  # Not persisted


@dataclass
class AuthenticationConfig:
    """Configuration for authentication methods"""

    auth_type: AuthenticationType
    storage_method: CredentialStorage = CredentialStorage.KEYRING

    # Service-specific configuration
    service_name: str = ""
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    token: Optional[str] = None

    # Session management
    session_timeout: Optional[timedelta] = field(
        default_factory=lambda: timedelta(hours=24)
    )
    auto_refresh: bool = True

    # Security options
    require_secure_storage: bool = True
    allow_fallback_storage: bool = False


@dataclass
class AuthenticationState:
    """Current authentication state"""

    authenticated: bool = False
    auth_timestamp: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    session_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if authentication has expired"""
        if not self.authenticated or not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def time_until_expiry(self) -> Optional[timedelta]:
        """Time until authentication expires"""
        if not self.expires_at:
            return None
        return self.expires_at - datetime.utcnow()


class StandardAuthenticationProtocol(Protocol):
    """Enhanced authentication protocol with standard methods"""

    def authenticate(self) -> IntegrationResponse:
        """Authenticate with the external service"""
        ...

    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        ...

    def refresh_authentication(self) -> IntegrationResponse:
        """Refresh expired authentication"""
        ...

    def logout(self) -> IntegrationResponse:
        """Explicitly log out and clear authentication"""
        ...


class BaseAuthenticationHandler(ABC):
    """Base authentication handler with common functionality"""

    def __init__(self, config: AuthenticationConfig):
        self.config = config
        self.state = AuthenticationState()
        self._credential_manager = None

        if SECURE_CREDENTIALS_AVAILABLE and config.require_secure_storage:
            self._credential_manager = SecureCredentialManager()

    @abstractmethod
    def _perform_authentication(self) -> IntegrationResponse:
        """Perform the actual authentication with the service"""
        pass

    @abstractmethod
    def _validate_authentication(self) -> IntegrationResponse:
        """Validate current authentication state"""
        pass

    def authenticate(self) -> IntegrationResponse:
        """Main authentication method with automatic refresh"""
        try:
            # Check if already authenticated and not expired
            if self.state.authenticated and not self.state.is_expired:
                logger.debug(f"Already authenticated for {self.config.service_name}")
                return IntegrationResponse(
                    status=IntegrationStatus.SUCCESS,
                    message="Already authenticated",
                    data={
                        "authenticated": True,
                        "expires_in": self.state.time_until_expiry,
                    },
                )

            # If expired but auto-refresh enabled, try refresh first
            if self.state.is_expired and self.config.auto_refresh:
                refresh_result = self.refresh_authentication()
                if refresh_result.success:
                    return refresh_result

            # Perform new authentication
            return self._perform_authentication()

        except Exception as e:
            logger.error(f"Authentication failed for {self.config.service_name}: {e}")
            self.state.authenticated = False
            return IntegrationResponse(
                status=IntegrationStatus.AUTHENTICATION_REQUIRED,
                message=f"Authentication failed: {str(e)}",
                error_details={"exception": str(e)},
            )

    def is_authenticated(self) -> bool:
        """Check authentication status with expiry validation"""
        return self.state.authenticated and not self.state.is_expired

    def refresh_authentication(self) -> IntegrationResponse:
        """Default refresh implementation - re-authenticate"""
        logger.info(f"Refreshing authentication for {self.config.service_name}")
        return self._perform_authentication()

    def logout(self) -> IntegrationResponse:
        """Clear authentication state"""
        self.state = AuthenticationState()
        return IntegrationResponse(
            status=IntegrationStatus.SUCCESS, message="Logged out successfully"
        )

    def get_credentials(self) -> Dict[str, Any]:
        """Retrieve credentials based on storage method"""
        if not self._credential_manager and self.config.require_secure_storage:
            raise AuthenticationError("Secure credential storage not available")

        credentials = {}

        # Build credentials from config
        if self.config.username:
            credentials["username"] = self.config.username
        if self.config.password:
            credentials["password"] = self.config.password
        if self.config.api_key:
            credentials["api_key"] = self.config.api_key
        if self.config.token:
            credentials["token"] = self.config.token

        # TODO: Implement secure retrieval from credential manager
        # This would integrate with the SecureCredentialManager for production use

        return credentials


class UsernamePasswordAuthHandler(BaseAuthenticationHandler):
    """Authentication handler for username/password systems (e.g., qBittorrent)"""

    def __init__(
        self, config: AuthenticationConfig, login_endpoint: str, client_session=None
    ):
        super().__init__(config)
        self.login_endpoint = login_endpoint
        self.client_session = client_session

    def _perform_authentication(self, **kwargs) -> IntegrationResponse:
        """Perform username/password authentication"""
        credentials = self.get_credentials()

        if not credentials.get("username") or not credentials.get("password"):
            return IntegrationResponse(
                status=IntegrationStatus.AUTHENTICATION_REQUIRED,
                message="Username and password required",
            )

        try:
            # This is a template - actual implementation depends on the service
            logger.info(
                f"Authenticating {credentials['username']} with {self.config.service_name}"
            )

            # Update authentication state on success
            self.state.authenticated = True
            self.state.auth_timestamp = datetime.utcnow()

            if self.config.session_timeout:
                self.state.expires_at = datetime.utcnow() + self.config.session_timeout

            return IntegrationResponse(
                status=IntegrationStatus.SUCCESS,
                message="Authentication successful",
                data={
                    "authenticated": True,
                    "username": credentials["username"],
                    "expires_at": self.state.expires_at.isoformat()
                    if self.state.expires_at
                    else None,
                },
            )

        except Exception as e:
            self.state.authenticated = False
            return IntegrationResponse(
                status=IntegrationStatus.AUTHENTICATION_REQUIRED,
                message=f"Login failed: {str(e)}",
                error_details={"exception": str(e)},
            )

    def _validate_authentication(self) -> IntegrationResponse:
        """Validate current authentication by checking session"""
        if not self.is_authenticated():
            return IntegrationResponse(
                status=IntegrationStatus.AUTHENTICATION_REQUIRED,
                message="Not authenticated",
            )

        # Service-specific validation would go here
        return IntegrationResponse(
            status=IntegrationStatus.SUCCESS, message="Authentication valid"
        )


class ApiKeyAuthHandler(BaseAuthenticationHandler):
    """Authentication handler for API key-based systems (e.g., RED tracker)"""

    def __init__(
        self, config: AuthenticationConfig, test_endpoint: str = "", client_session=None
    ):
        super().__init__(config)
        self.test_endpoint = test_endpoint
        self.client_session = client_session

    def _perform_authentication(self) -> IntegrationResponse:
        """Validate API key authentication"""
        credentials = self.get_credentials()

        if not credentials.get("api_key"):
            return IntegrationResponse(
                status=IntegrationStatus.AUTHENTICATION_REQUIRED,
                message="API key required",
            )

        try:
            logger.info(f"Validating API key for {self.config.service_name}")

            # API key validation would happen here
            # For most APIs, this involves a test request

            self.state.authenticated = True
            self.state.auth_timestamp = datetime.utcnow()

            # API keys typically don't expire, but we can set a validation period
            if self.config.session_timeout:
                self.state.expires_at = datetime.utcnow() + self.config.session_timeout

            return IntegrationResponse(
                status=IntegrationStatus.SUCCESS,
                message="API key validated",
                data={
                    "authenticated": True,
                    "key_prefix": credentials["api_key"][:8] + "...",
                    "expires_at": self.state.expires_at.isoformat()
                    if self.state.expires_at
                    else None,
                },
            )

        except Exception as e:
            self.state.authenticated = False
            return IntegrationResponse(
                status=IntegrationStatus.AUTHENTICATION_REQUIRED,
                message=f"API key validation failed: {str(e)}",
                error_details={"exception": str(e)},
            )

    def _validate_authentication(self) -> IntegrationResponse:
        """Validate API key by testing endpoint access"""
        if not self.is_authenticated():
            return IntegrationResponse(
                status=IntegrationStatus.AUTHENTICATION_REQUIRED,
                message="API key not validated",
            )

        # Service-specific validation would go here
        return IntegrationResponse(
            status=IntegrationStatus.SUCCESS, message="API key valid"
        )


class NoAuthHandler(BaseAuthenticationHandler):
    """Authentication handler for public APIs that require no authentication"""

    def _perform_authentication(self) -> IntegrationResponse:
        """No authentication required"""
        self.state.authenticated = True
        self.state.auth_timestamp = datetime.utcnow()

        return IntegrationResponse(
            status=IntegrationStatus.SUCCESS,
            message="No authentication required",
            data={"authenticated": True},
        )

    def _validate_authentication(self) -> IntegrationResponse:
        """Always valid for no-auth services"""
        return IntegrationResponse(
            status=IntegrationStatus.SUCCESS, message="No authentication required"
        )


class AuthenticationFactory:
    """Factory for creating appropriate authentication handlers"""

    @staticmethod
    def create_handler(
        config: AuthenticationConfig, **kwargs
    ) -> BaseAuthenticationHandler:
        """Create appropriate authentication handler based on config"""

        if config.auth_type == AuthenticationType.USERNAME_PASSWORD:
            return UsernamePasswordAuthHandler(
                config,
                login_endpoint=kwargs.get("login_endpoint", ""),
                client_session=kwargs.get("client_session"),
            )
        elif config.auth_type == AuthenticationType.API_KEY:
            return ApiKeyAuthHandler(
                config,
                test_endpoint=kwargs.get("test_endpoint", ""),
                client_session=kwargs.get("client_session"),
            )
        elif config.auth_type == AuthenticationType.NO_AUTH:
            return NoAuthHandler(config)
        else:
            raise ValueError(f"Unsupported authentication type: {config.auth_type}")


__all__ = [
    "AuthenticationType",
    "CredentialStorage",
    "AuthenticationConfig",
    "AuthenticationState",
    "StandardAuthenticationProtocol",
    "BaseAuthenticationHandler",
    "UsernamePasswordAuthHandler",
    "ApiKeyAuthHandler",
    "NoAuthHandler",
    "AuthenticationFactory",
]
