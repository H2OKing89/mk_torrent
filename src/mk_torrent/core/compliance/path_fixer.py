"""
Path fixing/renaming logic for different trackers
Integrates existing RED compliance functionality
"""

import re
import shutil
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import logging

from .path_validator import PathValidator, PathRule

logger = logging.getLogger(__name__)

@dataclass
class ComplianceConfig:
    """Configuration for path compliance fixing"""
    max_full_path: int = 150
    file_first: bool = True
    priority_order_keep: Optional[List[int]] = None  # [0, 1, 2, 3, 4, 5]
    edit_order_apply: Optional[List[int]] = None     # [5, 4, 3, 2, 1, 0]
    
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
    
    def __init__(self, tracker: str = 'red', config: Optional[ComplianceConfig] = None):
        self.tracker = tracker.lower()
        self.validator = PathValidator(tracker)
        
        # Use tracker-specific config
        if config is None:
            if tracker.lower() in ['red', 'redacted']:
                config = ComplianceConfig(max_full_path=150)
            elif tracker.lower() in ['mam', 'myanonamouse']:
                config = ComplianceConfig(max_full_path=255)
            else:
                config = ComplianceConfig(max_full_path=255)
        
        self.config = config
        self.log: List[ComplianceLog] = []
    
    def fix_path(self, folder_path: str, filenames: List[str], 
                 apply_changes: bool = False) -> Tuple[str, List[str], List[ComplianceLog]]:
        """Fix paths to meet compliance requirements"""
        self.log = []
        
        # Normalize inputs
        normalized_folder, changes = self.normalize_text(folder_path)
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
            self.log.append(ComplianceLog(
                scope="file",
                target=filename,
                priority=5,
                step="conservative_file_edit",
                before_len=len(original_path),
                after_len=len(conservative_path),
                saved_chars=len(original_path) - len(conservative_path),
                compliant=len(conservative_path) <= self.config.max_full_path,
                before_text=original_path,
                after_text=conservative_path
            ))
        
        # Check if conservative edits are sufficient
        max_overage = max(0, max(len(f"{normalized_folder}/{file}") - self.config.max_full_path 
                                for file in files_after_conservative))
        
        if max_overage == 0:
            # Already compliant with conservative edits
            self.log.append(ComplianceLog(
                scope="strategy",
                target="all_files",
                priority=0,
                step="early_success",
                before_len=0,
                after_len=0,
                saved_chars=0,
                compliant=True,
                before_text="",
                after_text="Conservative file edits achieved compliance"
            ))
            
            if apply_changes:
                success = self._apply_filesystem_renames(folder_path, filenames, 
                                                       normalized_folder, files_after_conservative)
                if not success:
                    logger.error("Failed to apply filesystem changes")
            
            return normalized_folder, files_after_conservative, self.log
        
        # Need more aggressive edits - apply folder + aggressive file edits
        self.log.append(ComplianceLog(
            scope="strategy",
            target="decision",
            priority=0,
            step="need_aggressive_edits",
            before_len=max_overage,
            after_len=0,
            saved_chars=0,
            compliant=False,
            before_text=f"Max overage: {max_overage} chars",
            after_text="Applying folder edits + aggressive file edits"
        ))
        
        # Apply folder edits stepwise
        folder_after_edits = self._shorten_folder_stepwise(normalized_folder, files_after_conservative)
        
        # Apply aggressive file edits to each file
        final_files = []
        for filename in files_after_conservative:
            # Apply full stepwise reduction (5→0) using the shortened folder
            aggressive_filename = self._shorten_filename_stepwise(folder_after_edits, filename)
            final_files.append(aggressive_filename)
            
            # Log the transformation
            original_path = f"{normalized_folder}/{filename}"
            final_path = f"{folder_after_edits}/{aggressive_filename}"
            self.log.append(ComplianceLog(
                scope="file",
                target=filename,
                priority=1,
                step="aggressive_file_edit",
                before_len=len(original_path),
                after_len=len(final_path),
                saved_chars=len(original_path) - len(final_path),
                compliant=len(final_path) <= self.config.max_full_path,
                before_text=original_path,
                after_text=final_path
            ))
        
        # Apply filesystem changes if requested
        if apply_changes:
            success = self._apply_filesystem_renames(folder_path, filenames, 
                                                   folder_after_edits, final_files)
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
        pattern = r'\{ASIN\.([A-Z0-9]+)\}'
        new_text = re.sub(pattern, r'{ASIN.\1}', text)
        if new_text != text:
            changes.append(f"Fixed ASIN format: {text} → {new_text}")
            text = new_text
        
        # Unicode NFC normalize
        if self.config.unicode_nfc:
            new_text = unicodedata.normalize('NFC', text)
            if new_text != text:
                changes.append("Applied Unicode NFC normalization")
                text = new_text
        
        # Normalize title/volume separator
        text = re.sub(r'\s*-\s*vol_(\d+)', r' - vol_\1', text)
        
        # Ensure zero-padded volumes
        if self.config.zero_pad_volume:
            text = re.sub(r'\bvol_(\d)\b', r'vol_0\1', text)
        
        # Collapse multiple spaces and trim
        if self.config.space_collapse:
            new_text = re.sub(r'\s+', ' ', text).strip()
            if new_text != text:
                changes.append("Collapsed spaces")
                text = new_text
        
        return text, changes
    
    def _apply_conservative_file_edits(self, filename: str) -> str:
        """Apply conservative file edits (year, author, group removal)"""
        current = filename
        
        # Priority 5: Year removal
        current = re.sub(r'\s*\(\d{4}\)', '', current)
        
        # Priority 4: Author removal
        current = self._remove_rightmost_author_parens(current)
        
        # Priority 3: Group removal
        current = re.sub(r'\s*\[[^\]]+\]', '', current)
        
        return current.strip()
    
    def _remove_rightmost_author_parens(self, text: str) -> str:
        """Remove rightmost parenthetical (likely author)"""
        # Find all parenthetical expressions
        parens = list(re.finditer(r'\([^)]+\)', text))
        if parens:
            # Remove the rightmost one
            last_paren = parens[-1]
            return text[:last_paren.start()].strip() + text[last_paren.end():]
        return text
    
    def _shorten_folder_stepwise(self, folder: str, filenames: List[str]) -> str:
        """Apply folder shortening following priority order 5→0"""
        current_folder = folder
        
        # Priority 5: Year
        new_folder = re.sub(r'\s*\(\d{4}\)', '', current_folder)
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
        new_folder = re.sub(r'\s*\[[^\]]+\]', '', current_folder)
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
        current_filename = re.sub(r'vol_(\d+)', r'\1', current_filename)
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
                title_part = re.split(r'\s*\{', current_filename)[0]
                extension = Path(current_filename).suffix
                
                # Calculate max title length
                other_parts_len = len(current_filename) - len(title_part)
                available_for_title = self.config.max_full_path - len(folder) - 1 - other_parts_len
                
                if available_for_title > self.config.title_min_after:
                    # Truncate title at word boundary
                    truncated = title_part[:available_for_title]
                    last_space = truncated.rfind(' ')
                    if last_space > self.config.title_min_after:
                        truncated = truncated[:last_space]
                    
                    # Reconstruct filename
                    new_filename = truncated + self.config.title_ellipsis + current_filename[len(title_part):]
                    current_filename = new_filename
        
        return current_filename
    
    def _apply_filesystem_renames(self, original_folder: str, original_files: List[str],
                                 new_folder: str, new_files: List[str]) -> bool:
        """Apply the calculated renames to the filesystem"""
        try:
            original_path = Path(original_folder)
            new_path = Path(new_folder)
            
            # If folder name changed, rename the folder
            if original_folder != new_folder and original_path.exists():
                logger.info(f"Renaming folder: {original_folder} → {new_folder}")
                if not self.config.dry_run:
                    shutil.move(str(original_path), str(new_path))
                else:
                    logger.info("DRY RUN: Would rename folder")
            
            # Rename files if needed
            base_path = new_path if new_path.exists() or not self.config.dry_run else original_path
            
            for orig_file, new_file in zip(original_files, new_files):
                if orig_file != new_file:
                    orig_file_path = base_path / orig_file
                    new_file_path = base_path / new_file
                    
                    if orig_file_path.exists():
                        logger.info(f"Renaming file: {orig_file} → {new_file}")
                        if not self.config.dry_run:
                            shutil.move(str(orig_file_path), str(new_file_path))
                        else:
                            logger.info("DRY RUN: Would rename file")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply filesystem renames: {e}")
            return False
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Get detailed compliance report from last fix operation"""
        return {
            'tracker': self.tracker,
            'max_length': self.config.max_full_path,
            'transformations': len(self.log),
            'log_entries': [
                {
                    'scope': log.scope,
                    'step': log.step,
                    'priority': log.priority,
                    'saved_chars': log.saved_chars,
                    'compliant': log.compliant,
                    'before': log.before_text,
                    'after': log.after_text
                }
                for log in self.log
            ]
        }
