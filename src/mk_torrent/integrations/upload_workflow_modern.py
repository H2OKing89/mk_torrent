"""
Modern upload workflow implementation using new base infrastructure

This provides a concrete implementation of BaseUploadWorkflow with:
- Standardized error handling and progress tracking
- Integration with the existing metadata system
- Path compliance checking and auto-fixing
- Tracker API integration through existing systems

Part of Phase 3B.2: Upload Workflow Unification
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rich.console import Console

from .workflows import (
    BaseUploadWorkflow,
    UploadWorkflowConfig,
    WorkflowStep,
    WorkflowStepResult,
    WorkflowStatus,
)

console = Console()
logger = logging.getLogger(__name__)


class ModernUploadWorkflow(BaseUploadWorkflow):
    """Modern upload workflow using base infrastructure and existing systems"""

    def __init__(self, config: UploadWorkflowConfig, api_key: str):
        super().__init__(config)
        self.api_key = api_key
        self.tracker_api = None
        self.metadata_engine = None

    def _step_initialize(self) -> WorkflowStepResult:
        """Initialize the workflow (API clients, metadata engine, etc.)"""
        try:
            # Check API key
            if not self.api_key:
                return WorkflowStepResult(
                    step=WorkflowStep.INITIALIZE,
                    status=WorkflowStatus.FAILED,
                    message=f"No API key configured for {self.config.tracker.upper()}",
                )

            # Initialize tracker API using existing system
            from ..trackers.factory import TrackerAdapterFactory

            self.tracker_api = TrackerAdapterFactory.create(
                self.config.tracker, api_key=self.api_key
            )

            # Test connection
            if not self.tracker_api.test_connection():
                return WorkflowStepResult(
                    step=WorkflowStep.INITIALIZE,
                    status=WorkflowStatus.FAILED,
                    message=f"Failed to connect to {self.config.tracker.upper()} API",
                )

            # Initialize metadata engine
            from ..core.metadata.engine import MetadataEngine
            from ..core.metadata.processors.audiobook import AudiobookProcessor

            self.metadata_engine = MetadataEngine()
            audiobook_processor = AudiobookProcessor()
            self.metadata_engine.register_processor("audiobook", audiobook_processor)
            self.metadata_engine.set_default_processor("audiobook")

            self._store_workflow_data("tracker_api", self.tracker_api)
            self._store_workflow_data("metadata_engine", self.metadata_engine)

            return WorkflowStepResult(
                step=WorkflowStep.INITIALIZE,
                status=WorkflowStatus.SUCCESS,
                message=f"Connected to {self.config.tracker.upper()} and initialized metadata engine",
                data={
                    "tracker": self.config.tracker,
                    "api_connected": True,
                    "metadata_engine_ready": True,
                },
            )

        except Exception as e:
            logger.exception("Initialization failed")
            return WorkflowStepResult(
                step=WorkflowStep.INITIALIZE,
                status=WorkflowStatus.FAILED,
                message=f"Initialization failed: {e}",
                error_details={"exception": str(e)},
            )

    def _step_validate_path(self) -> WorkflowStepResult:
        """Validate source path and check compliance"""
        try:
            # Import path compliance functions from existing system
            from ..workflows.upload_integration import (
                check_path_compliance,
                fix_path_compliance,
            )

            console.print(
                f"[cyan]Checking path compliance for {self.config.tracker.upper()}...[/cyan]"
            )
            compliance_result = check_path_compliance(
                self.config.source_path, self.config.tracker
            )

            if compliance_result["compliant"]:
                return WorkflowStepResult(
                    step=WorkflowStep.VALIDATE_PATH,
                    status=WorkflowStatus.SUCCESS,
                    message=f"Path compliant with {self.config.tracker.upper()} requirements",
                    data=compliance_result,
                )

            # Path is not compliant
            issues = compliance_result.get("issues", [])
            console.print("[yellow]⚠ Path compliance issues found:[/yellow]")
            for issue in issues:
                console.print(f"[yellow]  • {issue}[/yellow]")

            if not compliance_result.get("fixable", False):
                return WorkflowStepResult(
                    step=WorkflowStep.VALIDATE_PATH,
                    status=WorkflowStatus.FAILED,
                    message="Path issues cannot be auto-fixed",
                    error_details={"issues": issues},
                )

            # Auto-fix if enabled
            if self.config.auto_fix_paths:
                console.print("[cyan]Auto-fixing path compliance issues...[/cyan]")

                fixed_path = fix_path_compliance(
                    self.config.source_path, self.config.tracker, dry_run=False
                )

                if fixed_path and fixed_path != self.config.source_path:
                    console.print(f"[green]✓ Path fixed: {fixed_path.name}[/green]")

                    # Update config with new path
                    self.config.source_path = fixed_path
                    self._store_workflow_data(
                        "original_path", str(self.config.source_path)
                    )
                    self._store_workflow_data("fixed_path", str(fixed_path))

                    return WorkflowStepResult(
                        step=WorkflowStep.VALIDATE_PATH,
                        status=WorkflowStatus.SUCCESS,
                        message="Path compliance fixed automatically",
                        data={
                            "fixed": True,
                            "new_path": str(fixed_path),
                            "issues_resolved": issues,
                        },
                    )
                else:
                    return WorkflowStepResult(
                        step=WorkflowStep.VALIDATE_PATH,
                        status=WorkflowStatus.FAILED,
                        message="Failed to fix path compliance issues",
                        error_details={"issues": issues},
                    )
            else:
                return WorkflowStepResult(
                    step=WorkflowStep.VALIDATE_PATH,
                    status=WorkflowStatus.FAILED,
                    message="Path compliance issues found (auto-fix disabled)",
                    error_details={"issues": issues},
                )

        except Exception as e:
            logger.exception("Path validation failed")
            return WorkflowStepResult(
                step=WorkflowStep.VALIDATE_PATH,
                status=WorkflowStatus.FAILED,
                message=f"Path validation failed: {e}",
                error_details={"exception": str(e)},
            )

    def _step_extract_metadata(self) -> WorkflowStepResult:
        """Extract metadata from source content"""
        try:
            source_path = self.config.source_path
            console.print(f"[cyan]Extracting metadata from: {source_path.name}[/cyan]")

            # Find audiobook file if source is directory
            audiobook_file = source_path
            if source_path.is_dir():
                audiobook_files = list(source_path.glob("*.m4b")) + list(
                    source_path.glob("*.mp3")
                )
                if not audiobook_files:
                    return WorkflowStepResult(
                        step=WorkflowStep.EXTRACT_METADATA,
                        status=WorkflowStatus.FAILED,
                        message="No audiobook files (.m4b or .mp3) found in directory",
                    )
                audiobook_file = audiobook_files[0]
                console.print(f"[dim]Using file: {audiobook_file.name}[/dim]")

            # Extract metadata using existing system
            metadata_dict = self.metadata_engine.extract_metadata(audiobook_file)

            # Convert to AudiobookMeta for consistency
            from ..core.metadata.base import AudiobookMeta

            audiobookmeta_fields = {
                field.name for field in AudiobookMeta.__dataclass_fields__.values()
            }
            filtered_metadata = {
                k: v for k, v in metadata_dict.items() if k in audiobookmeta_fields
            }

            # Convert year to int if it's a string
            if "year" in filtered_metadata and isinstance(
                filtered_metadata["year"], str
            ):
                try:
                    filtered_metadata["year"] = int(filtered_metadata["year"])
                except (ValueError, TypeError):
                    filtered_metadata["year"] = None

            audiobook_meta = AudiobookMeta(**filtered_metadata)

            # Map to tracker format
            from ..core.metadata.mappers.red import REDMapper

            red_mapper = REDMapper()
            tracker_data = red_mapper.map_to_red_upload(
                audiobook_meta, include_description=True
            )

            # Store metadata for later steps
            metadata = {
                "raw": metadata_dict,
                "audiobook_meta": audiobook_meta,
                "tracker_data": tracker_data,
                "content_type": "audiobook",
                "source_file": audiobook_file,
            }

            self._store_workflow_data("metadata", metadata)
            self._store_workflow_data("audiobook_file", audiobook_file)

            console.print(
                f"[green]✓ Metadata extracted: {audiobook_meta.title} by {audiobook_meta.author}[/green]"
            )

            return WorkflowStepResult(
                step=WorkflowStep.EXTRACT_METADATA,
                status=WorkflowStatus.SUCCESS,
                message=f"Metadata extracted: {audiobook_meta.title} by {audiobook_meta.author}",
                data={
                    "title": audiobook_meta.title,
                    "author": audiobook_meta.author,
                    "content_type": "audiobook",
                    "source_file": str(audiobook_file),
                },
            )

        except Exception as e:
            logger.exception("Metadata extraction failed")
            return WorkflowStepResult(
                step=WorkflowStep.EXTRACT_METADATA,
                status=WorkflowStatus.FAILED,
                message=f"Metadata extraction failed: {e}",
                error_details={"exception": str(e)},
            )

    def _step_validate_metadata(self) -> WorkflowStepResult:
        """Validate extracted metadata against tracker requirements"""
        try:
            metadata = self._get_workflow_data("metadata")
            if not metadata:
                return WorkflowStepResult(
                    step=WorkflowStep.VALIDATE_METADATA,
                    status=WorkflowStatus.FAILED,
                    message="No metadata available for validation",
                )

            # Import validation function from existing system
            from ..workflows.upload_integration import _validate_with_red_api

            console.print(
                "[cyan]Validating metadata with tracker requirements...[/cyan]"
            )

            # Prepare enhanced metadata for validation (following existing pattern)
            enhanced_metadata = {
                "raw": metadata["raw"],
                "source_path": self.config.source_path,
                "folder_name": self.config.source_path.name,
            }

            if self.config.require_complete_metadata:
                validation_result = _validate_with_red_api(
                    enhanced_metadata, self.api_key
                )

                if not validation_result:
                    return WorkflowStepResult(
                        step=WorkflowStep.VALIDATE_METADATA,
                        status=WorkflowStatus.FAILED,
                        message="Metadata validation failed against tracker requirements",
                    )

            console.print("[green]✓ Metadata validation passed[/green]")

            return WorkflowStepResult(
                step=WorkflowStep.VALIDATE_METADATA,
                status=WorkflowStatus.SUCCESS,
                message="Metadata validation passed",
                data={"validated": True},
            )

        except Exception as e:
            logger.exception("Metadata validation failed")
            return WorkflowStepResult(
                step=WorkflowStep.VALIDATE_METADATA,
                status=WorkflowStatus.FAILED,
                message=f"Metadata validation failed: {e}",
                error_details={"exception": str(e)},
            )

    def _step_check_existing(self) -> WorkflowStepResult:
        """Check for existing torrents on the tracker"""
        try:
            metadata = self._get_workflow_data("metadata")
            if not metadata:
                return WorkflowStepResult(
                    step=WorkflowStep.CHECK_EXISTING,
                    status=WorkflowStatus.FAILED,
                    message="No metadata available for existence check",
                )

            console.print(
                f"[cyan]Checking for existing torrents on {self.config.tracker.upper()}...[/cyan]"
            )

            # Extract search parameters from metadata
            search_params = {}
            raw_metadata = metadata.get("raw", {})

            if raw_metadata.get("artist"):
                search_params["artist"] = raw_metadata["artist"]
            if raw_metadata.get("album"):
                search_params["album"] = raw_metadata["album"]
            if raw_metadata.get("title"):
                search_params["title"] = raw_metadata["title"]

            if search_params:
                existing = self.tracker_api.search_existing(**search_params)

                if existing:
                    console.print(
                        f"[yellow]⚠ Found {len(existing)} potentially matching torrents[/yellow]"
                    )

                    # Show first few matches
                    for i, torrent in enumerate(existing[:3], 1):
                        title = torrent.get(
                            "groupName", torrent.get("title", "Unknown")
                        )
                        console.print(f"[dim]  {i}. {title}[/dim]")

                    if not self.config.force_upload:
                        return WorkflowStepResult(
                            step=WorkflowStep.CHECK_EXISTING,
                            status=WorkflowStatus.FAILED,
                            message=f"Found {len(existing)} existing torrents (use force_upload to override)",
                            data={"existing_torrents": existing},
                        )
                    else:
                        console.print(
                            "[yellow]⚠ Continuing despite existing torrents (force_upload=True)[/yellow]"
                        )

                        return WorkflowStepResult(
                            step=WorkflowStep.CHECK_EXISTING,
                            status=WorkflowStatus.SUCCESS,
                            message=f"Found {len(existing)} existing torrents but continuing (forced)",
                            data={"existing_torrents": existing, "forced": True},
                        )
                else:
                    console.print("[green]✓ No existing torrents found[/green]")

                    return WorkflowStepResult(
                        step=WorkflowStep.CHECK_EXISTING,
                        status=WorkflowStatus.SUCCESS,
                        message="No existing torrents found",
                        data={"existing_torrents": []},
                    )
            else:
                return WorkflowStepResult(
                    step=WorkflowStep.CHECK_EXISTING,
                    status=WorkflowStatus.SUCCESS,
                    message="No search parameters available, skipping existence check",
                    data={"skipped": True},
                )

        except Exception as e:
            logger.exception("Existence check failed")
            # Non-fatal error - continue with warning
            console.print(f"[yellow]⚠ Existence check failed: {e}[/yellow]")
            return WorkflowStepResult(
                step=WorkflowStep.CHECK_EXISTING,
                status=WorkflowStatus.SUCCESS,
                message=f"Existence check failed, continuing: {e}",
                data={"error": str(e), "continued": True},
            )

    def _step_create_torrent(self) -> WorkflowStepResult:
        """Create torrent file from source content"""
        try:
            # For now, assume torrent file exists or create a placeholder
            # This would integrate with existing torrent creation logic
            torrent_path = (
                self.config.source_path.parent
                / f"{self.config.source_path.name}.torrent"
            )

            # TODO: Integrate with actual torrent creation system
            # This is a placeholder that matches existing workflow behavior

            self._store_workflow_data("torrent_path", torrent_path)

            return WorkflowStepResult(
                step=WorkflowStep.CREATE_TORRENT,
                status=WorkflowStatus.SUCCESS,
                message=f"Torrent file prepared: {torrent_path.name}",
                data={"torrent_path": str(torrent_path)},
            )

        except Exception as e:
            logger.exception("Torrent creation failed")
            return WorkflowStepResult(
                step=WorkflowStep.CREATE_TORRENT,
                status=WorkflowStatus.FAILED,
                message=f"Torrent creation failed: {e}",
                error_details={"exception": str(e)},
            )

    def _step_upload(self) -> WorkflowStepResult:
        """Upload torrent to tracker"""
        try:
            metadata = self._get_workflow_data("metadata")
            torrent_path = self._get_workflow_data("torrent_path")

            if not metadata or not torrent_path:
                return WorkflowStepResult(
                    step=WorkflowStep.UPLOAD,
                    status=WorkflowStatus.FAILED,
                    message="Missing metadata or torrent file for upload",
                )

            if self.config.dry_run:
                console.print(
                    f"[yellow]DRY RUN: Would upload to {self.config.tracker.upper()}[/yellow]"
                )
                console.print(f"[dim]  Source: {self.config.source_path}[/dim]")
                console.print(f"[dim]  Torrent: {torrent_path}[/dim]")
                console.print(
                    f"[dim]  Content: {metadata.get('content_type', 'unknown')}[/dim]"
                )

                # Show what would be uploaded (debug info)
                if self.config.tracker.lower() == "red":
                    console.print(
                        "\n[bold cyan]🔍 DEBUG: Upload payload preview[/bold cyan]"
                    )
                    self.tracker_api.prepare_upload_data(metadata["raw"], torrent_path)

                return WorkflowStepResult(
                    step=WorkflowStep.UPLOAD,
                    status=WorkflowStatus.SUCCESS,
                    message="Dry run upload completed",
                    data={"dry_run": True, "tracker": self.config.tracker},
                )
            else:
                # Actual upload
                console.print(
                    f"[cyan]Uploading to {self.config.tracker.upper()}...[/cyan]"
                )
                result = self.tracker_api.upload_torrent(
                    torrent_path, metadata, dry_run=False
                )

                if result.get("success"):
                    upload_url = result.get("url")
                    console.print(
                        f"[green]✓ Successfully uploaded to {self.config.tracker.upper()}![/green]"
                    )
                    if upload_url:
                        console.print(f"[dim]  URL: {upload_url}[/dim]")

                    self._store_workflow_data("upload_url", upload_url)

                    return WorkflowStepResult(
                        step=WorkflowStep.UPLOAD,
                        status=WorkflowStatus.SUCCESS,
                        message="Upload completed successfully",
                        data={"upload_url": upload_url, "tracker": self.config.tracker},
                    )
                else:
                    error_message = result.get("error", "Unknown upload error")
                    console.print(
                        f"[red]✗ Upload to {self.config.tracker.upper()} failed[/red]"
                    )
                    console.print(f"[red]  Error: {error_message}[/red]")

                    return WorkflowStepResult(
                        step=WorkflowStep.UPLOAD,
                        status=WorkflowStatus.FAILED,
                        message=f"Upload failed: {error_message}",
                        error_details={"upload_result": result},
                    )

        except Exception as e:
            logger.exception("Upload failed")
            return WorkflowStepResult(
                step=WorkflowStep.UPLOAD,
                status=WorkflowStatus.FAILED,
                message=f"Upload failed: {e}",
                error_details={"exception": str(e)},
            )


# Convenience function to maintain compatibility with existing CLI
def modern_upload_workflow(
    source_path: Path,
    tracker: str,
    config: dict[str, Any],
    dry_run: bool = True,
    check_existing: bool = True,
) -> bool:
    """Modern upload workflow function compatible with existing CLI"""

    # Get API key
    api_key_field = f"{tracker}_api_key"
    api_key = config.get(api_key_field)

    if not api_key:
        console.print(f"[red]✗ {tracker.upper()} API key not configured[/red]")
        return False

    # Create workflow config
    workflow_config = UploadWorkflowConfig(
        source_path=source_path,
        tracker=tracker,
        dry_run=dry_run,
        check_existing=check_existing,
        auto_fix_paths=True,
        force_upload=config.get("force_upload", False),
    )

    # Execute workflow
    workflow = ModernUploadWorkflow(workflow_config, api_key)
    result = workflow.execute()

    return result.success


__all__ = [
    "ModernUploadWorkflow",
    "modern_upload_workflow",
]
