"""
Path fixing/renaming logic for different trackers
Integrates existing RED compliance functionality
Includes hard link preservation to prevent breaking file links
"""

import re
import unicodedata
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass
import logging

from .path_validator import PathValidator

logger = logging.getLogger(__name__)

# Regex for replacing "Volume X" with "vol_X"
VOL_WORD_RE = re.compile(r"\bVolume\s+(\d+)\b", re.IGNORECASE)


@dataclass
class ComplianceConfig:
    """Configuration for path compliance fixing"""

    max_full_path: int = 180  # Updated to correct RED limit
    file_first: bool = True
    priority_order_keep: Optional[List[int]] = None  # [0, 1, 2, 3, 4, 5]
    edit_order_apply: Optional[List[int]] = None  # [5, 4, 3, 2, 1, 0]

    title_alias_map: Optional[Dict[str, str]] = None
    title_truncation_enable: bool = True
    title_reserve_chars: int = 12  # room for " - vNN" + extension
    title_ellipsis: str = "…"
    title_min_after: int = 12

    zero_pad_volume: bool = True
    unicode_nfc: bool = True
    punct_strip: Optional[List[str]] = None  # [":", ";", ",", "!", "?"]
    space_collapse: bool = True

    dry_run: bool = True
    apply: bool = False

    def __post_init__(self):
        if self.priority_order_keep is None:
            self.priority_order_keep = [0, 1, 2, 3, 4, 5]
        if self.edit_order_apply is None:
            self.edit_order_apply = [5, 4, 3, 2, 1, 0]
        if self.title_alias_map is None:
            self.title_alias_map = {
                "How a Realist Hero Rebuilt the Kingdom": "Realist Hero Rebuilt the Kingdom"
            }
        if self.punct_strip is None:
            self.punct_strip = [":", ";", ",", "!", "?"]


@dataclass
class ComplianceLog:
    """Log entry for compliance transformations"""

    scope: str  # "file", "folder", "strategy"
    target: str
    priority: int
    step: str
    before_len: int
    after_len: int
    saved_chars: int
    compliant: bool
    before_text: str
    after_text: str


class PathFixer:
    """Fixes paths to meet tracker compliance requirements"""

    def __init__(self, tracker: str = "red", config: Optional[ComplianceConfig] = None):
        self.tracker = tracker.lower()
        self.validator = PathValidator(tracker)

        # Use tracker-specific config
        if config is None:
            if tracker.lower() in ["red", "redacted"]:
                config = ComplianceConfig(
                    max_full_path=180
                )  # Updated to correct RED limit
            elif tracker.lower() in ["mam", "myanonamouse"]:
                config = ComplianceConfig(max_full_path=255)
            else:
                config = ComplianceConfig(max_full_path=255)

        self.config = config
        self.log: List[ComplianceLog] = []

    def fix_path(
        self, folder_abs_path: str, filenames: List[str], apply_changes: bool = False
    ) -> Tuple[str, List[str], List[ComplianceLog]]:
        """Fix paths to meet compliance requirements"""
        self.log = []
        abs_dir = Path(folder_abs_path).resolve()
        folder_basename = abs_dir.name

        # Normalize inputs - use basename for all compliance math
        normalized_folder, changes = self.normalize_text(folder_basename)
        normalized_files = []
        for filename in filenames:
            norm_file, _ = self.normalize_text(filename)
            normalized_files.append(norm_file)

        # Check if already compliant
        if self._is_compliant(normalized_folder, normalized_files):
            return normalized_folder, normalized_files, self.log

        # Apply conservative file edits first
        files_after_conservative = []
        for filename in normalized_files:
            conservative_file = self._apply_conservative_file_edits(filename)
            files_after_conservative.append(conservative_file)

            # Log the transformation
            original_path = f"{normalized_folder}/{filename}"
            conservative_path = f"{normalized_folder}/{conservative_file}"
            self.log.append(
                ComplianceLog(
                    scope="file",
                    target=filename,
                    priority=5,
                    step="conservative_file_edit",
                    before_len=len(original_path),
                    after_len=len(conservative_path),
                    saved_chars=len(original_path) - len(conservative_path),
                    compliant=len(conservative_path) <= self.config.max_full_path,
                    before_text=original_path,
                    after_text=conservative_path,
                )
            )

        # Check if conservative edits are sufficient
        max_overage = max(
            0,
            max(
                len(f"{normalized_folder}/{file}") - self.config.max_full_path
                for file in files_after_conservative
            ),
        )

        if max_overage == 0:
            # Already compliant with conservative edits
            self.log.append(
                ComplianceLog(
                    scope="strategy",
                    target="all_files",
                    priority=0,
                    step="early_success",
                    before_len=0,
                    after_len=0,
                    saved_chars=0,
                    compliant=True,
                    before_text="",
                    after_text="Conservative file edits achieved compliance",
                )
            )

            if apply_changes:
                success = self._apply_filesystem_renames(
                    abs_dir=abs_dir,
                    original_files=filenames,
                    new_folder_name=normalized_folder,
                    new_files=files_after_conservative,
                )
                if not success:
                    logger.error("Failed to apply filesystem changes")

            return normalized_folder, files_after_conservative, self.log

        # Need more aggressive edits - apply folder + aggressive file edits
        self.log.append(
            ComplianceLog(
                scope="strategy",
                target="decision",
                priority=0,
                step="need_aggressive_edits",
                before_len=max_overage,
                after_len=0,
                saved_chars=0,
                compliant=False,
                before_text=f"Max overage: {max_overage} chars",
                after_text="Applying folder edits + aggressive file edits",
            )
        )

        # Apply folder edits stepwise
        folder_after_edits = self._shorten_folder_stepwise(
            normalized_folder, files_after_conservative
        )

        # Apply aggressive file edits to each file
        final_files = []
        for filename in files_after_conservative:
            # Apply full stepwise reduction (5→0) using the shortened folder
            aggressive_filename = self._shorten_filename_stepwise(
                folder_after_edits, filename
            )
            final_files.append(aggressive_filename)

            # Log the transformation
            original_path = f"{normalized_folder}/{filename}"
            final_path = f"{folder_after_edits}/{aggressive_filename}"
            self.log.append(
                ComplianceLog(
                    scope="file",
                    target=filename,
                    priority=1,
                    step="aggressive_file_edit",
                    before_len=len(original_path),
                    after_len=len(final_path),
                    saved_chars=len(original_path) - len(final_path),
                    compliant=len(final_path) <= self.config.max_full_path,
                    before_text=original_path,
                    after_text=final_path,
                )
            )

        # Apply filesystem changes if requested
        if apply_changes:
            success = self._apply_filesystem_renames(
                abs_dir=abs_dir,
                original_files=filenames,
                new_folder_name=folder_after_edits,
                new_files=final_files,
            )
            if not success:
                logger.error("Failed to apply filesystem changes")

        return folder_after_edits, final_files, self.log

    def _is_compliant(self, folder: str, filenames: List[str]) -> bool:
        """Check if all paths are compliant"""
        return all(
            len(f"{folder}/{filename}") <= self.config.max_full_path
            for filename in filenames
        )

    def normalize_text(self, text: str) -> Tuple[str, List[str]]:
        """Normalize text for consistent processing"""
        changes = []

        # Fix ASIN format
        pattern = r"\{ASIN\.([A-Z0-9]+)\}"
        new_text = re.sub(pattern, r"{ASIN.\1}", text)
        if new_text != text:
            changes.append(f"Fixed ASIN format: {text} → {new_text}")
            text = new_text

        # Unicode NFC normalize
        if self.config.unicode_nfc:
            new_text = unicodedata.normalize("NFC", text)
            if new_text != text:
                changes.append("Applied Unicode NFC normalization")
                text = new_text

        # Normalize title/volume separator
        text = re.sub(r"\s*-\s*vol_(\d+)", r" - vol_\1", text)

        # Ensure zero-padded volumes
        if self.config.zero_pad_volume:
            text = re.sub(r"\bvol_(\d)\b", r"vol_0\1", text)

        # Strip configured punctuation
        if self.config.punct_strip:
            trans = str.maketrans({p: "" for p in self.config.punct_strip})
            newer = text.translate(trans)
            if newer != text:
                changes.append("Stripped configured punctuation")
                text = newer

        # Collapse multiple spaces and trim
        if self.config.space_collapse:
            new_text = re.sub(r"\s+", " ", text).strip()
            if new_text != text:
                changes.append("Collapsed spaces")
                text = new_text

        return text, changes

    def _strip_volume_word(self, text: str) -> str:
        """Replace 'Volume X' with 'vol_X'"""
        return VOL_WORD_RE.sub(r"vol_\1", text)

    def _apply_conservative_file_edits(self, filename: str) -> str:
        """Apply conservative file edits (volume word, year, author, group removal)"""
        current = filename

        # Strip Volume word first
        current = self._strip_volume_word(current)

        # Priority 5: Year removal
        current = re.sub(r"\s*\(\d{4}\)", "", current)

        # Priority 4: Author removal
        current = self._remove_rightmost_author_parens(current)

        # Priority 3: Group removal
        current = re.sub(r"\s*\[[^\]]+\]", "", current)

        return current.strip()

    def _remove_rightmost_author_parens(self, text: str) -> str:
        """Remove rightmost parenthetical (likely author)"""
        # Find all parenthetical expressions
        parens = list(re.finditer(r"\([^)]+\)", text))
        if parens:
            # Remove the rightmost one
            last_paren = parens[-1]
            return text[: last_paren.start()].strip() + text[last_paren.end() :]
        return text

    def _shorten_folder_stepwise(self, folder: str, filenames: List[str]) -> str:
        """Apply folder shortening following priority order 5→0"""
        current_folder = self._strip_volume_word(folder)  # NEW

        # Priority 5: Year
        new_folder = re.sub(r"\s*\(\d{4}\)", "", current_folder)
        if new_folder != current_folder:
            current_folder = new_folder
            if self._is_compliant(current_folder, filenames):
                return current_folder

        # Priority 4: Author
        new_folder = self._remove_rightmost_author_parens(current_folder)
        if new_folder != current_folder:
            current_folder = new_folder
            if self._is_compliant(current_folder, filenames):
                return current_folder

        # Priority 3: Group
        new_folder = re.sub(r"\s*\[[^\]]+\]", "", current_folder)
        if new_folder != current_folder:
            current_folder = new_folder.strip()
            if self._is_compliant(current_folder, filenames):
                return current_folder

        return current_folder

    def _shorten_filename_stepwise(self, folder: str, filename: str) -> str:
        """Apply filename shortening following priority order 5→0"""
        current_filename = filename

        # Check if already compliant
        if len(f"{folder}/{current_filename}") <= self.config.max_full_path:
            return current_filename

        # Priority 2: Volume compaction
        current_filename = re.sub(r"vol_(\d+)", r"\1", current_filename)
        if len(f"{folder}/{current_filename}") <= self.config.max_full_path:
            return current_filename

        # Priority 1: Title truncation (aggressive)
        if self.config.title_truncation_enable:
            # Calculate how much to truncate
            current_len = len(f"{folder}/{current_filename}")
            overage = current_len - self.config.max_full_path

            if overage > 0:
                # Find the title part (before any patterns like ASIN)
                # This is a simplified version - the full version would be more sophisticated
                title_part = re.split(r"\s*\{", current_filename)[0]
                _extension = Path(current_filename).suffix

                # Calculate max title length
                other_parts_len = len(current_filename) - len(title_part)
                available_for_title = (
                    self.config.max_full_path - len(folder) - 1 - other_parts_len
                )

                if available_for_title > self.config.title_min_after:
                    # Truncate title at word boundary
                    truncated = title_part[:available_for_title]
                    last_space = truncated.rfind(" ")
                    if last_space > self.config.title_min_after:
                        truncated = truncated[:last_space]

                    # Reconstruct filename
                    new_filename = (
                        truncated
                        + self.config.title_ellipsis
                        + current_filename[len(title_part) :]
                    )
                    current_filename = new_filename

        return current_filename

    def _detect_hard_links(
        self, folder_path: str, filenames: List[str]
    ) -> Dict[str, Set[str]]:
        """Detect hard links within the folder and external hard links

        Returns:
            Dictionary mapping inode numbers to sets of file paths that share that inode
        """
        hard_link_groups = {}
        folder = Path(folder_path)

        for filename in filenames:
            file_path = folder / filename
            if file_path.exists():
                try:
                    file_stat = file_path.stat()

                    # If this file has multiple links (hard links exist)
                    if file_stat.st_nlink > 1:
                        inode = file_stat.st_ino
                        if inode not in hard_link_groups:
                            hard_link_groups[inode] = set()
                        hard_link_groups[inode].add(str(file_path))

                except (OSError, FileNotFoundError) as e:
                    logger.warning(f"Could not stat file {file_path}: {e}")

        return hard_link_groups

    def _find_external_hard_links(
        self, file_path: Path, max_search_time: float = 0.5
    ) -> List[str]:
        """Find other hard links to this file outside the current directory

        This is a best-effort search with a time limit to prevent performance issues.
        If the search takes too long, it returns early with whatever it found.
        """
        external_links = []
        start_time = time.time()

        try:
            file_stat = file_path.stat()
            if file_stat.st_nlink <= 1:
                return external_links

            # Only search in immediate parent directory (very limited scope)
            search_path = file_path.parent.parent

            if search_path.exists() and search_path != file_path.parent:
                try:
                    # Check only first few sibling directories with time limit
                    for i, item in enumerate(search_path.iterdir()):
                        # Time limit check
                        if time.time() - start_time > max_search_time:
                            logger.debug(
                                f"External hard link search timed out after {max_search_time}s"
                            )
                            break

                        # Limit to first 10 directories to prevent excessive scanning
                        if i >= 10:
                            logger.debug(
                                "External hard link search limited to first 10 directories"
                            )
                            break

                        if item.is_dir() and item != file_path.parent:
                            try:
                                # Quick check of files in this directory
                                for other_file in item.iterdir():
                                    if other_file.is_file() and other_file != file_path:
                                        try:
                                            if (
                                                other_file.stat().st_ino
                                                == file_stat.st_ino
                                            ):
                                                external_links.append(str(other_file))
                                        except (OSError, FileNotFoundError):
                                            continue  # Skip files we can't stat
                            except (OSError, PermissionError):
                                continue  # Skip inaccessible directories
                except (OSError, PermissionError):
                    pass  # Skip inaccessible paths

        except (OSError, FileNotFoundError):
            pass

        return external_links

    def _validate_hard_links_preserved(
        self,
        original_folder: str,
        original_files: List[str],
        new_folder: str,
        new_files: List[str],
    ) -> bool:
        """Validate that hard links are preserved after renaming

        Returns True if all hard links remain intact, False otherwise.
        """
        if self.config.dry_run:
            return True  # Can't validate in dry-run mode

        # Check that renamed files still have the same hard link structure
        original_hard_links = self._detect_hard_links(original_folder, original_files)
        new_hard_links = self._detect_hard_links(new_folder, new_files)

        # Verify same number of hard link groups
        if len(original_hard_links) != len(new_hard_links):
            logger.error(
                "Hard link validation failed: Different number of hard link groups"
            )
            return False

        # For each original hard link group, verify a corresponding group exists
        for orig_inode, orig_paths in original_hard_links.items():
            found_corresponding_group = False

            for new_inode, new_paths in new_hard_links.items():
                if len(orig_paths) == len(new_paths):
                    # Check if the files are the same (just renamed)
                    orig_filenames = {Path(p).name for p in orig_paths}
                    new_filenames = {Path(p).name for p in new_paths}

                    # Map original to new filenames
                    filename_mapping = dict(zip(original_files, new_files))
                    expected_new_filenames = {
                        filename_mapping.get(fn, fn) for fn in orig_filenames
                    }

                    if expected_new_filenames == new_filenames:
                        found_corresponding_group = True
                        break

            if not found_corresponding_group:
                logger.error(
                    f"Hard link validation failed: Could not find corresponding group for inode {orig_inode}"
                )
                return False

        logger.info("✅ Hard link validation passed: All hard links preserved")
        return True

    def _safe_rename_with_hardlink_preservation(
        self, old_path: Path, new_path: Path
    ) -> bool:
        """Safely rename a file while preserving hard links

        Uses os.replace() for same-filesystem moves to preserve hard links.
        Issues warnings for cross-filesystem moves that would break hard links.
        """
        try:
            # Check if this file has hard links
            old_stat = old_path.stat()
            has_hard_links = old_stat.st_nlink > 1

            if has_hard_links:
                # Check if we're moving across filesystems
                old_device = old_stat.st_dev
                try:
                    # Ensure parent directory exists
                    new_parent = new_path.parent
                    new_parent.mkdir(parents=True, exist_ok=True)
                    new_device = new_parent.stat().st_dev
                    if old_device != new_device:
                        logger.error(
                            f"❌ Cross-filesystem move would break hard links: {old_path} -> {new_path}"
                        )
                        return False
                except FileNotFoundError:
                    # Parent directory doesn't exist yet, assume same filesystem
                    pass

            # Use os.replace() instead of os.rename() for atomic, overwrite-safe renames
            os.replace(str(old_path), str(new_path))

            if has_hard_links:
                # Verify hard links are still intact
                new_stat = new_path.stat()
                if (
                    new_stat.st_nlink == old_stat.st_nlink
                    and new_stat.st_ino == old_stat.st_ino
                ):
                    logger.info(
                        f"✅ Hard links preserved for {new_path.name} ({new_stat.st_nlink} links)"
                    )
                else:
                    logger.error(
                        f"❌ Hard link preservation failed for {new_path.name}"
                    )
                    return False

            return True

        except OSError as e:
            logger.error(f"Failed to rename {old_path} → {new_path}: {e}")
            return False

    def _apply_filesystem_renames(
        self,
        abs_dir: Path,
        original_files: List[str],
        new_folder_name: str,
        new_files: List[str],
    ) -> bool:
        """Apply the calculated renames to the filesystem with hard link preservation"""
        try:
            original_dir = abs_dir
            target_dir = (
                abs_dir
                if (abs_dir.name == new_folder_name)
                else abs_dir.parent / new_folder_name
            )

            # Rename the directory first (folders have no hard links, but keep it atomic)
            if original_dir != target_dir:
                if not self.config.dry_run:
                    os.replace(str(original_dir), str(target_dir))
                else:
                    logger.info(
                        f"DRY RUN: would rename dir {original_dir} -> {target_dir}"
                    )
            else:
                logger.debug("Folder name unchanged; skipping folder rename.")

            # We now operate inside target_dir
            base = target_dir

            # Two-phase rename to avoid collisions: temp -> final
            tmp_suffix = ".__tmp__ren__"
            # 1) plan -> detect collisions
            planned = {}
            seen_targets = set()
            for orig, new in zip(original_files, new_files):
                if orig == new:
                    continue
                src = base / orig
                dst = base / new

                # Handle case-only renames (macOS/Windows compatibility)
                if src.name.lower() == dst.name.lower() and src.name != dst.name:
                    # Case-only rename: use intermediate step
                    case_tmp = base / (dst.name + ".__case__tmp")
                    dst = case_tmp

                # dedupe if needed
                dedup_idx = 1
                stem, ext = dst.stem, dst.suffix
                while dst.name in seen_targets or dst.exists():
                    dst = base / f"{stem} ({dedup_idx}){ext}"
                    dedup_idx += 1
                seen_targets.add(dst.name)
                planned[src] = dst

            # 2) temp hop (avoid A->B while B->A race)
            temp_map = {}
            for src, dst in planned.items():
                if not src.exists():
                    logger.warning(f"Missing source {src}, skipping")
                    continue
                tmp = base / (src.name + tmp_suffix)
                if not self._safe_rename_with_hardlink_preservation(src, tmp):
                    return False
                temp_map[tmp] = dst

            # 3) final hop
            for tmp, dst in temp_map.items():
                if not self._safe_rename_with_hardlink_preservation(tmp, dst):
                    return False

            return True
        except Exception as e:
            logger.error(f"Failed to apply filesystem renames: {e}")
            return False

    def get_compliance_report(self) -> Dict[str, Any]:
        """Get detailed compliance report from last fix operation"""
        return {
            "tracker": self.tracker,
            "max_length": self.config.max_full_path,
            "transformations": len(self.log),
            "log_entries": [
                {
                    "scope": log.scope,
                    "step": log.step,
                    "priority": log.priority,
                    "saved_chars": log.saved_chars,
                    "compliant": log.compliant,
                    "before": log.before_text,
                    "after": log.after_text,
                }
                for log in self.log
            ],
        }
