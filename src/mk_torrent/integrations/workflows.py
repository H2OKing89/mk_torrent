"""
Base upload workflow infrastructure for standardized upload operations

This module provides common patterns for upload workflows including:
- Standardized workflow steps and error propagation
- Path validation and compliance checking
- Metadata extraction and validation
- Torrent creation and upload coordination
- Progress tracking and user feedback

Part of Phase 3B.2: Upload Workflow Unification
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console

from .base import IntegrationResponse

console = Console()
logger = logging.getLogger(__name__)


class WorkflowStep(Enum):
    """Standardized workflow steps"""

    INITIALIZE = "initialize"
    VALIDATE_PATH = "validate_path"
    EXTRACT_METADATA = "extract_metadata"
    VALIDATE_METADATA = "validate_metadata"
    CHECK_EXISTING = "check_existing"
    CREATE_TORRENT = "create_torrent"
    UPLOAD = "upload"
    CLEANUP = "cleanup"
    COMPLETED = "completed"


class WorkflowStatus(Enum):
    """Workflow execution status"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class WorkflowStepResult:
    """Result of a single workflow step"""

    step: WorkflowStep
    status: WorkflowStatus
    message: str | None = None
    data: dict[str, Any] | None = None
    error_details: dict[str, Any] | None = None
    execution_time: float = 0.0

    @property
    def success(self) -> bool:
        return self.status == WorkflowStatus.SUCCESS

    @property
    def can_continue(self) -> bool:
        return self.status in [WorkflowStatus.SUCCESS, WorkflowStatus.SKIPPED]


@dataclass
class UploadWorkflowConfig:
    """Configuration for upload workflows"""

    source_path: Path
    tracker: str
    dry_run: bool = True
    check_existing: bool = True
    force_upload: bool = False
    auto_fix_paths: bool = True
    create_backup: bool = False
    cleanup_on_failure: bool = True

    # Path validation settings
    max_path_length: int | None = None  # Will be set based on tracker
    validate_filenames: bool = True

    # Metadata settings
    require_complete_metadata: bool = True
    validate_against_tracker: bool = True

    # Upload settings
    verify_upload: bool = True
    add_to_client: bool = True

    def __post_init__(self):
        if not self.source_path.exists():
            raise ValueError(f"Source path does not exist: {self.source_path}")

        # Set tracker-specific defaults
        if self.max_path_length is None:
            self.max_path_length = 180 if self.tracker.lower() == "red" else 255


@dataclass
class UploadWorkflowResult:
    """Final result of upload workflow"""

    config: UploadWorkflowConfig
    status: WorkflowStatus
    step_results: list[WorkflowStepResult] = field(default_factory=list)
    final_message: str | None = None
    torrent_path: Path | None = None
    upload_url: str | None = None
    execution_time: float = 0.0

    @property
    def success(self) -> bool:
        return self.status == WorkflowStatus.SUCCESS

    @property
    def failed_step(self) -> WorkflowStep | None:
        """Get the first step that failed"""
        for result in self.step_results:
            if result.status == WorkflowStatus.FAILED:
                return result.step
        return None

    def get_step_result(self, step: WorkflowStep) -> WorkflowStepResult | None:
        """Get result for a specific step"""
        for result in self.step_results:
            if result.step == step:
                return result
        return None


class BaseUploadWorkflow(ABC):
    """Base class for all upload workflows"""

    def __init__(self, config: UploadWorkflowConfig):
        self.config = config
        self.step_results: list[WorkflowStepResult] = []
        self.current_step: WorkflowStep | None = None

        # Workflow data shared between steps
        self.workflow_data: dict[str, Any] = {}

    def execute(self) -> UploadWorkflowResult:
        """Execute the complete upload workflow"""
        import time

        start_time = time.time()

        console.print(
            f"\n[bold cyan]═══ Upload Workflow - {self.config.tracker.upper()} ═══[/bold cyan]\n"
        )

        if self.config.dry_run:
            console.print(
                "[yellow]🔍 DRY RUN MODE - No actual upload will be performed[/yellow]\n"
            )

        try:
            # Execute workflow steps in sequence
            workflow_steps = [
                WorkflowStep.INITIALIZE,
                WorkflowStep.VALIDATE_PATH,
                WorkflowStep.EXTRACT_METADATA,
                WorkflowStep.VALIDATE_METADATA,
                WorkflowStep.CHECK_EXISTING,
                WorkflowStep.CREATE_TORRENT,
                WorkflowStep.UPLOAD,
                WorkflowStep.CLEANUP,
                WorkflowStep.COMPLETED,
            ]

            for step in workflow_steps:
                # Skip certain steps based on configuration
                if self._should_skip_step(step):
                    self._add_step_result(
                        WorkflowStepResult(
                            step=step,
                            status=WorkflowStatus.SKIPPED,
                            message="Step skipped due to configuration",
                        )
                    )
                    continue

                self.current_step = step
                console.print(
                    f"[cyan]📋 {step.value.replace('_', ' ').title()}...[/cyan]"
                )

                # Execute the step
                step_result = self._execute_step(step)
                self._add_step_result(step_result)

                # Check if we can continue
                if not step_result.can_continue:
                    console.print(f"[red]❌ Workflow stopped at: {step.value}[/red]")
                    if step_result.message:
                        console.print(f"[red]   {step_result.message}[/red]")

                    return UploadWorkflowResult(
                        config=self.config,
                        status=WorkflowStatus.FAILED,
                        step_results=self.step_results,
                        final_message=step_result.message,
                        execution_time=time.time() - start_time,
                    )

                # Display step success
                status_icon = "✅" if step_result.success else "⏭️"
                console.print(
                    f"[green]{status_icon} {step.value.replace('_', ' ').title()} complete[/green]"
                )

            # Workflow completed successfully
            console.print(
                "\n[bold green]🎉 Upload workflow completed successfully![/bold green]"
            )

            return UploadWorkflowResult(
                config=self.config,
                status=WorkflowStatus.SUCCESS,
                step_results=self.step_results,
                final_message="Upload workflow completed successfully",
                torrent_path=self.workflow_data.get("torrent_path"),
                upload_url=self.workflow_data.get("upload_url"),
                execution_time=time.time() - start_time,
            )

        except KeyboardInterrupt:
            console.print("\n[yellow]⏹️ Workflow cancelled by user[/yellow]")
            return UploadWorkflowResult(
                config=self.config,
                status=WorkflowStatus.CANCELLED,
                step_results=self.step_results,
                final_message="Workflow cancelled by user",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            console.print(f"\n[red]💥 Unexpected workflow error: {e}[/red]")
            logger.exception("Workflow execution failed")

            return UploadWorkflowResult(
                config=self.config,
                status=WorkflowStatus.FAILED,
                step_results=self.step_results,
                final_message=f"Unexpected error: {e}",
                execution_time=time.time() - start_time,
            )

    def _should_skip_step(self, step: WorkflowStep) -> bool:
        """Determine if a step should be skipped based on configuration"""
        if step == WorkflowStep.CHECK_EXISTING and not self.config.check_existing:
            return True
        if step == WorkflowStep.UPLOAD and self.config.dry_run:
            # Don't skip upload step in dry run - we want to show what would happen
            return False
        return False

    def _execute_step(self, step: WorkflowStep) -> WorkflowStepResult:
        """Execute a single workflow step with error handling"""
        import time

        start_time = time.time()

        try:
            # Dispatch to the appropriate step method
            method_name = f"_step_{step.value}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                result = method()
            else:
                # Default implementation
                result = self._default_step_implementation(step)

            # Ensure result is a WorkflowStepResult
            if not isinstance(result, WorkflowStepResult):
                data: dict[str, Any] = (
                    result if isinstance(result, dict) else {"result": result}
                )
                result = WorkflowStepResult(
                    step=step, status=WorkflowStatus.SUCCESS, data=data
                )

            result.execution_time = time.time() - start_time
            return result

        except Exception as e:
            logger.exception(f"Step {step.value} failed")
            return WorkflowStepResult(
                step=step,
                status=WorkflowStatus.FAILED,
                message=f"Step failed: {e}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
            )

    def _add_step_result(self, result: WorkflowStepResult):
        """Add a step result to the workflow results"""
        self.step_results.append(result)

    # Abstract step methods - subclasses must implement these

    @abstractmethod
    def _step_initialize(self) -> WorkflowStepResult:
        """Initialize the workflow (e.g., check API keys, create clients)"""
        pass

    @abstractmethod
    def _step_validate_path(self) -> WorkflowStepResult:
        """Validate source path and check compliance"""
        pass

    @abstractmethod
    def _step_extract_metadata(self) -> WorkflowStepResult:
        """Extract metadata from source content"""
        pass

    @abstractmethod
    def _step_validate_metadata(self) -> WorkflowStepResult:
        """Validate extracted metadata against tracker requirements"""
        pass

    @abstractmethod
    def _step_check_existing(self) -> WorkflowStepResult:
        """Check for existing torrents on the tracker"""
        pass

    @abstractmethod
    def _step_create_torrent(self) -> WorkflowStepResult:
        """Create torrent file from source content"""
        pass

    @abstractmethod
    def _step_upload(self) -> WorkflowStepResult:
        """Upload torrent to tracker"""
        pass

    def _step_cleanup(self) -> WorkflowStepResult:
        """Cleanup temporary files and resources (optional override)"""
        return WorkflowStepResult(
            step=WorkflowStep.CLEANUP,
            status=WorkflowStatus.SUCCESS,
            message="No cleanup required",
        )

    def _step_completed(self) -> WorkflowStepResult:
        """Final workflow step (optional override)"""
        return WorkflowStepResult(
            step=WorkflowStep.COMPLETED,
            status=WorkflowStatus.SUCCESS,
            message="Workflow completed",
        )

    def _default_step_implementation(self, step: WorkflowStep) -> WorkflowStepResult:
        """Default implementation for steps not overridden"""
        return WorkflowStepResult(
            step=step,
            status=WorkflowStatus.SUCCESS,
            message=f"Default implementation for {step.value}",
        )

    # Helper methods for common operations

    def _store_workflow_data(self, key: str, value: Any):
        """Store data to be shared between workflow steps"""
        self.workflow_data[key] = value

    def _get_workflow_data(self, key: str, default: Any = None) -> Any:
        """Retrieve data stored by previous workflow steps"""
        return self.workflow_data.get(key, default)

    def _handle_integration_response(
        self,
        response: IntegrationResponse,
        step: WorkflowStep,
        success_message: str = "Operation completed",
    ) -> WorkflowStepResult:
        """Convert IntegrationResponse to WorkflowStepResult"""
        if response.success:
            return WorkflowStepResult(
                step=step,
                status=WorkflowStatus.SUCCESS,
                message=success_message,
                data=response.data,
                execution_time=response.execution_time,
            )
        else:
            return WorkflowStepResult(
                step=step,
                status=WorkflowStatus.FAILED,
                message=response.message or "Operation failed",
                error_details=response.error_details,
                execution_time=response.execution_time,
            )


__all__ = [
    # Enums
    "WorkflowStep",
    "WorkflowStatus",
    # Data Classes
    "WorkflowStepResult",
    "UploadWorkflowConfig",
    "UploadWorkflowResult",
    # Base Classes
    "BaseUploadWorkflow",
]
