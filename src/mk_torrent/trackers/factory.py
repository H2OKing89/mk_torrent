"""
Tracker Adapter Factory

This module provides centralized adapter creation and configuration management
for all tracker implementations. It standardizes the instantiation pattern
and provides consistent error handling across tracker types.

Usage:
    # Get an adapter by name with configuration
    adapter = TrackerAdapterFactory.create("red", api_key="your_key")

    # Register custom adapter types
    TrackerAdapterFactory.register("custom", CustomAdapter)

    # List available adapters
    adapters = TrackerAdapterFactory.list_available()
"""

from __future__ import annotations

import logging
from typing import Any, Type, Dict, Optional

from pydantic import BaseModel, ValidationError

from mk_torrent.trackers.base import TrackerAPI

logger = logging.getLogger(__name__)


class AdapterConfig(BaseModel):
    """Base configuration for all tracker adapters."""

    adapter_type: str
    name: str = ""
    enabled: bool = True

    class Config:
        extra = "allow"  # Allow tracker-specific config fields


class TrackerAdapterError(Exception):
    """Base exception for tracker adapter errors."""

    pass


class AdapterNotFoundError(TrackerAdapterError):
    """Raised when requested adapter type is not registered."""

    pass


class AdapterConfigurationError(TrackerAdapterError):
    """Raised when adapter configuration is invalid."""

    pass


class TrackerAdapterFactory:
    """
    Factory for creating and managing tracker adapters.

    Provides centralized adapter creation with consistent configuration
    and error handling patterns across all tracker implementations.
    """

    # Registry of available adapter classes
    _adapters: dict[str, type[TrackerAPI]] = {}

    # Registry of adapter configurations
    _configs: dict[str, AdapterConfig] = {}

    @classmethod
    def register(
        cls,
        adapter_type: str,
        adapter_class: type[TrackerAPI],
        default_config: dict[str, Any] | None = None,
    ) -> None:
        """
        Register a new adapter type.

        Args:
            adapter_type: Unique identifier for the adapter (e.g., "red", "mam")
            adapter_class: Class that implements TrackerAPI interface
            default_config: Default configuration values for this adapter type
        """
        if not issubclass(adapter_class, TrackerAPI):
            raise ValueError("Adapter class must implement TrackerAPI interface")

        cls._adapters[adapter_type.lower()] = adapter_class

        if default_config:
            # Extract name separately to avoid duplicate key error
            config_name = default_config.pop("name", adapter_type.upper())
            config = AdapterConfig(
                adapter_type=adapter_type.lower(), name=config_name, **default_config
            )
            cls._configs[adapter_type.lower()] = config

        logger.debug(f"Registered adapter: {adapter_type} -> {adapter_class.__name__}")

    @classmethod
    def create(
        cls,
        adapter_type: str,
        **kwargs: Any,
    ) -> TrackerAPI:
        """
        Create a new adapter instance.

        Args:
            adapter_type: Type of adapter to create ("red", "mam", etc.)
            **kwargs: Configuration parameters specific to the adapter

        Returns:
            Configured adapter instance

        Raises:
            AdapterNotFoundError: If adapter type is not registered
            AdapterConfigurationError: If configuration is invalid
        """
        adapter_type = adapter_type.lower()

        if adapter_type not in cls._adapters:
            available = list(cls._adapters.keys())
            raise AdapterNotFoundError(
                f"Adapter '{adapter_type}' not found. Available: {available}"
            )

        adapter_class = cls._adapters[adapter_type]

        try:
            # Merge with default config if available
            config = {}
            if adapter_type in cls._configs:
                default_config = cls._configs[adapter_type]
                config = default_config.model_dump(
                    exclude={"adapter_type", "name", "enabled"}
                )

            # Override with provided kwargs
            config.update(kwargs)

            logger.debug(f"Creating {adapter_type} adapter with config: {config}")

            # Create the adapter instance
            adapter = adapter_class(**config)

            # Test basic instantiation
            if hasattr(adapter, "get_tracker_config"):
                tracker_config = adapter.get_tracker_config()
                logger.debug(f"Created adapter for {tracker_config.name}")

            return adapter

        except TypeError as e:
            raise AdapterConfigurationError(
                f"Invalid configuration for {adapter_type} adapter: {e}"
            ) from e
        except ValidationError as e:
            raise AdapterConfigurationError(
                f"Configuration validation failed for {adapter_type}: {e}"
            ) from e
        except Exception as e:
            raise AdapterConfigurationError(
                f"Failed to create {adapter_type} adapter: {e}"
            ) from e

    @classmethod
    def list_available(cls) -> dict[str, dict[str, Any]]:
        """
        List all available adapter types with their information.

        Returns:
            Dictionary mapping adapter types to their info
        """
        result: dict[str, dict[str, Any]] = {}

        for adapter_type, adapter_class in cls._adapters.items():
            info = {
                "class": adapter_class.__name__,
                "module": adapter_class.__module__,
                "enabled": True,
            }

            # Add config info if available
            if adapter_type in cls._configs:
                config = cls._configs[adapter_type]
                info.update(
                    {
                        "name": config.name,
                        "enabled": config.enabled,
                    }
                )

            # Get tracker config if possible
            try:
                # Create a temporary instance to get tracker config
                temp_config = {"api_key": "test"} if "red" in adapter_type else {}
                temp_adapter = adapter_class(**temp_config)
                if hasattr(temp_adapter, "get_tracker_config"):
                    tracker_config = temp_adapter.get_tracker_config()
                    info.update(
                        {
                            "tracker_name": tracker_config.name,
                            "announce_url": tracker_config.announce_url,
                            "source_tag": tracker_config.source_tag,
                        }
                    )
            except Exception:
                # Skip if we can't create temp instance
                pass

            result[adapter_type] = info

        return result

    @classmethod
    def is_registered(cls, adapter_type: str) -> bool:
        """Check if an adapter type is registered."""
        return adapter_type.lower() in cls._adapters

    @classmethod
    def get_adapter_class(cls, adapter_type: str) -> type[TrackerAPI]:
        """Get the adapter class for a given type."""
        adapter_type = adapter_type.lower()
        if adapter_type not in cls._adapters:
            raise AdapterNotFoundError(f"Adapter '{adapter_type}' not registered")
        return cls._adapters[adapter_type]

    @classmethod
    def configure_adapter(cls, adapter_type: str, config: dict[str, Any]) -> None:
        """Set default configuration for an adapter type."""
        adapter_type = adapter_type.lower()

        if adapter_type not in cls._adapters:
            raise AdapterNotFoundError(f"Adapter '{adapter_type}' not registered")

        adapter_config = AdapterConfig(adapter_type=adapter_type, **config)
        cls._configs[adapter_type] = adapter_config
        logger.debug(f"Configured adapter {adapter_type}: {config}")


# Auto-register built-in adapters
def _register_builtin_adapters():
    """Register all built-in tracker adapters."""

    # Register RED adapter
    try:
        from mk_torrent.trackers.red_adapter import REDAdapter

        TrackerAdapterFactory.register(
            "red",
            REDAdapter,
            {
                "name": "Redacted",
                "base_url": "https://redacted.ch",
                "timeout": 30.0,
            },
        )
    except ImportError as e:
        logger.warning(f"Could not register RED adapter: {e}")

    # Register MAM adapter
    try:
        from mk_torrent.trackers.mam.adapter import MyAnonaMouseAPI

        TrackerAdapterFactory.register(
            "mam",
            MyAnonaMouseAPI,
            {
                "name": "MyAnonamouse",
                "base_url": "https://www.myanonamouse.net",
                "enabled": True,
            },
        )
    except ImportError as e:
        logger.warning(f"Could not register MAM adapter: {e}")


# Auto-register when module is imported
_register_builtin_adapters()


# Convenience functions for common operations
def create_red_adapter(api_key: str, **kwargs: Any) -> TrackerAPI:
    """Create a RED adapter with API key."""
    return TrackerAdapterFactory.create("red", api_key=api_key, **kwargs)


def create_mam_adapter(**kwargs: Any) -> TrackerAPI:
    """Create a MAM adapter (no API authentication)."""
    return TrackerAdapterFactory.create("mam", **kwargs)


def get_available_trackers() -> list[str]:
    """Get list of available tracker types."""
    return list(TrackerAdapterFactory._adapters.keys())
