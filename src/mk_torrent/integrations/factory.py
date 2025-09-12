"""
Integration Factory for centralized integration client management.

This module provides a factory pattern for creating and managing external
service integrations. It follows the same pattern as TrackerAdapterFactory
from Phase 3A.3 to maintain architectural consistency.

The factory handles:
- Centralized registration of integration clients
- Standardized configuration management
- Type-safe client instantiation
- Discovery and lifecycle management

Classes:
    IntegrationFactory: Main factory class for integration management
"""

from typing import Dict, Type, List, Optional, Any, TypeVar
import logging

from .base import BaseIntegrationClient, IntegrationConfig
from .qbittorrent_modern import QBittorrentClient, QBittorrentConfig

logger = logging.getLogger(__name__)

# Type variable for integration clients
T_Integration = TypeVar("T_Integration", bound=BaseIntegrationClient)


class IntegrationFactory:
    """
    Factory for creating and managing integration clients.

    This factory provides centralized management of all external service
    integrations, following the established factory pattern from Phase 3A.3.

    Features:
    - Auto-discovery and registration of integration clients
    - Type-safe client instantiation with configuration
    - Listing of available integrations
    - Standardized error handling and logging

    Example:
        # Get all available integrations
        integrations = IntegrationFactory.list_available()

        # Create a qBittorrent client
        client = IntegrationFactory.create('qbittorrent', {
            'url': 'http://localhost:8080',
            'username': 'admin',
            'password': 'secret'
        })

        # Register a new integration type
        IntegrationFactory.register(
            'custom_client',
            CustomIntegrationClient,
            default_config={'host': 'localhost'}
        )
    """

    _integrations: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        integration_class: Type[BaseIntegrationClient],
        config_class: Optional[Type[IntegrationConfig]] = None,
        default_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register an integration client class.

        Args:
            name: Unique name for the integration
            integration_class: Class that extends BaseIntegrationClient
            config_class: Configuration class for this integration (optional)
            default_config: Default configuration values

        Raises:
            ValueError: If integration name already registered
            TypeError: If integration_class doesn't extend BaseIntegrationClient
        """
        if name in cls._integrations:
            logger.warning(f"Integration '{name}' already registered, overwriting")

        if not issubclass(integration_class, BaseIntegrationClient):
            raise TypeError(
                f"Integration class {integration_class.__name__} must extend "
                "BaseIntegrationClient"
            )

        # Try to infer config class if not provided
        if config_class is None:
            # Look for a config class in the same module with naming convention
            module = integration_class.__module__
            class_name = integration_class.__name__

            # Try common naming patterns: QBittorrentClient -> QBittorrentConfig
            if class_name.endswith("Client"):
                config_class_name = class_name[:-6] + "Config"
            else:
                config_class_name = class_name + "Config"

            try:
                import importlib

                mod = importlib.import_module(module)
                if hasattr(mod, config_class_name):
                    config_class = getattr(mod, config_class_name)
                    logger.debug(f"Auto-detected config class: {config_class_name}")
            except Exception:
                logger.debug(f"Could not auto-detect config class for {name}")

        cls._integrations[name] = {
            "class": integration_class,
            "config_class": config_class,
            "default_config": default_config or {},
        }

        logger.info(f"Registered integration: {name}")

    @classmethod
    def create(
        cls, name: str, config: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> BaseIntegrationClient:
        """
        Create an integration client instance.

        Args:
            name: Name of the registered integration
            config: Configuration override values
            **kwargs: Additional configuration parameters

        Returns:
            Configured integration client instance

        Raises:
            ValueError: If integration name not found
            Exception: If client instantiation fails
        """
        if name not in cls._integrations:
            available = list(cls._integrations.keys())
            raise ValueError(f"Integration '{name}' not found. Available: {available}")

        integration_info = cls._integrations[name]
        integration_class = integration_info["class"]
        config_class = integration_info["config_class"]

        # Merge default config with provided config
        final_config = integration_info["default_config"].copy()
        if config:
            final_config.update(config)
        final_config.update(kwargs)

        try:
            logger.info(f"Creating integration client: {name}")

            # If we have a config class, create a proper config object
            if config_class:
                logger.debug(f"Using config class: {config_class.__name__}")

                # Filter config parameters to only include those accepted by the config class
                import inspect

                config_signature = inspect.signature(config_class)
                valid_params = {}

                for param_name, param_value in final_config.items():
                    if param_name in config_signature.parameters:
                        valid_params[param_name] = param_value
                    else:
                        logger.debug(
                            f"Filtering out invalid parameter '{param_name}' for {config_class.__name__}"
                        )

                config_obj = config_class(**valid_params)
                return integration_class(config_obj)
            else:
                # Fallback to passing dict directly (for backward compatibility)
                logger.warning(f"No config class registered for '{name}', passing dict")
                return integration_class(config=final_config)

        except Exception as e:
            logger.error(f"Failed to create integration '{name}': {e}")
            raise

    @classmethod
    def list_available(cls) -> List[str]:
        """
        Get list of all registered integration names.

        Returns:
            List of integration names
        """
        return list(cls._integrations.keys())

    @classmethod
    def get_info(cls, name: str) -> Dict[str, Any]:
        """
        Get detailed information about a registered integration.

        Args:
            name: Integration name

        Returns:
            Dictionary with integration info including class and config details

        Raises:
            ValueError: If integration name not found
        """
        if name not in cls._integrations:
            available = list(cls._integrations.keys())
            raise ValueError(f"Integration '{name}' not found. Available: {available}")

        info = cls._integrations[name].copy()
        # Convert class references to names for serialization
        info["class_name"] = info["class"].__name__
        if info["config_class"]:
            info["config_class_name"] = info["config_class"].__name__
        else:
            info["config_class_name"] = None

        return info

    @classmethod
    def is_available(cls, name: str) -> bool:
        """
        Check if an integration is available.

        Args:
            name: Integration name

        Returns:
            True if integration is registered
        """
        return name in cls._integrations

    @classmethod
    def clear_registry(cls) -> None:
        """
        Clear all registered integrations.

        Warning:
            This is primarily for testing purposes.
        """
        logger.info("Clearing integration registry")
        cls._integrations.clear()


# Auto-register built-in integrations
def _register_builtin_integrations():
    """Register all built-in integration clients."""

    # Register qBittorrent client
    IntegrationFactory.register(
        "qbittorrent",
        QBittorrentClient,
        QBittorrentConfig,  # Add config class
        default_config={
            "host": "localhost",
            "port": 8080,
            "username": "admin",
            "password": "",
            "use_https": False,
            "timeout": 30.0,
            "verify_ssl": True,
            "max_retries": 3,
            "user_agent": "mk_torrent/1.0 (qBittorrent Integration)",
        },
    )

    logger.info("Auto-registered built-in integrations")


# Auto-register on module import
_register_builtin_integrations()


# Workflow factory for upload workflows
class WorkflowFactory:
    """
    Factory for creating upload workflow instances.

    Provides standardized creation of workflow objects that coordinate
    between integration clients and upload processes.
    """

    _workflows: Dict[str, Type[Any]] = {}

    @classmethod
    def register_workflow(cls, name: str, workflow_class: Type[Any]) -> None:
        """Register a workflow class."""
        cls._workflows[name] = workflow_class
        logger.info(f"Registered workflow: {name}")

    @classmethod
    def create_workflow(
        cls, name: str, integration_client: BaseIntegrationClient, **kwargs: Any
    ) -> Any:
        """Create a workflow instance."""
        if name not in cls._workflows:
            available = list(cls._workflows.keys())
            raise ValueError(f"Workflow '{name}' not found. Available: {available}")

        workflow_class = cls._workflows[name]
        return workflow_class(integration_client=integration_client, **kwargs)

    @classmethod
    def list_workflows(cls) -> List[str]:
        """Get list of available workflow names."""
        return list(cls._workflows.keys())


# Auto-register built-in workflows
def _register_builtin_workflows():
    """Register all built-in workflow classes."""

    # Note: Specific workflow implementations will be added as they're created
    # WorkflowFactory.register_workflow(
    #     'qbittorrent_upload',
    #     QBittorrentUploadWorkflow
    # )

    logger.info("Built-in workflows registration ready")


# Auto-register on module import
_register_builtin_workflows()
