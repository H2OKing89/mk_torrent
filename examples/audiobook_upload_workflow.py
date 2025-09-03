#!/usr/bin/env python3
"""
Audiobook Upload Workflow for RED Tracker

This script demonstrates a complete workflow for uploading an audiobook torrent
to the RED (Redacted) private tracker after it's been created and added to qBittorrent.

Workflow Steps:
1. Torrent created and added to qBittorrent
2. Extract or prompt for audiobook metadata
3. Prepare RED upload request with proper parameters
4. Authenticate using secure API key
5. Upload torrent to RED with dryrun first for testing
6. Handle response and provide feedback

Usage:
    python audiobook_upload_workflow.py /path/to/torrent.torrent

Requirements:
- RED API key stored securely via secure_credentials.py
- requests library
- Torrent file ready for upload
"""

import sys
import os
import requests
from typing import Dict, List, Optional, Any

# Import from our secure credentials system
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from core_secure_credentials import get_secure_tracker_credential

# RED API Configuration
RED_BASE_URL = "https://redacted.sh"
UPLOAD_ENDPOINT = f"{RED_BASE_URL}/ajax.php?action=upload"

# Audiobook category mapping
AUDIOBOOK_CATEGORY = 3  # RED category for Audiobooks


class AudiobookUploader:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": api_key, "User-Agent": "mk_torrent/1.0"}
        )

    def upload_audiobook(
        self,
        torrent_path: str,
        title: str,
        artists: List[str],
        year: int,
        releasetype: int = 1,  # Default to Album
        format_type: str = "MP3",
        bitrate: str = "320",
        media: str = "CD",
        tags: str = "audiobook",
        description: str = "",
        other_bitrate: Optional[str] = None,
        dryrun: bool = True,
    ) -> Dict:
        """
        Upload an audiobook torrent to RED tracker.

        Args:
            torrent_path: Path to the .torrent file
            title: Audiobook title
            artists: List of artist names (authors/narrators)
            year: Release year
            releasetype: Release type ID (1=Album, etc.)
            format_type: Audio format (MP3, FLAC, etc.)
            bitrate: Bitrate (192, 320, Lossless, etc.)
            media: Media type (CD, WEB, etc.)
            tags: Comma-separated tags
            description: Album description
            other_bitrate: Optional custom bitrate when bitrate='Other' (max 9 chars)
            dryrun: If True, test upload without actually uploading

        Returns:
            Dict containing response from RED API
        """

        if not os.path.exists(torrent_path):
            raise FileNotFoundError(f"Torrent file not found: {torrent_path}")

        # Prepare multipart form data
        files = {
            "file_input": (
                "torrent.torrent",
                open(torrent_path, "rb"),
                "application/x-bittorrent",
            )
        }

        # Prepare form data with audiobook-specific parameters
        data = {
            "type": AUDIOBOOK_CATEGORY,  # Audiobooks category
            "title": title,
            "year": str(year),
            "releasetype": str(releasetype),
            "format": format_type,
            "bitrate": bitrate,
            "media": media,
            "tags": tags,
            "album_desc": description,
        }

        # Add other_bitrate if specified (for bitrate='Other')
        if other_bitrate:
            data["other_bitrate"] = other_bitrate

        # Add artists array (match curl example format)
        for i, artist in enumerate(artists):
            data[f"artists[{i}]"] = artist
            data[f"importance[{i}]"] = "1"  # Main artist

        # Add dryrun parameter for testing
        if dryrun:
            data["dryrun"] = "1"

        print("🚀 Uploading audiobook to RED...")
        print(f"   Title: {title}")
        print(f"   Artists: {', '.join(artists)}")
        print(f"   Year: {year}")
        print(f"   Dry Run: {'Yes' if dryrun else 'No'}")
        print(f"   Torrent: {os.path.basename(torrent_path)}")

        print("📤 Request details:")
        print(f"   URL: {UPLOAD_ENDPOINT}")
        print(f"   Headers: {dict(self.session.headers)}")
        print(f"   Files: {list(files.keys())}")
        print(f"   Data keys: {list(data.keys())}")
        print(f"   Data: {data}")

        try:
            response = self.session.post(UPLOAD_ENDPOINT, files=files, data=data)
            print(f"📥 Response status: {response.status_code}")
            print(f"📥 Response headers: {dict(response.headers)}")
            print(f"📥 Response content: {response.text[:500]}...")
            response.raise_for_status()

            result = response.json()

            # Handle both regular success and dry run success
            if result.get("status") in ["success", "dry run success"]:
                print("✅ Upload successful!")
                if dryrun:
                    print("   (This was a dry run - no actual upload occurred)")
                    print(
                        f"   📊 Validation results: {result.get('data', {}).get('torrent', 'N/A')}"
                    )
                return result
            else:
                error_msg = result.get("error", result.get("data", "Unknown error"))
                print(f"❌ Upload failed: {error_msg}")
                return result

        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            # Print more details for debugging
            if hasattr(e, "response") and e.response:
                print(f"   Status Code: {e.response.status_code}")
                print(f"   Response: {e.response.text[:500]}...")
            return {"status": "error", "error": str(e)}
        except ValueError as e:
            print(f"❌ JSON parsing error: {e}")
            return {"status": "error", "error": str(e)}


def main():
    """Main workflow execution"""
    if len(sys.argv) != 2:
        print("Usage: python audiobook_upload_workflow.py <torrent_file>")
        sys.exit(1)

    torrent_path = sys.argv[1]

    # Get RED API key from secure storage
    try:
        api_key = get_secure_tracker_credential("red", "api_key")
        if not api_key:
            print(
                "❌ RED API key not found. Please store it using secure_credentials.py"
            )
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error retrieving API key: {e}")
        sys.exit(1)

    # Initialize uploader
    uploader = AudiobookUploader(api_key)

    # Example audiobook metadata (in real usage, this could be extracted from torrent or prompted)
    # For demonstration, using sample data
    sample_metadata: Dict[str, Any] = {
        "title": "The Great Gatsby",
        "artists": ["F. Scott Fitzgerald", "Narrated by Jake Gyllenhaal"],
        "year": 2023,
        "format_type": "MP3",
        "bitrate": "320",
        "media": "WEB",
        "tags": "audiobook, fiction, classic",
        "description": "A classic American novel narrated by Jake Gyllenhaal",
    }

    print("📖 Audiobook Upload Workflow")
    print("=" * 50)

    # First, do a dry run
    print("\n🔍 Performing dry run test...")
    result = uploader.upload_audiobook(
        torrent_path=torrent_path,
        title=sample_metadata["title"],
        artists=sample_metadata["artists"],
        year=sample_metadata["year"],
        format_type=sample_metadata["format_type"],
        bitrate=sample_metadata["bitrate"],
        media=sample_metadata["media"],
        tags=sample_metadata["tags"],
        description=sample_metadata["description"],
        dryrun=True,
    )

    if result.get("status") in ["success", "dry run success"]:
        print("\n✅ Dry run successful! Ready for real upload.")
        print("   📊 RED validation passed - all metadata accepted!")
        print("\nTo perform actual upload, call with dryrun=False:")
        print("   uploader.upload_audiobook(torrent_path, ..., dryrun=False)")

        # Uncomment below for actual upload (after testing)
        # print("\n🚀 Performing actual upload...")
        # result = uploader.upload_audiobook(
        #     torrent_path=torrent_path,
        #     **sample_metadata,
        #     dryrun=False
        # )
    else:
        print("\n❌ Dry run failed. Please check the error and try again.")
        print(f"Error: {result.get('error', result.get('data', 'Unknown'))}")


if __name__ == "__main__":
    main()
