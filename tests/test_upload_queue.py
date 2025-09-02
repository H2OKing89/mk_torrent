#!/usr/bin/env python3
"""Unit tests for upload queue system"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.mk_torrent.core.upload_queue import UploadQueue, UploadJob, UploadStatus

class TestUploadJob(unittest.TestCase):
    """Test cases for UploadJob class"""

    def _assert_job_results_initialized(self, job: UploadJob):
        """Helper method to assert job results are properly initialized"""
        self.assertIsNotNone(job.results)
        if job.results is not None:
            self.assertEqual(len(job.results), 0)

    def test_job_creation(self):
        """Test creating a new upload job"""
        job = UploadJob(
            job_id="test-job-1",
            torrent_path="/path/to/torrent.torrent",
            trackers=["red", "ops"],
            metadata={"title": "Test Torrent"},
            status=UploadStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self.assertEqual(job.job_id, "test-job-1")
        self.assertEqual(job.torrent_path, "/path/to/torrent.torrent")
        self.assertEqual(job.trackers, ["red", "ops"])
        self.assertEqual(job.status, UploadStatus.PENDING)
        self._assert_job_results_initialized(job)

    def test_job_serialization(self):
        """Test job serialization to/from dict"""
        original_job = UploadJob(
            job_id="test-job-1",
            torrent_path="/path/to/torrent.torrent",
            trackers=["red", "ops"],
            metadata={"title": "Test Torrent"},
            status=UploadStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Serialize to dict
        job_dict = original_job.to_dict()

        # Deserialize from dict
        restored_job = UploadJob.from_dict(job_dict)

        self.assertEqual(restored_job.job_id, original_job.job_id)
        self.assertEqual(restored_job.torrent_path, original_job.torrent_path)
        self.assertEqual(restored_job.trackers, original_job.trackers)
        self.assertEqual(restored_job.status, original_job.status)

    def test_job_mark_success(self):
        """Test marking job as successful"""
        job = UploadJob(
            job_id="test-job-1",
            torrent_path="/path/to/torrent.torrent",
            trackers=["red", "ops"],
            metadata={},
            status=UploadStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Mark success for one tracker
        job.mark_success("red")
        self.assertIsNotNone(job.results)
        if job.results is not None:
            self.assertEqual(job.results["red"], True)
        self.assertEqual(job.status, UploadStatus.PENDING)  # Not complete yet

        # Mark success for second tracker
        job.mark_success("ops")
        self.assertIsNotNone(job.results)
        if job.results is not None:
            self.assertEqual(job.results["ops"], True)
        self.assertEqual(job.status, UploadStatus.SUCCESS)  # Now complete

    def test_job_mark_failed(self):
        """Test marking job as failed"""
        job = UploadJob(
            job_id="test-job-1",
            torrent_path="/path/to/torrent.torrent",
            trackers=["red"],
            metadata={},
            status=UploadStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Mark failed
        job.mark_failed("red", "Network error")
        self.assertIsNotNone(job.results)
        if job.results is not None:
            self.assertEqual(job.results["red"], False)
        self.assertEqual(job.error_message, "Network error")
        self.assertEqual(job.status, UploadStatus.FAILED)

    def test_job_can_retry(self):
        """Test retry logic"""
        job = UploadJob(
            job_id="test-job-1",
            torrent_path="/path/to/torrent.torrent",
            trackers=["red"],
            metadata={},
            status=UploadStatus.FAILED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            retry_count=0,
            max_retries=3
        )

        # Should be able to retry
        self.assertTrue(job.can_retry())

        # Increment retry count
        job.retry_count = 3
        self.assertFalse(job.can_retry())  # Max retries reached

    def test_job_is_expired(self):
        """Test job expiration"""
        recent_time = datetime.now() - timedelta(hours=1)
        old_time = datetime.now() - timedelta(hours=25)

        recent_job = UploadJob(
            job_id="recent",
            torrent_path="/path/to/torrent.torrent",
            trackers=["red"],
            metadata={},
            status=UploadStatus.PENDING,
            created_at=recent_time,
            updated_at=recent_time
        )

        old_job = UploadJob(
            job_id="old",
            torrent_path="/path/to/torrent.torrent",
            trackers=["red"],
            metadata={},
            status=UploadStatus.PENDING,
            created_at=old_time,
            updated_at=old_time
        )

        self.assertFalse(recent_job.is_expired(24))
        self.assertTrue(old_job.is_expired(24))

class TestUploadQueue(unittest.TestCase):
    """Test cases for UploadQueue class"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.queue_dir = Path(self.temp_dir) / "upload_queue"
        self.queue = UploadQueue(self.queue_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)

    def test_queue_initialization(self):
        """Test queue initialization"""
        self.assertTrue(self.queue_dir.exists())
        self.assertTrue(self.queue.jobs_file.exists())
        self.assertIsInstance(self.queue._jobs, dict)
        self.assertEqual(len(self.queue._jobs), 0)

    def test_add_job(self):
        """Test adding a job to the queue"""
        job_id = self.queue.add_job(
            torrent_path=Path("/path/to/test.torrent"),
            trackers=["red", "ops"],
            metadata={"title": "Test Torrent"}
        )

        self.assertIsInstance(job_id, str)
        self.assertIn(job_id, self.queue._jobs)

        job = self.queue._jobs[job_id]
        self.assertEqual(job.torrent_path, "/path/to/test.torrent")
        self.assertEqual(job.trackers, ["red", "ops"])
        self.assertEqual(job.status, UploadStatus.PENDING)

    def test_get_job(self):
        """Test retrieving a job"""
        job_id = self.queue.add_job(
            torrent_path=Path("/path/to/test.torrent"),
            trackers=["red"],
            metadata={"title": "Test Torrent"}
        )

        job = self.queue.get_job(job_id)
        self.assertIsNotNone(job)
        if job is not None:
            self.assertEqual(job.job_id, job_id)

        # Test non-existent job
        nonexistent = self.queue.get_job("nonexistent")
        self.assertIsNone(nonexistent)

    def test_get_pending_jobs(self):
        """Test getting pending jobs"""
        # Add pending job
        job_id1 = self.queue.add_job(
            torrent_path=Path("/path/to/test1.torrent"),
            trackers=["red"],
            metadata={"title": "Test 1"}
        )

        # Add completed job
        job_id2 = self.queue.add_job(
            torrent_path=Path("/path/to/test2.torrent"),
            trackers=["red"],
            metadata={"title": "Test 2"}
        )
        self.queue.update_job_status(job_id2, UploadStatus.SUCCESS)

        pending_jobs = self.queue.get_pending_jobs()
        self.assertEqual(len(pending_jobs), 1)
        self.assertEqual(pending_jobs[0].job_id, job_id1)

    def test_get_failed_jobs(self):
        """Test getting failed jobs that can be retried"""
        # Add failed job with retries available
        job_id1 = self.queue.add_job(
            torrent_path=Path("/path/to/test1.torrent"),
            trackers=["red"],
            metadata={"title": "Test 1"}
        )
        self.queue.update_job_status(job_id1, UploadStatus.FAILED)

        # Add failed job with no retries left
        job_id2 = self.queue.add_job(
            torrent_path=Path("/path/to/test2.torrent"),
            trackers=["red"],
            metadata={"title": "Test 2"}
        )
        self.queue._jobs[job_id2].retry_count = 3  # Max retries
        self.queue.update_job_status(job_id2, UploadStatus.FAILED)

        failed_jobs = self.queue.get_failed_jobs()
        self.assertEqual(len(failed_jobs), 1)
        self.assertEqual(failed_jobs[0].job_id, job_id1)

    def test_update_job_status(self):
        """Test updating job status"""
        job_id = self.queue.add_job(
            torrent_path=Path("/path/to/test.torrent"),
            trackers=["red"],
            metadata={"title": "Test"}
        )

        self.queue.update_job_status(job_id, UploadStatus.UPLOADING, "Starting upload")
        job = self.queue.get_job(job_id)
        self.assertIsNotNone(job)
        if job is not None:
            self.assertEqual(job.status, UploadStatus.UPLOADING)
            self.assertEqual(job.error_message, "Starting upload")

    def test_mark_job_success(self):
        """Test marking job as successful"""
        job_id = self.queue.add_job(
            torrent_path=Path("/path/to/test.torrent"),
            trackers=["red", "ops"],
            metadata={"title": "Test"}
        )

        self.queue.mark_job_success(job_id, "red")
        job = self.queue.get_job(job_id)
        self.assertIsNotNone(job)
        if job is not None and job.results is not None:
            self.assertEqual(job.results["red"], True)
            self.assertEqual(job.status, UploadStatus.PENDING)  # Not complete yet

        self.queue.mark_job_success(job_id, "ops")
        job = self.queue.get_job(job_id)
        self.assertIsNotNone(job)
        if job is not None:
            self.assertEqual(job.status, UploadStatus.SUCCESS)  # Now complete

    def test_mark_job_failed(self):
        """Test marking job as failed"""
        job_id = self.queue.add_job(
            torrent_path=Path("/path/to/test.torrent"),
            trackers=["red"],
            metadata={"title": "Test"}
        )

        self.queue.mark_job_failed(job_id, "red", "Network error")
        job = self.queue.get_job(job_id)
        self.assertIsNotNone(job)
        if job is not None and job.results is not None:
            self.assertEqual(job.results["red"], False)
            self.assertEqual(job.error_message, "Network error")
            self.assertEqual(job.status, UploadStatus.FAILED)

    def test_retry_job(self):
        """Test retrying a job"""
        job_id = self.queue.add_job(
            torrent_path=Path("/path/to/test.torrent"),
            trackers=["red"],
            metadata={"title": "Test"}
        )

        # Mark as failed first
        self.queue.update_job_status(job_id, UploadStatus.FAILED)

        # Retry should succeed
        success = self.queue.retry_job(job_id)
        self.assertTrue(success)

        job = self.queue.get_job(job_id)
        self.assertIsNotNone(job)
        if job is not None:
            self.assertEqual(job.status, UploadStatus.RETRYING)
            self.assertEqual(job.retry_count, 1)

            # Retry should fail after max retries
            job.retry_count = 3
            success = self.queue.retry_job(job_id)
            self.assertFalse(success)

    def test_remove_job(self):
        """Test removing a job"""
        job_id = self.queue.add_job(
            torrent_path=Path("/path/to/test.torrent"),
            trackers=["red"],
            metadata={"title": "Test"}
        )

        self.assertIn(job_id, self.queue._jobs)
        success = self.queue.remove_job(job_id)
        self.assertTrue(success)
        self.assertNotIn(job_id, self.queue._jobs)

        # Try to remove non-existent job
        success = self.queue.remove_job("nonexistent")
        self.assertFalse(success)

    def test_cleanup_expired_jobs(self):
        """Test cleaning up expired jobs"""
        # Create a job with old timestamp
        old_time = datetime.now() - timedelta(hours=25)
        job_id = "old-job"
        job = UploadJob(
            job_id=job_id,
            torrent_path="/path/to/old.torrent",
            trackers=["red"],
            metadata={"title": "Old Job"},
            status=UploadStatus.PENDING,
            created_at=old_time,
            updated_at=old_time
        )
        self.queue._jobs[job_id] = job

        # Add a recent job
        recent_job_id = self.queue.add_job(
            torrent_path=Path("/path/to/recent.torrent"),
            trackers=["red"],
            metadata={"title": "Recent Job"}
        )

        # Cleanup should remove old job but keep recent one
        self.queue.cleanup_expired_jobs(24)
        self.assertNotIn(job_id, self.queue._jobs)
        self.assertIn(recent_job_id, self.queue._jobs)

    def test_get_queue_stats(self):
        """Test getting queue statistics"""
        # Add jobs in different states
        job1 = self.queue.add_job(Path("/path/to/test1.torrent"), ["red"], {})
        job2 = self.queue.add_job(Path("/path/to/test2.torrent"), ["red"], {})
        job3 = self.queue.add_job(Path("/path/to/test3.torrent"), ["red"], {})

        self.queue.update_job_status(job1, UploadStatus.SUCCESS)
        self.queue.update_job_status(job2, UploadStatus.FAILED)
        # job3 remains PENDING

        stats = self.queue.get_queue_stats()
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['pending'], 1)
        self.assertEqual(stats['success'], 1)
        self.assertEqual(stats['failed'], 1)
        self.assertEqual(stats['uploading'], 0)

    def test_persistence(self):
        """Test job persistence across queue instances"""
        # Add a job to first queue instance
        job_id = self.queue.add_job(
            torrent_path=Path("/path/to/test.torrent"),
            trackers=["red"],
            metadata={"title": "Test"}
        )

        # Create new queue instance (simulating restart)
        new_queue = UploadQueue(self.queue_dir)

        # Job should still exist
        job = new_queue.get_job(job_id)
        self.assertIsNotNone(job)
        if job is not None:
            self.assertEqual(job.job_id, job_id)

if __name__ == '__main__':
    unittest.main()
