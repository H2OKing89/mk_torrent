#!/usr/bin/env python3
"""Upload Queue Management System"""

from pathlib import Path
from typing import Any
from datetime import datetime, timedelta
import json
import uuid
import threading
from dataclasses import dataclass, asdict
from enum import Enum

from rich.console import Console
from rich.table import Table

console = Console()


class UploadStatus(Enum):
    """Upload status enumeration"""

    PENDING = "pending"
    UPLOADING = "uploading"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class UploadJob:
    """Represents a single upload job"""

    job_id: str
    torrent_path: str
    trackers: list[str]
    metadata: dict[str, Any]
    status: UploadStatus
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    results: dict[str, bool] | None = None
    error_message: str | None = None

    def __post_init__(self):
        if self.results is None:
            self.results = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UploadJob":
        """Create from dictionary (JSON deserialization)"""
        data["status"] = UploadStatus(data["status"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)

    def is_expired(self, max_age_hours: int = 24) -> bool:
        """Check if job is expired"""
        return datetime.now() - self.created_at > timedelta(hours=max_age_hours)

    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return (
            self.status == UploadStatus.FAILED and self.retry_count < self.max_retries
        )

    def mark_success(self, tracker: str):
        """Mark upload as successful for a tracker"""
        if self.results is None:
            self.results = {}
        self.results[tracker] = True
        self.updated_at = datetime.now()
        # Check if all trackers have been processed (have results)
        # Allow partial success - job succeeds if at least one tracker succeeds
        if len(self.results) == len(self.trackers):
            if any(self.results.values()):
                self.status = UploadStatus.SUCCESS
            else:
                # All trackers failed
                self.status = UploadStatus.FAILED

    def mark_failed(self, tracker: str, error: str | None = None):
        """Mark upload as failed for a tracker"""
        if self.results is None:
            self.results = {}
        self.results[tracker] = False
        self.error_message = error
        self.updated_at = datetime.now()
        # Only mark as failed if all trackers have been processed and all failed
        if len(self.results) == len(self.trackers) and not any(self.results.values()):
            self.status = UploadStatus.FAILED


class UploadQueue:
    """Thread-safe upload queue management"""

    def __init__(self, queue_dir: Path):
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_file = self.queue_dir / "upload_jobs.json"
        self.lock = threading.RLock()
        self._jobs: dict[str, UploadJob] = {}
        self._load_jobs()
        # Ensure jobs file exists
        if not self.jobs_file.exists():
            self._save_jobs()

    def _load_jobs(self):
        """Load jobs from persistent storage"""
        if not self.jobs_file.exists():
            return

        try:
            with open(self.jobs_file) as f:
                data = json.load(f)
                for job_data in data.get("jobs", []):
                    job = UploadJob.from_dict(job_data)
                    self._jobs[job.job_id] = job
        except (json.JSONDecodeError, KeyError) as e:
            backup_file = None
            if self.jobs_file.exists():
                backup_file = self.jobs_file.with_suffix(".bak")
                self.jobs_file.rename(backup_file)
            console.print(
                f"[yellow]Warning: Could not load upload jobs: {e}\n"
                f"The jobs file appears to be corrupted and has been renamed to: {backup_file}\n"
                "A new jobs file will be created. "
                "If you wish to attempt manual recovery, you can try to fix the backup file and restore it as 'upload_jobs.json'.[/yellow]"
            )

    def _save_jobs(self):
        """Save jobs to persistent storage"""
        data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "jobs": [job.to_dict() for job in self._jobs.values()],
        }

        try:
            with open(self.jobs_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving upload jobs: {e}[/red]")

    def add_job(
        self, torrent_path: Path, trackers: list[str], metadata: dict[str, Any]
    ) -> str:
        """Add a new upload job to the queue"""
        with self.lock:
            job_id = str(uuid.uuid4())
            job = UploadJob(
                job_id=job_id,
                torrent_path=str(torrent_path),
                trackers=trackers,
                metadata=metadata,
                status=UploadStatus.PENDING,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            self._jobs[job_id] = job
            self._save_jobs()
            return job_id

    def get_job(self, job_id: str) -> UploadJob | None:
        """Get a job by ID"""
        with self.lock:
            return self._jobs.get(job_id)

    def get_pending_jobs(self) -> list[UploadJob]:
        """Get all pending jobs"""
        with self.lock:
            return [
                job for job in self._jobs.values() if job.status == UploadStatus.PENDING
            ]

    def get_failed_jobs(self) -> list[UploadJob]:
        """Get all failed jobs that can be retried"""
        with self.lock:
            return [job for job in self._jobs.values() if job.can_retry()]

    def update_job_status(
        self, job_id: str, status: UploadStatus, error_message: str | None = None
    ):
        """Update job status"""
        with self.lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                job.status = status
                job.updated_at = datetime.now()
                if error_message:
                    job.error_message = error_message
                self._save_jobs()

    def mark_job_uploading(self, job_id: str):
        """Mark job as currently uploading"""
        self.update_job_status(job_id, UploadStatus.UPLOADING)

    def mark_job_success(self, job_id: str, tracker: str):
        """Mark job as successful for a tracker"""
        with self.lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                job.mark_success(tracker)
                self._save_jobs()

    def mark_job_failed(self, job_id: str, tracker: str, error: str | None = None):
        """Mark job as failed for a tracker"""
        with self.lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                job.mark_failed(tracker, error)
                self._save_jobs()

    def retry_job(self, job_id: str) -> bool:
        """Retry a failed job"""
        with self.lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                if job.can_retry():
                    job.retry_count += 1
                    job.status = UploadStatus.RETRYING
                    job.updated_at = datetime.now()
                    self._save_jobs()
                    return True
            return False

    def remove_job(self, job_id: str) -> bool:
        """Remove a job from the queue"""
        with self.lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                self._save_jobs()
                return True
            return False

    def cleanup_expired_jobs(self, max_age_hours: int = 24):
        """Remove expired jobs"""
        with self.lock:
            expired_jobs = []
            expired_job_infos = []
            for job_id, job in self._jobs.items():
                if job.is_expired(max_age_hours):
                    expired_jobs.append(job_id)
                    expired_job_infos.append((job_id, job.created_at.isoformat()))

            for job_id in expired_jobs:
                del self._jobs[job_id]

            if expired_jobs:
                self._save_jobs()
                job_info_str = ", ".join(
                    [f"{jid} (created_at: {ts})" for jid, ts in expired_job_infos]
                )
                console.print(
                    f"[dim]Cleaned up {len(expired_jobs)} expired jobs: {job_info_str}[/dim]"
                )

    def get_queue_stats(self) -> dict[str, int]:
        """Get queue statistics"""
        with self.lock:
            stats = {
                "total": len(self._jobs),
                "pending": len(
                    [j for j in self._jobs.values() if j.status == UploadStatus.PENDING]
                ),
                "uploading": len(
                    [
                        j
                        for j in self._jobs.values()
                        if j.status == UploadStatus.UPLOADING
                    ]
                ),
                "success": len(
                    [j for j in self._jobs.values() if j.status == UploadStatus.SUCCESS]
                ),
                "failed": len(
                    [j for j in self._jobs.values() if j.status == UploadStatus.FAILED]
                ),
                "retrying": len(
                    [
                        j
                        for j in self._jobs.values()
                        if j.status == UploadStatus.RETRYING
                    ]
                ),
            }
            return stats

    def display_queue_status(self):
        """Display queue status in a rich table"""
        stats = self.get_queue_stats()

        table = Table(title="📋 Upload Queue Status")
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="magenta", justify="right")

        for status, count in stats.items():
            if status != "total":
                table.add_row(status.title(), str(count))

        table.add_row("", "")
        table.add_row("Total", str(stats["total"]), style="bold")

        console.print(table)

        # Show recent jobs
        if self._jobs:
            recent_jobs = sorted(
                self._jobs.values(), key=lambda x: x.updated_at, reverse=True
            )[:5]

            job_table = Table(title="🔄 Recent Jobs")
            job_table.add_column("Job ID", style="dim")
            job_table.add_column("Status", style="cyan")
            job_table.add_column("Trackers", style="yellow")
            job_table.add_column("Updated", style="green")

            for job in recent_jobs:
                trackers_str = ", ".join(job.trackers[:2])
                if len(job.trackers) > 2:
                    trackers_str += f" +{len(job.trackers) - 2}"
                job_table.add_row(
                    job.job_id[:8],
                    job.status.value.title(),
                    trackers_str,
                    job.updated_at.strftime("%H:%M:%S"),
                )

            console.print(job_table)
