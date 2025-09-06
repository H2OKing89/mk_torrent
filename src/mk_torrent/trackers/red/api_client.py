"""
RED API client for dry run testing.

Simple client to test RED tracker upload forms using the dry run functionality.
This allows testing the complete pipeline without actually uploading torrents.
"""

import logging
from typing import Any, Optional

import httpx
from pydantic import BaseModel

from .upload_spec import REDUploadSpec, REDFormAdapter

logger = logging.getLogger(__name__)


class REDResponse(BaseModel):
    """Response from RED API."""

    success: bool
    error: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    status_code: int


class REDUploadResult(BaseModel):
    """Result from RED API upload attempt."""

    success: bool
    error: Optional[str] = None
    data: Optional[dict[str, Any]] = None


class REDAPIClient:
    """RED tracker API client for dry run upload testing."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://redacted.sh"  # Fixed URL from documentation
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self) -> bool:
        """Test connection to RED API."""
        try:
            logger.info("Testing RED API connection...")
            # Use Authorization header as per documentation
            headers = {"Authorization": self.api_key}
            response = self.client.get(
                f"{self.base_url}/ajax.php?action=index", headers=headers
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def dry_run_upload(
        self, upload_spec: REDUploadSpec, torrent_file_path: str | None = None
    ) -> REDUploadResult:
        """Perform a dry run upload to RED API."""
        try:
            logger.info("Validating form data...")
            form_adapter = REDFormAdapter()
            form_data = form_adapter.convert_to_form_data(upload_spec)

            # Add auth key to form data as per documentation
            form_data["auth"] = self.api_key
            # Add dryrun parameter
            form_data["dryrun"] = "1"

            logger.info("Performing dry run upload...")
            logger.info(f"Calling RED API upload.audiobooks for: {upload_spec.title}")
            logger.info(f"Form data fields: {list(form_data.keys())}")
            logger.info(
                f"Form data preview: {dict(list(form_data.items())[:8])}"
            )  # Show more fields including bitrate

            # Use correct endpoint from documentation
            url = f"{self.base_url}/ajax.php?action=upload"

            # Use Authorization header as per documentation
            headers = {"Authorization": self.api_key}

            # Handle torrent file upload if provided
            files = None
            if torrent_file_path:
                import os

                if os.path.exists(torrent_file_path):
                    # Read file and create proper multipart file structure
                    with open(torrent_file_path, "rb") as f:
                        file_content = f.read()

                    # Create proper file tuple for httpx: (filename, content, content_type)
                    filename = os.path.basename(torrent_file_path)
                    files = {
                        "file_input": (
                            filename,
                            file_content,
                            "application/x-bittorrent",
                        )
                    }
                    logger.info(
                        f"Including torrent file: {torrent_file_path} ({len(file_content)} bytes)"
                    )
                else:
                    logger.warning(f"Torrent file not found: {torrent_file_path}")

            if files:
                # Use multipart form data when file is included
                response = self.client.post(
                    url, data=form_data, files=files, headers=headers
                )
            else:
                # Use regular form data for dry run without file
                response = self.client.post(url, data=form_data, headers=headers)

            logger.info(f"RED API response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                try:
                    response_data = response.json()
                    logger.info(f"Response JSON: {response_data}")

                    if response_data.get("status") == "success":
                        return REDUploadResult(
                            success=True,
                            data=response_data.get("response", response_data),
                        )
                    elif response_data.get("status") in [
                        "dry run failure",
                        "dry run success",
                    ]:
                        # Both are expected for dry runs - treat as success
                        logger.info(
                            f"Dry run completed successfully with status: {response_data.get('status')}"
                        )
                        return REDUploadResult(
                            success=True,
                            data=response_data.get("data", response_data),
                        )
                    else:
                        # Error response
                        error_msg = response_data.get(
                            "error", response_data.get("data", "Unknown RED API error")
                        )
                        logger.error(f"RED API error: {error_msg}")
                        return REDUploadResult(
                            success=False,
                            error=str(error_msg),
                        )

                except Exception:
                    # Not JSON response - likely HTML error page
                    response_text = response.text[:1000]
                    logger.warning(f"Non-JSON response: {response_text}")
                    return REDUploadResult(
                        success=False,
                        error=f"Non-JSON response: {response_text}",
                    )
            else:
                # HTTP error
                logger.error(f"HTTP error: {response.status_code}")
                return REDUploadResult(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text[:500]}",
                )

        except Exception as e:
            logger.error(f"Dry run upload failed: {e}")
            return REDUploadResult(
                success=False,
                error=f"Upload failed: {str(e)}",
            )

    def real_upload(
        self, upload_spec: REDUploadSpec, torrent_file_path: str
    ) -> REDUploadResult:
        """Perform a REAL upload to RED API (no dry run)."""
        try:
            logger.info("Validating form data...")
            form_adapter = REDFormAdapter()
            form_data = form_adapter.convert_to_form_data(upload_spec)

            # Add auth key to form data as per documentation
            form_data["auth"] = self.api_key
            # NO dryrun parameter for real upload

            logger.info("Performing REAL upload...")
            logger.info(f"Calling RED API upload.audiobooks for: {upload_spec.title}")
            logger.info(f"Form data fields: {list(form_data.keys())}")
            logger.info(f"Form data preview: {dict(list(form_data.items())[:8])}")

            # Use correct endpoint from documentation
            url = f"{self.base_url}/ajax.php?action=upload"

            # Use Authorization header as per documentation
            headers = {"Authorization": self.api_key}

            # Handle torrent file upload - REQUIRED for real uploads
            if not torrent_file_path:
                logger.error("Torrent file is required for real uploads")
                return REDUploadResult(
                    success=False, error="Torrent file is required for real uploads"
                )

            import os

            if not os.path.exists(torrent_file_path):
                logger.error(f"Torrent file not found: {torrent_file_path}")
                return REDUploadResult(
                    success=False, error=f"Torrent file not found: {torrent_file_path}"
                )

            # Read file and create proper multipart file structure
            with open(torrent_file_path, "rb") as f:
                file_content = f.read()

            # Create proper file tuple for httpx: (filename, content, content_type)
            filename = os.path.basename(torrent_file_path)
            files = {"file_input": (filename, file_content, "application/x-bittorrent")}
            logger.info(
                f"Including torrent file: {torrent_file_path} ({len(file_content)} bytes)"
            )

            # Use multipart form data with file
            response = self.client.post(
                url, data=form_data, files=files, headers=headers
            )

            logger.info(f"RED API response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                try:
                    response_data = response.json()
                    logger.info(f"Response JSON: {response_data}")

                    if response_data.get("status") == "success":
                        # Real upload successful!
                        torrent_id = response_data.get("response", {}).get("torrentid")
                        group_id = response_data.get("response", {}).get("groupid")
                        logger.info(
                            f"✅ REAL UPLOAD SUCCESSFUL! Torrent ID: {torrent_id}, Group ID: {group_id}"
                        )
                        return REDUploadResult(
                            success=True,
                            data=response_data.get("response", response_data),
                        )
                    else:
                        # Error response
                        error_msg = response_data.get(
                            "error", response_data.get("data", "Unknown RED API error")
                        )
                        logger.error(f"RED API error: {error_msg}")
                        return REDUploadResult(
                            success=False,
                            error=str(error_msg),
                        )

                except Exception:
                    # Not JSON response - likely HTML error page
                    response_text = response.text[:1000]
                    logger.warning(f"Non-JSON response: {response_text}")
                    return REDUploadResult(
                        success=False,
                        error=f"Non-JSON response: {response_text}",
                    )
            else:
                # HTTP error
                logger.error(f"HTTP error: {response.status_code}")
                return REDUploadResult(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text[:500]}",
                )

        except Exception as e:
            logger.error(f"Real upload failed: {e}")
            return REDUploadResult(
                success=False,
                error=f"Upload failed: {str(e)}",
            )

    def validate_form_data(self, form_data: dict[str, str]) -> dict[str, Any]:
        """
        Validate form data against RED requirements.

        Args:
            form_data: Form data to validate

        Returns:
            Validation results with warnings and errors
        """
        validation = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "field_count": len(form_data),
        }

        # Required fields for RED uploads
        required_fields = [
            "title",
            "artists[]",
            "year",
            "type",
            "format",
            "bitrate",
            "releasetype",
            "album_desc",
        ]

        # Check required fields
        for field in required_fields:
            if field not in form_data:
                validation["errors"].append(f"Missing required field: {field}")
                validation["valid"] = False
            elif not form_data[field]:
                validation["errors"].append(f"Empty value for required field: {field}")
                validation["valid"] = False

        # Validate field formats
        if "type" in form_data:
            try:
                type_id = int(form_data["type"])
                if type_id not in [1, 2, 3, 4, 5, 6, 7, 8]:
                    validation["warnings"].append(f"Unusual category ID: {type_id}")
            except ValueError:
                validation["errors"].append("Category type must be numeric")
                validation["valid"] = False

        if "year" in form_data:
            try:
                year = int(form_data["year"])
                if year < 1800 or year > 2030:
                    validation["warnings"].append(f"Unusual year: {year}")
            except ValueError:
                validation["errors"].append("Year must be numeric")
                validation["valid"] = False

        # Check description length
        if "album_desc" in form_data:
            desc_length = len(form_data["album_desc"])
            if desc_length < 50:
                validation["warnings"].append(f"Short description: {desc_length} chars")
            elif desc_length > 10000:
                validation["warnings"].append(f"Long description: {desc_length} chars")

        return validation

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def run_red_api_integration_test(
    upload_spec: REDUploadSpec, api_key: str, torrent_file_path: str | None = None
) -> dict[str, Any]:
    """
    Run complete RED API integration test with dry run.

    Args:
        upload_spec: Upload specification to test
        api_key: RED API key

    Returns:
        Comprehensive test results
    """
    results = {
        "connection_test": None,
        "form_validation": None,
        "dry_run_upload": None,
        "overall_success": False,
    }

    with REDAPIClient(api_key) as client:
        # Test 1: Connection
        logger.info("Testing RED API connection...")
        connection_success = client.test_connection()
        results["connection_test"] = {"success": connection_success}

        if not connection_success:
            logger.error("Connection test failed, skipping other tests")
            return results

        # Test 2: Form validation
        logger.info("Validating form data...")
        form_adapter = REDFormAdapter()
        form_data = form_adapter.convert_to_form_data(upload_spec)
        results["form_validation"] = client.validate_form_data(form_data)

        if not results["form_validation"]["valid"]:
            logger.warning("Form validation has errors")

        # Test 3: Dry run upload
        logger.info("Performing dry run upload...")
        results["dry_run_upload"] = client.dry_run_upload(
            upload_spec, torrent_file_path
        )

        # Overall success assessment
        results["overall_success"] = (
            results["connection_test"]["success"]
            and results["form_validation"]["valid"]
            and results["dry_run_upload"].success
        )

    return results
