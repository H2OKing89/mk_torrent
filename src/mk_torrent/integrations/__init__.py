"""
Integrations package for external APIs and services

DEPRECATION NOTICE: Audnexus functionality moved to core metadata system
======================================================================

As of 2025-01-09, Audnexus integration has been consolidated into the
core metadata system at mk_torrent.core.metadata.sources.audnexus.

This consolidation follows the established architecture pattern where:
- core/metadata/ contains all metadata processing logic
- integrations/ contains only HTTP clients and minimal wrappers

The integration files will be removed on 2025-02-09.

NEW IN PHASE 3B.2: Modern Integration Infrastructure
===================================================

The integrations package now provides standardized base classes and
infrastructure for all external service integrations:

- BaseIntegrationClient: Common patterns for HTTP clients
- BaseUploadWorkflow: Standardized upload workflow steps
- Unified error handling and retry logic
- Standardized configuration management
"""

import warnings

# Re-export from deprecated modules (which in turn import from core)
# This preserves backward compatibility during migration period
from .audnexus import AudnexusAPI, get_audnexus_metadata, get_audnexus_metadata_async

# Export new modern infrastructure (Phase 3B.2)
from .base import (
    BaseIntegrationClient,
    IntegrationConfig,
    IntegrationError,
    IntegrationResponse,
    IntegrationStatus,
)
from .workflows import (
    BaseUploadWorkflow,
    UploadWorkflowConfig,
    UploadWorkflowResult,
    WorkflowStep,
    WorkflowStatus,
)
from .qbittorrent_modern import QBittorrentClient, QBittorrentConfig
from .upload_workflow_modern import ModernUploadWorkflow, modern_upload_workflow

# Issue deprecation warning for the whole package when importing Audnexus
warnings.warn(
    "Audnexus integrations are deprecated. "
    "Use mk_torrent.core.metadata.sources.audnexus instead. "
    "Integration files will be removed on 2025-02-09.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    # Deprecated Audnexus (Phase 3B.1)
    "AudnexusAPI",  # DEPRECATED: Use AudnexusSource from core.metadata.sources.audnexus
    "get_audnexus_metadata",
    "get_audnexus_metadata_async",
    # Modern Infrastructure (Phase 3B.2)
    # Base classes
    "BaseIntegrationClient",
    "BaseUploadWorkflow",
    # Configuration and responses
    "IntegrationConfig",
    "IntegrationResponse",
    "IntegrationStatus",
    "IntegrationError",
    # Workflow infrastructure
    "UploadWorkflowConfig",
    "UploadWorkflowResult",
    "WorkflowStep",
    "WorkflowStatus",
    # Concrete implementations
    "QBittorrentClient",
    "QBittorrentConfig",
    "ModernUploadWorkflow",
    "modern_upload_workflow",
]
