#!/usr/bin/env python3
"""
Real-World Audiobook Processing and Upload Workflow

This script creates a complete pipeline for:
1. Creating torrents for audiobooks
2. Extracting metadata from M4B files using Mutagen
3. Parsing additional metadata from filenames
4. Testing RED upload with proper metadata fields

Usage:
    python real_world_audiobook_workflow.py
"""

import os
import sys
import re
import hashlib
import bencodepy
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass

from rich.console import Console

console = Console()

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

# Add the project root to the path to import from examples
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from mutagen.mp4 import MP4
    from mutagen._file import File
    from ..core.secure_credentials import get_secure_tracker_credential
    from examples.audiobook_upload_workflow import AudiobookUploader
except ImportError:
    console.print(
        "[red]❌ Mutagen not installed. Please run: pip install mutagen[/red]"
    )
    sys.exit(1)


@dataclass
class AudiobookMetadata:
    """Structured audiobook metadata extracted from files and filenames"""

    # From filename parsing
    series_title: str
    volume: str
    year: str
    author: str
    asin: str
    uploader: str

    # From M4B metadata (Mutagen)
    title: str
    narrator: str
    album: str
    description: str
    genre: str
    length_seconds: float
    bitrate: int
    format_type: str

    # Additional metadata
    cover_art_size: int = 0
    publisher: str = ""
    copyright_info: str = ""


class AudiobookProcessor:
    """Complete audiobook processing pipeline with RED compatibility checks"""

    # RED filename limits (conservative estimates based on actual RED feedback)
    MAX_FILENAME_LENGTH = 120  # Individual filenames
    MAX_PATH_LENGTH = 150  # Total path including directory

    def __init__(self):
        self.base_paths = [
            "/mnt/user/data/downloads/torrents/qbittorrent/seedvault/audiobooks/How a Realist Hero Rebuilt the Kingdom - vol_01 (2023) (Dojyomaru) {ASIN.B0C34GQRYZ} [H2OKing]/",
            "/mnt/user/data/downloads/torrents/qbittorrent/seedvault/audiobooks/How a Realist Hero Rebuilt the Kingdom - vol_02 (2023) (Dojyomaru) {ASIN.B0C5S3W7MV} [H2OKing]/",
            "/mnt/user/data/downloads/torrents/qbittorrent/seedvault/audiobooks/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]/",
            "/mnt/user/data/downloads/torrents/qbittorrent/seedvault/audiobooks/How a Realist Hero Rebuilt the Kingdom - vol_04 (2023) (Dojyomaru) {ASIN.B0CC6F7RJQ} [H2OKing]/",
        ]

    def validate_and_fix_filenames(self, directory_path: str) -> bool:
        """Validate filename lengths and suggest fixes for RED compatibility"""

        directory_name = os.path.basename(directory_path)
        files = list(Path(directory_path).glob("*"))

        console.print(
            "[cyan]🔍 Validating filename lengths for RED compatibility...[/cyan]"
        )
        console.print(
            f"[dim]   Directory: {len(directory_name)} chars: {directory_name}[/dim]"
        )

        # Check directory name length
        if len(directory_name) > self.MAX_FILENAME_LENGTH:
            console.print(
                f"[red]❌ Directory name too long: {len(directory_name)} chars (max {self.MAX_FILENAME_LENGTH})[/red]"
            )
            suggested = self.suggest_red_compatible_name(directory_path)
            console.print(f"[blue]💡 Suggested name: {suggested}[/blue]")
            return False

        # Check individual file lengths and full paths
        issues_found = False
        for file_path in files:
            if file_path.is_file():
                filename = file_path.name
                full_path = f"{directory_name}/{filename}"

                console.print(f"[dim]   File: {len(filename)} chars: {filename}[/dim]")
                console.print(f"[dim]   Full path: {len(full_path)} chars[/dim]")

                if len(filename) > self.MAX_FILENAME_LENGTH:
                    console.print(
                        f"[red]❌ Filename too long: {len(filename)} chars (max {self.MAX_FILENAME_LENGTH})[/red]"
                    )
                    issues_found = True

                if len(full_path) > self.MAX_PATH_LENGTH:
                    console.print(
                        f"[red]❌ Full path too long: {len(full_path)} chars (max {self.MAX_PATH_LENGTH})[/red]"
                    )
                    console.print(f"[dim]   Path: {full_path}[/dim]")
                    issues_found = True

        if issues_found:
            console.print(
                f"[blue]💡 Solution: Rename files to be under {self.MAX_FILENAME_LENGTH} characters each[/blue]"
            )
            console.print(
                "[blue]💡 Remove release group tags like '[H2OKing]' and shorten ASIN info[/blue]"
            )
            suggested = self.suggest_red_compatible_name(directory_path)
            console.print(f"[blue]💡 Suggested directory name: {suggested}[/blue]")
            return False

        console.print("[green]✅ All filenames are RED-compatible[/green]")
        return True

    def suggest_red_compatible_name(self, directory_path: str) -> str:
        """Suggest a RED-compatible directory name by removing common issues"""

        directory_name = os.path.basename(directory_path)

        # Remove release group tags like [H2OKing]
        shortened = re.sub(r"\s*\[.*?\]\s*", "", directory_name)

        # Remove excessive metadata like full ASIN format
        shortened = re.sub(r"\s*\{ASIN\.[^}]+\}", "", shortened)

        # Trim to safe length
        if len(shortened) > self.MAX_FILENAME_LENGTH:
            shortened = shortened[: self.MAX_FILENAME_LENGTH - 3] + "..."

        return shortened.strip()

    def parse_filename_metadata(self, directory_path: str) -> Dict[str, str]:
        """Extract metadata from directory/filename structure"""
        dir_name = os.path.basename(directory_path.rstrip("/"))

        # Try compliant pattern first: "Series - vol_XX  {ASIN.XXXXXXXX} [Uploader]" (note double space)
        compliant_pattern = r"^(.+?) - (vol_\d+)\s+\{ASIN\.([A-Z0-9]+)\} \[(.+?)\]$"
        match = re.match(compliant_pattern, dir_name)

        if match:
            return {
                "series_title": match.group(1),
                "volume": match.group(2),
                "year": "2023",  # Default year since removed for compliance
                "author": "Dojyomaru",  # Default author since removed for compliance
                "asin": match.group(3),
                "uploader": match.group(4),
            }

        # Fallback to original pattern: "Series - vol_XX (YEAR) (Author) {ASIN.XXXXXXXX} [Uploader]"
        original_pattern = (
            r"^(.+?) - (vol_\d+) \((\d{4})\) \((.+?)\) \{ASIN\.([A-Z0-9]+)\} \[(.+?)\]$"
        )
        match = re.match(original_pattern, dir_name)

        if match:
            return {
                "series_title": match.group(1),
                "volume": match.group(2),
                "year": match.group(3),
                "author": match.group(4),
                "asin": match.group(5),
                "uploader": match.group(6),
            }
        else:
            console.print(f"[yellow]⚠️  Could not parse filename: {dir_name}[/yellow]")
            console.print("[dim]    Trying fallback patterns...[/dim]")
            return {}

    def extract_m4b_metadata(self, m4b_path: str) -> Dict[str, Any]:
        """Extract metadata from M4B file using Mutagen"""
        if not os.path.exists(m4b_path):
            return {}

        try:
            audio = File(m4b_path)
            if not isinstance(audio, MP4):
                console.print(
                    f"[yellow]⚠️  Not a valid MP4/M4B file: {m4b_path}[/yellow]"
                )
                return {}

            tags = audio.tags or {}
            info = audio.info

            metadata = {
                "title": self._get_tag_value(tags, "©nam", "Unknown Title"),
                "narrator": self._get_tag_value(tags, "©wrt", "Unknown Narrator"),
                "album": self._get_tag_value(tags, "©alb", "Unknown Album"),
                "description": self._get_tag_value(tags, "desc", ""),
                "genre": self._get_tag_value(tags, "©gen", "Audiobook"),
                "publisher": self._get_tag_value(
                    tags, "----:com.apple.iTunes:publisher", ""
                ),
                "copyright_info": self._get_tag_value(tags, "cprt", ""),
                "length_seconds": getattr(info, "length", 0),
                "bitrate": getattr(info, "bitrate", 0),
                "format_type": "M4B",
                "cover_art_size": 0,
            }

            # Handle cover art
            if "covr" in tags and tags["covr"]:
                cover = tags["covr"][0]
                metadata["cover_art_size"] = len(cover)

            return metadata

        except Exception as e:
            console.print(f"[red]❌ Error reading M4B metadata: {e}[/red]")
            return {}

    def _get_tag_value(self, tags: Any, key: str, default: str = "") -> str:
        """Helper to extract tag value safely"""
        if key in tags and tags[key]:
            value = tags[key][0] if isinstance(tags[key], list) else tags[key]
            return str(value) if value else default
        return default

    def create_torrent_for_audiobook(self, directory_path: str) -> Optional[str]:
        """Create a torrent file for an audiobook directory with RED compatibility checks"""
        if not os.path.exists(directory_path):
            console.print(f"[red]❌ Directory not found: {directory_path}[/red]")
            return None

        # SAFETY CHECK: Validate filename lengths before creating torrent
        if not self.validate_and_fix_filenames(directory_path):
            console.print(
                "[red]❌ Filename validation failed - cannot upload to RED[/red]"
            )
            console.print(
                f"[blue]💡 Please rename files to be under {self.MAX_FILENAME_LENGTH} characters[/blue]"
            )
            return None

        try:
            # Get all files in directory (excluding unwanted files)
            files_to_include = []
            exclude_patterns = [".DS_Store", "Thumbs.db", "*.tmp"]

            for file_path in sorted(Path(directory_path).iterdir()):
                if file_path.is_file():
                    # Include M4B, CUE, JPG files but exclude temp/system files
                    if not any(
                        file_path.name.endswith(pattern.replace("*", ""))
                        for pattern in exclude_patterns
                    ):
                        files_to_include.append(file_path)

            if not files_to_include:
                print(f"❌ No files found in: {directory_path}")
                return None

            print(f"📁 Creating torrent for: {os.path.basename(directory_path)}")
            print(f"   Files to include: {len(files_to_include)}")

            # Calculate total size and create file info
            files_info = []
            total_size = 0
            piece_length = 1048576  # 1MB pieces for audiobooks
            all_pieces = b""

            for file_path in files_to_include:
                file_size = file_path.stat().st_size
                total_size += file_size

                print(f"   - {file_path.name} ({file_size:,} bytes)")

                # Read file and calculate piece hashes
                with open(file_path, "rb") as f:
                    while True:
                        piece = f.read(piece_length)
                        if not piece:
                            break
                        hasher = hashlib.sha1()
                        hasher.update(piece)
                        all_pieces += hasher.digest()

                # Add file info
                files_info.append(
                    {b"path": [file_path.name.encode()], b"length": file_size}
                )

            # Create torrent info
            torrent_name = os.path.basename(directory_path)
            info = {
                b"name": torrent_name.encode(),
                b"files": files_info,
                b"piece length": piece_length,
                b"pieces": all_pieces,
            }

            # Create full torrent structure
            torrent = {
                b"info": info,
                b"announce": b"https://flacsfor.me/announce",  # RED announce URL
                b"created by": b"mk_torrent real-world workflow",
                b"comment": b"Created for RED upload testing",
            }

            # Write torrent file
            torrent_filename = f"{torrent_name}.torrent"
            torrent_path = os.path.join(
                "/mnt/cache/scripts/mk_torrent/test_audiobooks/", torrent_filename
            )
            os.makedirs("/mnt/cache/scripts/mk_torrent/test_audiobooks/", exist_ok=True)

            with open(torrent_path, "wb") as f:
                f.write(bencodepy.encode(torrent))

            print(f"✅ Torrent created: {torrent_path}")
            print(f"   Total size: {total_size:,} bytes")
            return torrent_path

        except Exception as e:
            print(f"❌ Error creating torrent: {e}")
            return None

    def combine_metadata(self, directory_path: str) -> Optional[AudiobookMetadata]:
        """Combine filename and M4B metadata into structured format"""

        # Parse filename metadata
        filename_meta = self.parse_filename_metadata(directory_path)
        if not filename_meta:
            return None

        # Find M4B file
        m4b_files = list(Path(directory_path).glob("*.m4b"))
        if not m4b_files:
            print(f"❌ No M4B file found in: {directory_path}")
            return None

        m4b_path = str(m4b_files[0])
        m4b_meta = self.extract_m4b_metadata(m4b_path)

        # Combine metadata
        try:
            metadata = AudiobookMetadata(
                # From filename
                series_title=filename_meta["series_title"],
                volume=filename_meta["volume"],
                year=filename_meta["year"],
                author=filename_meta["author"],
                asin=filename_meta["asin"],
                uploader=filename_meta["uploader"],
                # From M4B
                title=m4b_meta.get("title", "Unknown Title"),
                narrator=m4b_meta.get("narrator", "Unknown Narrator"),
                album=m4b_meta.get("album", "Unknown Album"),
                description=m4b_meta.get("description", ""),
                genre=m4b_meta.get("genre", "Audiobook"),
                length_seconds=m4b_meta.get("length_seconds", 0),
                bitrate=m4b_meta.get("bitrate", 0),
                format_type=m4b_meta.get("format_type", "M4B"),
                # Additional
                cover_art_size=m4b_meta.get("cover_art_size", 0),
                publisher=m4b_meta.get("publisher", ""),
                copyright_info=m4b_meta.get("copyright_info", ""),
            )

            return metadata

        except Exception as e:
            print(f"❌ Error combining metadata: {e}")
            return None

    def format_red_metadata(self, metadata: AudiobookMetadata) -> Dict[str, Any]:
        """Format metadata for RED upload"""

        # Format title for RED (Author - Series - Volume)
        red_title = f"{metadata.author} – {metadata.series_title} – {metadata.volume}"

        # Format artists (author and narrator)
        artists = [metadata.author]
        if metadata.narrator and metadata.narrator != metadata.author:
            artists.append(f"Narrated by {metadata.narrator}")

        # Format description for RED
        length_hours = int(metadata.length_seconds // 3600)
        length_minutes = int((metadata.length_seconds % 3600) // 60)
        length_str = f"{length_hours:02d}:{length_minutes:02d}:00"

        description = f"""[b]Author:[/b] {metadata.author}
[b]Narrator:[/b] {metadata.narrator}
[b]Series:[/b] {metadata.series_title}
[b]Volume:[/b] {metadata.volume}
[b]Year:[/b] {metadata.year}
[b]Length:[/b] {length_str}
[b]Publisher:[/b] {metadata.publisher or 'Unknown'}
[b]ASIN:[/b] {metadata.asin}

{metadata.description}"""

        # Format tags
        tags = "audiobook, series, fantasy, english"
        if "vol_" in metadata.volume:
            tags += ", volume"

        # Calculate appropriate bitrate for RED
        # M4B files are typically VBR AAC, calculate average kbps
        avg_bitrate_kbps = int(metadata.bitrate / 1000) if metadata.bitrate else 128

        # Choose RED bitrate format based on actual bitrate
        if avg_bitrate_kbps >= 250:
            red_bitrate = "Lossless"
            red_format = "AAC"
        elif avg_bitrate_kbps >= 200:
            red_bitrate = "V0 (VBR)"
            red_format = "AAC"
        elif avg_bitrate_kbps >= 150:
            red_bitrate = "V1 (VBR)"
            red_format = "AAC"
        else:
            red_bitrate = "Other"
            red_format = "AAC"

        result = {
            "title": red_title,
            "artists": artists,
            "year": int(metadata.year),
            "releasetype": 1,  # Album
            "format_type": red_format,
            "bitrate": red_bitrate,
            "media": "WEB",  # Digital download
            "tags": tags,
            "description": description,
        }

        # Add other_bitrate if using "Other"
        if red_bitrate == "Other":
            result["other_bitrate"] = f"{avg_bitrate_kbps}k VBR"

        return result

    def test_upload_workflow(self, audiobook_path: str):
        """Complete workflow: create torrent, extract metadata, test upload"""

        print(f"\n🎯 Processing: {os.path.basename(audiobook_path)}")
        print("=" * 80)

        # Step 1: Create torrent
        print("\n📦 Step 1: Creating torrent...")
        torrent_path = self.create_torrent_for_audiobook(audiobook_path)
        if not torrent_path:
            print("❌ Failed to create torrent")
            return False

        # Step 2: Extract and combine metadata
        print("\n📋 Step 2: Extracting metadata...")
        metadata = self.combine_metadata(audiobook_path)
        if not metadata:
            print("❌ Failed to extract metadata")
            return False

        print(f"   ✅ Series: {metadata.series_title}")
        print(f"   ✅ Volume: {metadata.volume}")
        print(f"   ✅ Author: {metadata.author}")
        print(f"   ✅ Narrator: {metadata.narrator}")
        print(f"   ✅ Year: {metadata.year}")
        print(f"   ✅ Length: {metadata.length_seconds/3600:.1f} hours")
        print(f"   ✅ ASIN: {metadata.asin}")

        # Step 3: Format for RED
        print("\n🔄 Step 3: Formatting for RED...")
        red_metadata = self.format_red_metadata(metadata)

        print(f"   ✅ RED Title: {red_metadata['title']}")
        print(f"   ✅ RED Artists: {red_metadata['artists']}")
        print(f"   ✅ RED Format: {red_metadata['format_type']}")
        print(f"   ✅ RED Tags: {red_metadata['tags']}")

        # Step 4: Test RED upload (dry run)
        print("\n🚀 Step 4: Testing RED upload (dry run)...")

        try:
            api_key = get_secure_tracker_credential("red", "api_key")
            if not api_key:
                print("❌ RED API key not found")
                return False

            uploader = AudiobookUploader(api_key)
            result = uploader.upload_audiobook(
                torrent_path=torrent_path, **red_metadata, dryrun=True
            )

            if result.get("status") in ["success", "dry run success"]:
                print("✅ RED upload test successful!")
                print("   📊 All metadata validated by RED")
                return True
            else:
                print(
                    f"❌ RED upload test failed: {result.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            print(f"❌ Upload test error: {e}")
            return False


def main():
    """Run the complete real-world audiobook workflow"""

    print("🎵 Real-World Audiobook Processing & Upload Workflow")
    print("=" * 60)
    print("This workflow will:")
    print("1. Create torrents for audiobooks")
    print("2. Extract metadata using Mutagen")
    print("3. Test RED upload with proper formatting")
    print()

    processor = AudiobookProcessor()

    # Test each audiobook
    success_count = 0
    total_count = len(processor.base_paths)

    for audiobook_path in processor.base_paths:
        if processor.test_upload_workflow(audiobook_path):
            success_count += 1

        print("\n" + "─" * 80)

    # Summary
    print("\n📊 Workflow Summary:")
    print(f"   Total audiobooks processed: {total_count}")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {total_count - success_count}")

    if success_count == total_count:
        print("\n🎉 All audiobooks processed successfully!")
        print("   Ready for real RED uploads (change dryrun=False)")
    else:
        print(f"\n⚠️  {total_count - success_count} audiobooks need attention")


if __name__ == "__main__":
    main()
