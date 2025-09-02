#!/usr/bin/env python3
"""
Path-Length Compliance Tool for RED Tracker (≤ 150 chars)

This tool implements a preserve-first workflow that applies minimal, ordered edits
to make audiobook folder/file paths compliant with RED's length limits.

Priority Order (0 = most important to keep):
0: ASIN
1: title  
2: volume
3: group
4: author
5: year

Edit Order (least important first): year → author → group → volume → title → ASIN
"""

import re
import os
import json
import argparse
import unicodedata
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ComplianceConfig:
    """Configuration for path compliance"""
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
                "How a Realist Hero Rebuilt the Kingdom": "Realist Hero Rebuilt Kingdom"
            }
        if self.punct_strip is None:
            self.punct_strip = [":", ";", ",", "!", "?"]

@dataclass
class ComplianceLog:
    """Log entry for a micro-step edit"""
    scope: str          # "file" or "folder"
    target: str         # filename or folder name
    priority: int       # 0-5
    step: str          # description of action
    before_len: int    # path length before
    after_len: int     # path length after
    saved_chars: int   # characters saved
    compliant: bool    # whether this made it compliant
    before_text: str   # text before change
    after_text: str    # text after change

class PathComplianceTool:
    """Tool to make folder/file paths compliant with RED's length limits"""
    
    def __init__(self, config: ComplianceConfig):
        self.config = config
        self.log: List[ComplianceLog] = []
    
    def normalize_text(self, text: str) -> Tuple[str, List[str]]:
        """Apply normalization transforms (idempotent)"""
        changes = []
        original = text
        
        # Fix duplicate ASIN prefixes: {ASIN.ASIN.X} → {ASIN.X}
        pattern = r'\{ASIN\.(?:ASIN\.)?([A-Z0-9]+)\}'
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
    
    def get_full_path_length(self, folder: str, filename: str) -> int:
        """Calculate full path length: folder + "/" + filename"""
        return len(f"{folder}/{filename}")
    
    def is_compliant(self, folder: str, filenames: List[str]) -> bool:
        """Check if all paths are compliant"""
        return all(
            self.get_full_path_length(folder, fn) <= self.config.max_full_path 
            for fn in filenames
        )
    
    def log_step(self, scope: str, target: str, priority: int, step: str, 
                 before_text: str, after_text: str, folder: str, filename: Optional[str] = None):
        """Log a micro-step edit"""
        if filename:
            before_len = self.get_full_path_length(folder, before_text if scope == "file" else filename)
            after_len = self.get_full_path_length(after_text if scope == "folder" else folder, 
                                                after_text if scope == "file" else filename)
        else:
            # Folder-only change
            test_file = "test.m4b"  # Use a test filename for length calculation
            before_len = self.get_full_path_length(before_text, test_file)
            after_len = self.get_full_path_length(after_text, test_file)
        
        entry = ComplianceLog(
            scope=scope,
            target=target,
            priority=priority,
            step=step,
            before_len=before_len,
            after_len=after_len,
            saved_chars=before_len - after_len,
            compliant=after_len <= self.config.max_full_path,
            before_text=before_text,
            after_text=after_text
        )
        self.log.append(entry)
    
    def remove_year_pattern(self, text: str) -> str:
        """Remove (YYYY) pattern"""
        return re.sub(r'\s*\(\d{4}\)', '', text)
    
    def remove_rightmost_author_parens(self, text: str) -> str:
        """Remove rightmost parentheses group that is not a year"""
        # Find all parentheses groups
        parens_matches = list(re.finditer(r'\([^()]+\)', text))
        if not parens_matches:
            return text
        
        # Check from right to left for non-year group
        for match in reversed(parens_matches):
            group_text = match.group(0)
            if not re.match(r'\(\d{4}\)', group_text):
                # Remove this group
                return text[:match.start()] + text[match.end():]
        
        return text
    
    def remove_group_tag(self, text: str) -> str:
        """Remove trailing [Group] tag"""
        return re.sub(r'\s*\[[^\]]+\]\s*$', '', text)
    
    def compact_volume_stepwise(self, text: str, step: int) -> str:
        """Compact volume token in steps"""
        if step == 1:  # vol_01 → v01
            return re.sub(r'\bvol_(\d{1,2})\b', r'v\1', text)
        elif step == 2:  # v01 → 01
            return re.sub(r'\bv(\d{1,2})\b', r'\1', text)
        elif step == 3:  # 01 → 1 (last resort)
            return re.sub(r'\b0+(\d{1,2})\b', r'\1', text)
        return text
    
    def shorten_title_stepwise(self, text: str, step: int, reserve_chars: int = 0) -> str:
        """Apply title shortening in steps"""
        if step == 1:  # Remove leading articles
            return re.sub(r'^(the|a|an|how a|how to)\s+', '', text, flags=re.IGNORECASE)
        elif step == 2:  # Remove soft punctuation
            for punct in self.config.punct_strip or []:
                text = text.replace(punct, '')
            return re.sub(r'\s+', ' ', text).strip()
        elif step == 3:  # Apply alias mapping
            for long_title, short_title in (self.config.title_alias_map or {}).items():
                if long_title.lower() in text.lower():
                    return text.replace(long_title, short_title)
            return text
        elif step == 4:  # Last resort truncation
            if len(text) <= reserve_chars:
                return text
            max_len = len(text) - reserve_chars
            if max_len < self.config.title_min_after:
                return text  # Don't truncate too much
            
            # Find word boundary
            truncated = text[:max_len]
            last_space = truncated.rfind(' ')
            if last_space > self.config.title_min_after:
                truncated = truncated[:last_space]
            
            return truncated + self.config.title_ellipsis
        return text
    
    def shorten_asin_stepwise(self, text: str, step: int) -> str:
        """Shorten ASIN in steps"""
        if step == 1:  # {ASIN.B0C34GQRYZ} → {B0C34GQRYZ}
            return re.sub(r'\{ASIN\.([A-Z0-9]+)\}', r'{\1}', text)
        elif step == 2:  # Remove {ASIN} entirely
            return re.sub(r'\s*\{[A-Z0-9]+\}', '', text)
        return text
    
    def shorten_filename_stepwise(self, folder: str, filename: str) -> str:
        """Apply filename shortening following priority order 5→0"""
        current_filename = filename
        
        # Check if already compliant
        if self.get_full_path_length(folder, current_filename) <= self.config.max_full_path:
            return current_filename
        
        # Priority 5: Year
        new_filename = self.remove_year_pattern(current_filename)
        if new_filename != current_filename:
            self.log_step("file", filename, 5, "remove_year_from_filename", 
                         current_filename, new_filename, folder, current_filename)
            current_filename = new_filename
            if self.get_full_path_length(folder, current_filename) <= self.config.max_full_path:
                return current_filename
        
        # Priority 4: Author
        new_filename = self.remove_rightmost_author_parens(current_filename)
        if new_filename != current_filename:
            self.log_step("file", filename, 4, "remove_author_from_filename",
                         current_filename, new_filename, folder, current_filename)
            current_filename = new_filename
            if self.get_full_path_length(folder, current_filename) <= self.config.max_full_path:
                return current_filename
        
        # Priority 3: Group
        new_filename = self.remove_group_tag(current_filename)
        if new_filename != current_filename:
            self.log_step("file", filename, 3, "remove_group_from_filename",
                         current_filename, new_filename, folder, current_filename)
            current_filename = new_filename
            if self.get_full_path_length(folder, current_filename) <= self.config.max_full_path:
                return current_filename
        
        # Priority 2: Volume (stepwise)
        for vol_step in [1, 2, 3]:
            new_filename = self.compact_volume_stepwise(current_filename, vol_step)
            if new_filename != current_filename:
                step_name = ["", "vol_to_v", "v_to_number", "remove_zero_pad"][vol_step]
                self.log_step("file", filename, 2, f"compact_volume_{step_name}",
                             current_filename, new_filename, folder, current_filename)
                current_filename = new_filename
                if self.get_full_path_length(folder, current_filename) <= self.config.max_full_path:
                    return current_filename
        
        # Priority 1: Title (stepwise)
        for title_step in [1, 2, 3, 4]:
            new_filename = self.shorten_title_stepwise(current_filename, title_step, 
                                                     self.config.title_reserve_chars)
            if new_filename != current_filename:
                step_name = ["", "remove_articles", "remove_punctuation", "apply_aliases", "truncate"][title_step]
                self.log_step("file", filename, 1, f"shorten_title_{step_name}",
                             current_filename, new_filename, folder, current_filename)
                current_filename = new_filename
                if self.get_full_path_length(folder, current_filename) <= self.config.max_full_path:
                    return current_filename
        
        # Priority 0: ASIN (last resort)
        for asin_step in [1, 2]:
            new_filename = self.shorten_asin_stepwise(current_filename, asin_step)
            if new_filename != current_filename:
                step_name = ["", "shorten_asin", "remove_asin"][asin_step]
                self.log_step("file", filename, 0, f"asin_{step_name}",
                             current_filename, new_filename, folder, current_filename)
                current_filename = new_filename
                if self.get_full_path_length(folder, current_filename) <= self.config.max_full_path:
                    return current_filename
        
        return current_filename
    
    def shorten_folder_stepwise(self, folder: str, filenames: List[str]) -> str:
        """Apply folder shortening following priority order 5→0"""
        current_folder = folder
        
        # Priority 5: Year
        new_folder = self.remove_year_pattern(current_folder)
        if new_folder != current_folder:
            self.log_step("folder", folder, 5, "remove_year_from_folder",
                         current_folder, new_folder, current_folder)
            current_folder = new_folder
            if self.is_compliant(current_folder, filenames):
                return current_folder
        
        # Priority 4: Author
        new_folder = self.remove_rightmost_author_parens(current_folder)
        if new_folder != current_folder:
            self.log_step("folder", folder, 4, "remove_author_from_folder",
                         current_folder, new_folder, current_folder)
            current_folder = new_folder
            if self.is_compliant(current_folder, filenames):
                return current_folder
        
        # Priority 3: Group
        new_folder = self.remove_group_tag(current_folder)
        if new_folder != current_folder:
            self.log_step("folder", folder, 3, "remove_group_from_folder",
                         current_folder, new_folder, current_folder)
            current_folder = new_folder
            if self.is_compliant(current_folder, filenames):
                return current_folder
        
        # Priority 2: Volume (stepwise)
        for vol_step in [1, 2, 3]:
            new_folder = self.compact_volume_stepwise(current_folder, vol_step)
            if new_folder != current_folder:
                step_name = ["", "vol_to_v", "v_to_number", "remove_zero_pad"][vol_step]
                self.log_step("folder", folder, 2, f"compact_volume_{step_name}",
                             current_folder, new_folder, current_folder)
                current_folder = new_folder
                if self.is_compliant(current_folder, filenames):
                    return current_folder
        
        # Priority 1: Title (stepwise)
        for title_step in [1, 2, 3, 4]:
            new_folder = self.shorten_title_stepwise(current_folder, title_step, 0)
            if new_folder != current_folder:
                step_name = ["", "remove_articles", "remove_punctuation", "apply_aliases", "truncate"][title_step]
                self.log_step("folder", folder, 1, f"shorten_title_{step_name}",
                             current_folder, new_folder, current_folder)
                current_folder = new_folder
                if self.is_compliant(current_folder, filenames):
                    return current_folder
        
        # Priority 0: ASIN (last resort)
        for asin_step in [1, 2]:
            new_folder = self.shorten_asin_stepwise(current_folder, asin_step)
            if new_folder != current_folder:
                step_name = ["", "shorten_asin", "remove_asin"][asin_step]
                self.log_step("folder", folder, 0, f"asin_{step_name}",
                             current_folder, new_folder, current_folder)
                current_folder = new_folder
                if self.is_compliant(current_folder, filenames):
                    return current_folder
        
        return current_folder
    
    def shorten_filename_conservative(self, folder: str, filename: str) -> str:
        """Apply only priorities 5-2 (year, author, group, volume) to filename"""
        current_filename = filename
        
        # Priority 5: Remove year
        current_filename = re.sub(r'\s*\(\d{4}\)', '', current_filename).strip()
        
        # Priority 4: Remove author (rightmost non-year parens)
        parens_matches = list(re.finditer(r'\([^()]+\)', current_filename))
        if parens_matches:
            last_match = parens_matches[-1]
            if not re.match(r'\(\d{4}\)', last_match.group()):
                current_filename = current_filename[:last_match.start()] + current_filename[last_match.end():]
                current_filename = re.sub(r'\s+', ' ', current_filename).strip()
        
        # Priority 3: Remove group (rare in filenames)
        current_filename = re.sub(r'\s*\[[^\]]+\]\s*$', '', current_filename)
        
        # Priority 2: Compact volume
        current_filename = re.sub(r'\bvol_(\d{1,2})\b', r'v\1', current_filename)
        current_filename = re.sub(r'\bv(\d{1,2})\b', r'\1', current_filename)
        current_filename = re.sub(r'\b0?(\d{1,2})\b', r'\1', current_filename)
        
        return current_filename
    
    def apply_title_edits_aggressive(self, folder: str, filename: str) -> str:
        """Apply aggressive title edits as last resort"""
        current_filename = filename
        
        # Priority 1: Title modifications
        # Drop leading articles
        current_filename = re.sub(r'^(?i)(the|a|an|how a|how to)\s+', '', current_filename)
        
        # Remove soft punctuation
        for punct in [':', ';', ',', '!', '?']:
            current_filename = current_filename.replace(punct, '')
        current_filename = re.sub(r'\s+', ' ', current_filename).strip()
        
        # Check if we need truncation
        full_path = f"{folder}/{current_filename}"
        if len(full_path) <= self.config.max_full_path:
            return current_filename
            
        # Title truncation as absolute last resort
        name, ext = os.path.splitext(current_filename)
        available_chars = self.config.max_full_path - len(folder) - 1 - len(ext) - 1  # -1 for '/', -1 for ellipsis
        
        if available_chars > 10:  # Minimum sensible title
            current_filename = name[:available_chars] + "…" + ext
        
        return current_filename

    def ensure_compliance(self, folder: str, filenames: List[str]) -> Tuple[str, List[str], List[ComplianceLog]]:
        """
        Main compliance function following the preserve-first workflow with proper handoff logic.
        
        Strategy per spec:
        1. Normalize everything first  
        2. Apply conservative file edits (priorities 5-2) first
        3. If close to compliance, try folder edits before aggressive title truncation
        4. Only do title truncation as absolute last resort
        """
        log_entries = []
        
        # Step 1: Normalize inputs
        normalized_folder, folder_changes = self.normalize_text(folder)
        normalized_files = []
        for fn in filenames:
            norm_fn, file_changes = self.normalize_text(fn)
            normalized_files.append(norm_fn)
        
        # Step 2: Conservative file edits (priorities 5-2: year, author, group, volume)
        files_after_conservative = []
        for filename in normalized_files:
            original_path = f"{normalized_folder}/{filename}"
            conservative_filename = self.shorten_filename_conservative(normalized_folder, filename)
            conservative_path = f"{normalized_folder}/{conservative_filename}"
            files_after_conservative.append(conservative_filename)
            
            log_entries.append(ComplianceLog(
                scope="file",
                target=filename,
                priority=5,  # conservative edits span priorities 5-2
                step="conservative_file_edit",
                before_len=len(original_path),
                after_len=len(conservative_path),
                saved_chars=len(original_path) - len(conservative_path),
                compliant=len(conservative_path) <= self.config.max_full_path,
                before_text=original_path,
                after_text=conservative_path
            ))
        
        # Check current status
        max_overage = max(0, max(len(f"{normalized_folder}/{file}") - self.config.max_full_path for file in files_after_conservative))
        
        if max_overage == 0:
            # Already compliant after conservative file edits
            log_entries.append(ComplianceLog(
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
            return normalized_folder, files_after_conservative, log_entries
            
        elif max_overage <= 20:
            # Close enough - try folder edits before aggressive title truncation
            log_entries.append(ComplianceLog(
                scope="strategy",
                target="decision",
                priority=0,
                step="handoff_to_folder",
                before_len=max_overage,
                after_len=0,
                saved_chars=0,
                compliant=False,
                before_text=f"Max overage: {max_overage} chars",
                after_text="Trying folder edits before title truncation"
            ))
            
            # Apply folder edits stepwise
            folder_after_edits = self.shorten_folder_stepwise(normalized_folder, files_after_conservative)
            
            # Check if folder edits resolved it
            max_overage_after_folder = max(0, max(len(f"{folder_after_edits}/{file}") - self.config.max_full_path for file in files_after_conservative))
            
            if max_overage_after_folder == 0:
                log_entries.append(ComplianceLog(
                    scope="folder",
                    target="folder_edits",
                    priority=5,
                    step="folder_success",
                    before_len=len(normalized_folder),
                    after_len=len(folder_after_edits),
                    saved_chars=len(normalized_folder) - len(folder_after_edits),
                    compliant=True,
                    before_text=f"Folder: {normalized_folder}",
                    after_text=f"Folder: {folder_after_edits}"
                ))
                return folder_after_edits, files_after_conservative, log_entries
            else:
                # Still need aggressive title edits as last resort
                final_files = []
                for filename in files_after_conservative:
                    if len(f"{folder_after_edits}/{filename}") <= self.config.max_full_path:
                        final_files.append(filename)
                    else:
                        original_path = f"{folder_after_edits}/{filename}"
                        aggressive_filename = self.apply_title_edits_aggressive(folder_after_edits, filename)
                        aggressive_path = f"{folder_after_edits}/{aggressive_filename}"
                        final_files.append(aggressive_filename)
                        
                        log_entries.append(ComplianceLog(
                            scope="file",
                            target=filename,
                            priority=1,
                            step="aggressive_title_edit",
                            before_len=len(original_path),
                            after_len=len(aggressive_path),
                            saved_chars=len(original_path) - len(aggressive_path),
                            compliant=len(aggressive_path) <= self.config.max_full_path,
                            before_text=original_path,
                            after_text=aggressive_path
                        ))
                
                return folder_after_edits, final_files, log_entries
        else:
            # Way over limit - proceed with full aggressive edits
            log_entries.append(ComplianceLog(
                scope="strategy",
                target="decision",
                priority=0,
                step="full_aggressive",
                before_len=max_overage,
                after_len=0,
                saved_chars=0,
                compliant=False,
                before_text=f"Max overage: {max_overage} chars - too far over for folder-first approach",
                after_text="Applying full aggressive file edits"
            ))
            
            aggressive_files = []
            for filename in normalized_files:
                # Apply full stepwise reduction (5→0)
                aggressive_filename = self.shorten_filename_stepwise(normalized_folder, filename)
                aggressive_files.append(aggressive_filename)
            
            return normalized_folder, aggressive_files, log_entries
        
        return current_folder, final_files, self.log


def main():
    parser = argparse.ArgumentParser(description="RED Path-Length Compliance Tool")
    parser.add_argument("--folder", required=True, help="Folder name to check/fix")
    parser.add_argument("--files", nargs="+", required=True, help="List of filenames")
    parser.add_argument("--max-length", type=int, default=150, help="Maximum path length")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument("--log-json", help="Save detailed log to JSON file")
    
    args = parser.parse_args()
    
    # Create config
    config = ComplianceConfig(
        max_full_path=args.max_length,
        dry_run=not args.apply,
        apply=args.apply
    )
    
    # Create tool and run compliance check
    tool = PathComplianceTool(config)
    
    print(f"🔍 Path-Length Compliance Tool (RED ≤ {config.max_full_path} chars)")
    print("=" * 70)
    print(f"Mode: {'APPLY CHANGES' if config.apply else 'DRY-RUN'}")
    print()
    
    # Show original lengths
    print("📊 Original Paths:")
    for filename in args.files:
        path_len = tool.get_full_path_length(args.folder, filename)
        status = "✅" if path_len <= config.max_full_path else "❌"
        print(f"   {status} {path_len:3d} chars: {args.folder}/{filename}")
    print()
    
    # Run compliance
    new_folder, new_files, log_entries = tool.ensure_compliance(args.folder, args.files)
    
    # Show results
    print("📊 Compliant Paths:")
    all_compliant = True
    for filename in new_files:
        path_len = tool.get_full_path_length(new_folder, filename)
        status = "✅" if path_len <= config.max_full_path else "❌"
        if path_len > config.max_full_path:
            all_compliant = False
        print(f"   {status} {path_len:3d} chars: {new_folder}/{filename}")
    print()
    
    # Show edit log
    if log_entries:
        print("📝 Edit Log (Priority Order: Year→Author→Group→Volume→Title→ASIN):")
        for entry in log_entries:
            print(f"   {entry.scope.upper()} Priority {entry.priority}: {entry.step}")
            print(f"      Before: {entry.before_text}")
            print(f"      After:  {entry.after_text}")
            print(f"      Saved: {entry.saved_chars} chars ({entry.before_len}→{entry.after_len})")
            print()
    
    # Summary
    if all_compliant:
        print("🎉 All paths are now compliant!")
    else:
        print("⚠️  Some paths still exceed length limit")
    
    # Save log if requested
    if args.log_json:
        log_data = [
            {
                "scope": entry.scope,
                "target": entry.target,
                "priority": entry.priority,
                "step": entry.step,
                "before_len": entry.before_len,
                "after_len": entry.after_len,
                "saved_chars": entry.saved_chars,
                "compliant": entry.compliant,
                "before_text": entry.before_text,
                "after_text": entry.after_text
            }
            for entry in log_entries
        ]
        
        with open(args.log_json, 'w') as f:
            json.dump(log_data, f, indent=2)
        print(f"📄 Detailed log saved to: {args.log_json}")


if __name__ == "__main__":
    main()
