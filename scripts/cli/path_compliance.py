#!/usr/bin/env python3
"""
RED Path Compliance Tool

Unified tool for RED tracker path compliance checking and automated fixing.
RED limit: 180 characters for folder + "/" + filename paths.

Modes:
- Single audiobook analysis and fixing
- Batch scanning of multiple audiobooks with filtering
- Dry-run preview (default) or actual renaming

Features:
- Selective targeting with include/exclude filters
- Protection for files intended for other trackers
- Priority-based preservation (ASIN > Title > Volume > Group > Author > Year)
- Detailed change logging with rollback support
- Batch script generation for targeted mass fixes
"""

import argparse
import json
import sys
import os
import stat
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mk_torrent.core.compliance.path_fixer import PathFixer, ComplianceConfig, ComplianceLog

console = Console()

# === SHARED UTILITIES ===

def detect_hard_links_in_directory(folder_path: Path) -> Tuple[int, Dict[int, List[str]]]:
    """Detect hard links in a directory
    
    Returns:
        Tuple of (total_hard_linked_files, hard_link_groups)
        where hard_link_groups maps inode -> list of file paths
    """
    hard_link_groups = {}
    
    if not folder_path.exists():
        return 0, {}
    
    for file_path in folder_path.iterdir():
        if file_path.is_file():
            try:
                file_stat = file_path.stat()
                if file_stat.st_nlink > 1:  # File has hard links
                    inode = file_stat.st_ino
                    if inode not in hard_link_groups:
                        hard_link_groups[inode] = []
                    hard_link_groups[inode].append(str(file_path))
            except (OSError, FileNotFoundError):
                continue
    
    total_linked_files = sum(len(files) for files in hard_link_groups.values())
    return total_linked_files, hard_link_groups

def find_audio_files(path: Path) -> List[str]:
    """Find audio files in a directory"""
    audio_extensions = {'.m4b', '.mp3', '.flac', '.m4a', '.wav', '.ogg'}
    return [f.name for f in path.iterdir() 
            if f.is_file() and f.suffix.lower() in audio_extensions]

def find_all_files(path: Path) -> List[str]:
    """Find all files in a directory (for renaming consistency)"""
    return sorted(
        (f.name for f in path.iterdir() if f.is_file()),
        key=lambda s: s.lower()
    )

def has_audio_files(path: Path) -> bool:
    """Check if directory contains audio files (to identify audiobook directories)"""
    audio_extensions = {'.m4b', '.mp3', '.flac', '.m4a', '.wav', '.ogg'}
    return any(f.suffix.lower() in audio_extensions for f in path.iterdir() if f.is_file())

def analyze_path_compliance(folder_path: Path, files: List[str], max_length: int = 180) -> Dict[str, Any]:
    """Analyze compliance for a folder and its files, including hard link detection"""
    violations = []
    max_overage = 0
    total_overage = 0
    folder_name = folder_path.name
    
    # Detect hard links
    hard_linked_count, hard_link_groups = detect_hard_links_in_directory(folder_path)
    
    for filename in files:
        full_path = f"{folder_name}/{filename}"
        path_length = len(full_path)
        
        if path_length > max_length:
            overage = path_length - max_length
            violations.append({
                'filename': filename,
                'path': full_path,
                'length': path_length,
                'overage': overage
            })
            max_overage = max(max_overage, overage)
            total_overage += overage
    
    return {
        'compliant': len(violations) == 0,
        'violations': violations,
        'violation_count': len(violations),
        'max_overage': max_overage,
        'total_overage': total_overage,
        'hard_linked_files': hard_linked_count,
        'hard_link_groups': len(hard_link_groups),
        'hard_link_details': hard_link_groups
    }

# === FILTERING AND TARGETING ===

def should_include_directory(dir_path: Path, include_patterns: List[str], exclude_patterns: List[str]) -> Dict[str, Any]:
    """Determine if directory should be included based on filters"""
    dir_name = dir_path.name.lower()
    full_path = str(dir_path).lower()
    
    # Check exclude patterns first (higher priority)
    exclude_reasons = []
    for pattern in exclude_patterns:
        pattern_lower = pattern.lower()
        if pattern_lower in dir_name or pattern_lower in full_path:
            exclude_reasons.append(f"matches exclude pattern: '{pattern}'")
    
    if exclude_reasons:
        return {
            'include': False,
            'reason': 'excluded',
            'details': exclude_reasons
        }
    
    # If no include patterns specified, include by default
    if not include_patterns:
        return {'include': True, 'reason': 'default_include', 'details': []}
    
    # Check include patterns
    include_reasons = []
    for pattern in include_patterns:
        pattern_lower = pattern.lower()
        if pattern_lower in dir_name or pattern_lower in full_path:
            include_reasons.append(f"matches include pattern: '{pattern}'")
    
    if include_reasons:
        return {
            'include': True,
            'reason': 'included',
            'details': include_reasons
        }
    else:
        return {
            'include': False,
            'reason': 'not_matched',
            'details': ['does not match any include patterns']
        }

def detect_tracker_intent(dir_path: Path) -> Dict[str, Any]:
    """Detect what tracker this directory might be intended for"""
    dir_name = dir_path.name.lower()
    
    # Look for tracker-specific indicators
    tracker_indicators = {
        'ops': ['ops', 'orpheus'],
        'mam': ['mam', 'myanonamouse'],
        'red': ['red', 'redacted', 'h2oking'],  # H2OKing is your RED group
        'apt': ['apt', 'audiophile'],
        'btn': ['btn'],
        'ptp': ['ptp']
    }
    
    detected_trackers = []
    for tracker, indicators in tracker_indicators.items():
        for indicator in indicators:
            if indicator in dir_name:
                detected_trackers.append(tracker)
                break
    
    # Check path length compliance for different trackers
    folder_name = dir_path.name
    audio_files = find_audio_files(dir_path)
    
    compliance_status = {}
    if audio_files:
        # Check compliance for major trackers
        for filename in audio_files[:1]:  # Just check first file for efficiency
            full_path = f"{folder_name}/{filename}"
            path_len = len(full_path)
            
            compliance_status['red'] = path_len <= 180
            compliance_status['ops'] = path_len <= 180  
            compliance_status['mam'] = path_len <= 255
    
    return {
        'detected_trackers': detected_trackers,
        'compliance_status': compliance_status,
        'primary_intent': detected_trackers[0] if detected_trackers else 'unknown',
        'safe_for_red': not detected_trackers or 'red' in detected_trackers or 'h2oking' in dir_name.lower()
    }

def get_confirmation_for_risky_changes(results: List[Dict[str, Any]]) -> bool:
    """Get user confirmation for potentially risky changes"""
    risky_dirs = []
    
    for result in results:
        if not result.get('safe_for_red', True):
            risky_dirs.append({
                'path': result['path'],
                'detected_trackers': result.get('tracker_intent', {}).get('detected_trackers', []),
                'primary_intent': result.get('tracker_intent', {}).get('primary_intent', 'unknown')
            })
    
    if not risky_dirs:
        return True
    
    console.print("\n[bold yellow]⚠️  WARNING: Potentially risky changes detected![/bold yellow]")
    console.print("The following directories might be intended for other trackers:")
    
    for risky in risky_dirs:
        dir_name = Path(risky['path']).name
        console.print(f"  • [cyan]{dir_name}[/cyan]")
        console.print(f"    Detected: {', '.join(risky['detected_trackers']) or 'Unknown tracker intent'}")
    
    console.print(f"\n[yellow]Found {len(risky_dirs)} directories that might not be intended for RED.[/yellow]")
    console.print("[yellow]Renaming these could break compatibility with other trackers.[/yellow]")
    
    while True:
        response = input("\nProceed anyway? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no', '']:
            return False
        else:
            console.print("Please enter 'y' or 'n'")

# === SINGLE AUDIOBOOK MODE ===

def handle_single_audiobook(args):
    """Handle single audiobook analysis and fixing"""
    audiobook_path = Path(args.path).resolve()
    
    if not audiobook_path.exists():
        console.print(f"[red]❌ Path does not exist: {audiobook_path}[/red]")
        return 1
    
    if not audiobook_path.is_dir():
        console.print(f"[red]❌ Path is not a directory: {audiobook_path}[/red]")
        return 1
    
    # Check if this is an audiobook directory (has audio files)
    if not has_audio_files(audiobook_path):
        console.print(f"[red]❌ No audio files found in: {audiobook_path}[/red]")
        return 1
    
    # Find all files for renaming (to maintain consistency)
    files = find_all_files(audiobook_path)
    audio_files = find_audio_files(audiobook_path)
    
    if not files:
        console.print(f"[red]❌ No files found in: {audiobook_path}[/red]")
        return 1
    
    folder_name = audiobook_path.name
    
    # Detect tracker intent and safety check
    if not args.force:
        tracker_intent = detect_tracker_intent(audiobook_path)
        
        if not args.quiet and tracker_intent['detected_trackers']:
            console.print(f"[cyan]🔍 Detected tracker indicators: {', '.join(tracker_intent['detected_trackers'])}[/cyan]")
        
        if not tracker_intent['safe_for_red'] and not args.quiet:
            console.print(f"[yellow]⚠️  Warning: This directory appears to be intended for {tracker_intent['primary_intent'].upper()}[/yellow]")
            console.print("[yellow]   Renaming might break compatibility with that tracker.[/yellow]")
            
            if args.apply:
                response = input("\nProceed with renaming anyway? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    console.print("[cyan]📌 Cancelled. Use --force to override safety checks.[/cyan]")
                    return 0
    
    if not args.quiet:
        console.print(Panel.fit(
            f"🎵 RED Path Compliance Tool\n"
            f"Mode: {'APPLY CHANGES' if args.apply else 'DRY RUN'}\n"
            f"Target: {folder_name}\n"
            f"Limit: {args.max_length} characters",
            style="bold blue"
        ))
        console.print(f"🎵 Found {len(audio_files)} audio files, {len(files)} total files")
    
    # Analyze current compliance
    analysis = analyze_path_compliance(audiobook_path, files, args.max_length)
    
    if not args.quiet:
        display_compliance_table(analysis, args.max_length)
    
    # If already compliant, exit early
    if analysis['compliant']:
        if not args.quiet:
            console.print("[green]🎉 Already compliant! No changes needed.[/green]")
        return 0
    
    # Setup path fixer and calculate fixes
    config = ComplianceConfig(
        max_full_path=args.max_length,
        dry_run=not args.apply,
        apply=args.apply
    )
    
    fixer = PathFixer(tracker='red', config=config)
    
    if not args.quiet:
        console.print("\n[yellow]🔧 Calculating optimal fixes...[/yellow]")
    
    new_folder, new_files, log_entries = fixer.fix_path(
        str(audiobook_path), files, apply_changes=args.apply  # pass ABS path
    )
    
    # Verify fixes worked
    new_folder_path = audiobook_path.parent / new_folder
    final_analysis = analyze_path_compliance(new_folder_path, new_files, args.max_length)
    
    if not final_analysis['compliant']:
        console.print("[red]❌ Unable to achieve full compliance[/red]")
        if args.verbose:
            display_compliance_table(final_analysis, args.max_length)
        return 1
    
    # Show results
    if args.verbose or not args.quiet:
        display_changes_preview(log_entries)
    
    if not args.quiet:
        console.print(f"\n[green]✅ Solution found! All paths will be ≤ {args.max_length} chars[/green]")
    
    if args.verbose:
        console.print("\n[bold green]📊 Final Compliance Check:[/bold green]")
        display_compliance_table(final_analysis, args.max_length, show_all_files=True)
    
    # Save detailed log if requested
    if args.log_json:
        save_detailed_log(args.log_json, folder_name, files, new_folder, new_files, log_entries, args.max_length)
    
    if args.apply:
        if not args.quiet:
            console.print("[green]🎉 Changes applied successfully![/green]")
    else:
        if not args.quiet:
            console.print(f"\n[yellow]💡 To apply these changes, run with --apply[/yellow]")
    
    return 0

def display_compliance_table(analysis: Dict[str, Any], max_length: int = 180, show_all_files: bool = False):
    """Display compliance analysis in a table with hard link information"""
    violations = analysis['violations']
    hard_linked_files = analysis.get('hard_linked_files', 0)
    hard_link_groups = analysis.get('hard_link_groups', 0)
    
    # Create header with hard link info
    title = f"Path Compliance Analysis (RED Limit: {max_length} chars)"
    if hard_linked_files > 0:
        title += f"\n🔗 Hard Links: {hard_linked_files} files in {hard_link_groups} groups"
    
    table = Table(title=title)
    table.add_column("File", style="cyan", no_wrap=False)
    table.add_column("Length", justify="right", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Overage", justify="right", style="red")
    if hard_linked_files > 0:
        table.add_column("Hard Links", justify="center", style="yellow")
    
    # Get hard link details for lookup
    hard_link_details = analysis.get('hard_link_details', {})
    file_to_link_count = {}
    
    # Map each file to its hard link count
    for inode, file_paths in hard_link_details.items():
        for file_path in file_paths:
            filename = Path(file_path).name
            file_to_link_count[filename] = len(file_paths)
    
    # If we should show all files (for final compliance check), reconstruct from analysis
    if show_all_files and analysis.get('compliant', False):
        # We need to show all files, but we only have violations stored
        # This is a limitation - we'll show a summary instead
        if hard_linked_files > 0:
            table.add_row("All files", "≤ 180", "✅ PASS", "", f"🔗 Total: {hard_linked_files}")
        else:
            table.add_row("All files", "≤ 180", "✅ PASS", "")
    else:
        # Display violations only
        for violation in violations:
            filename = violation['filename']
            length = violation['length']
            overage = violation['overage']
            
            status = "❌ FAIL"
            overage_str = f"+{overage}"
            
            row_data = [filename, str(length), status, overage_str]
            
            # Add hard link info if applicable
            if hard_linked_files > 0:
                link_count = file_to_link_count.get(filename, 1)
                if link_count > 1:
                    row_data.append(f"🔗 {link_count}")
                else:
                    row_data.append("")
            
            table.add_row(*row_data)
    
    console.print(table)
    
    # Summary
    violation_count = len(violations)
    if violation_count > 0:
        total_files = violation_count  # Only showing violations in this view
        max_overage = max(v['overage'] for v in violations) if violations else 0
        console.print(f"\n[red]📊 Showing {violation_count} files that need renaming[/red]")
        console.print(f"[red]📏 Maximum overage: {max_overage} characters[/red]")
        
        if hard_linked_files > 0:
            console.print(f"[yellow]🔗 {hard_linked_files} files have hard links - renaming will preserve them[/yellow]")
    else:
        console.print(f"\n[green]✅ All files are compliant![/green]")

def display_changes_preview(log_entries: List[ComplianceLog]):
    """Display detailed preview of proposed changes"""
    if not log_entries:
        console.print("[green]No changes needed - already compliant![/green]")
        return
    
    console.print("\n[bold cyan]📋 Proposed Changes Preview[/bold cyan]")
    
    file_changes = [log for log in log_entries if log.scope == "file"]
    folder_changes = [log for log in log_entries if log.scope == "folder"]
    
    if folder_changes:
        console.print("\n[yellow]📁 Folder Changes:[/yellow]")
        for change in folder_changes:
            console.print(f"  • Priority {change.priority}: {change.step}")
            console.print(f"    Before: {change.before_text}")
            console.print(f"    After:  {change.after_text}")
            console.print(f"    Saved: {change.saved_chars} chars")
    
    if file_changes:
        console.print(f"\n[yellow]📄 File Changes ({len(file_changes)} files):[/yellow]")
        for change in file_changes:
            console.print(f"  • {change.target}")
            console.print(f"    Priority {change.priority}: {change.step}")
            console.print(f"    Saved: {change.saved_chars} chars")

# === BATCH SCANNING MODE ===

def handle_batch_scan(args):
    """Handle batch scanning of multiple audiobooks"""
    scan_path = Path(args.path).resolve()
    
    if not scan_path.exists():
        console.print(f"[red]❌ Path does not exist: {scan_path}[/red]")
        return 1
    
    # Parse include/exclude patterns
    include_patterns = args.include or []
    exclude_patterns = args.exclude or []
    
    if not args.quiet:
        filter_info = ""
        if include_patterns:
            filter_info += f"\nInclude: {', '.join(include_patterns)}"
        if exclude_patterns:
            filter_info += f"\nExclude: {', '.join(exclude_patterns)}"
        
        console.print(Panel.fit(
            f"🔍 RED Path Compliance Scanner\n"
            f"Scanning: {scan_path}\n"
            f"Limit: {args.max_length} characters{filter_info}",
            style="bold blue"
        ))
    
    # Find all audiobook directories
    all_audiobook_dirs = find_audiobook_directories(scan_path)
    
    if not all_audiobook_dirs:
        console.print("[yellow]⚠️  No audiobook directories found[/yellow]")
        return 0
    
    # Apply filtering
    filtered_dirs = []
    excluded_count = 0
    
    for dir_path in all_audiobook_dirs:
        filter_result = should_include_directory(dir_path, include_patterns, exclude_patterns)
        
        if filter_result['include']:
            filtered_dirs.append(dir_path)
        else:
            excluded_count += 1
            if args.verbose:
                console.print(f"[dim]Excluded: {dir_path.name} - {filter_result['reason']}[/dim]")
    
    if not args.quiet:
        console.print(f"📁 Found {len(all_audiobook_dirs)} total directories")
        if excluded_count > 0:
            console.print(f"🚫 Excluded {excluded_count} directories by filters")
        console.print(f"🎯 Targeting {len(filtered_dirs)} directories for analysis")
    
    if not filtered_dirs:
        console.print("[yellow]⚠️  No directories remaining after filtering[/yellow]")
        return 0
    
    # Scan each directory
    results = []
    issues_found = 0
    fixable_issues = 0
    risky_changes = 0
    
    for dir_path in track(filtered_dirs, description="Scanning directories..."):
        scan_result = scan_directory_for_batch(dir_path, args.max_length)
        if scan_result:
            # Add tracker detection
            scan_result['tracker_intent'] = detect_tracker_intent(dir_path)
            scan_result['safe_for_red'] = scan_result['tracker_intent']['safe_for_red']
            
            results.append(scan_result)
            
            if not scan_result['compliant']:
                issues_found += 1
                if scan_result['fix_estimate'].get('fixable', False):
                    fixable_issues += 1
                    if not scan_result['safe_for_red']:
                        risky_changes += 1
    
    # Display results
    if not args.quiet:
        display_batch_summary_table(results, args.max_length, args.show_compliant)
    
    # Summary statistics
    total_dirs = len(results)
    compliant_dirs = total_dirs - issues_found
    
    if not args.quiet:
        console.print(f"\n[bold]📊 Summary:[/bold]")
        console.print(f"  Total directories: {total_dirs}")
        console.print(f"  Compliant: {compliant_dirs} ({compliant_dirs/total_dirs*100:.1f}%)")
        console.print(f"  Need fixes: {issues_found} ({issues_found/total_dirs*100:.1f}%)")
        if issues_found > 0:
            console.print(f"  Auto-fixable: {fixable_issues} ({fixable_issues/issues_found*100:.1f}% of issues)")
            if risky_changes > 0:
                console.print(f"  [yellow]⚠️  Risky changes: {risky_changes} (may affect other trackers)[/yellow]")
    
    # Safety warning for batch operations
    if args.generate_script and risky_changes > 0 and not args.force:
        console.print(f"\n[yellow]⚠️  Warning: {risky_changes} directories appear to be intended for other trackers.[/yellow]")
        console.print("[yellow]   Review the generated script before running to avoid breaking compatibility.[/yellow]")
        console.print("[yellow]   Use --force to include risky changes or --exclude to filter them out.[/yellow]")
    
    # Generate batch script if requested
    if args.generate_script:
        generate_batch_script(results, args.generate_script, args.force)
    
    # Apply fixes directly in batch if requested
    if args.apply_batch:
        console.print("\n[bold yellow]🔧 Applying fixes in batch mode...[/bold yellow]")
        applied_count = 0
        for r in results:
            if not r['compliant'] and r['fix_estimate'].get('fixable', False):
                target = Path(r['path'])
                # Re-read actual filenames at apply time
                files = find_all_files(target)
                fixer = PathFixer(tracker='red', config=ComplianceConfig(max_full_path=args.max_length, dry_run=False, apply=True))
                try:
                    console.print(f"  🔧 Fixing: {target.name}")
                    new_folder, new_files, _ = fixer.fix_path(str(target), files, apply_changes=True)
                    applied_count += 1
                except Exception as e:
                    console.print(f"  [red]❌ Failed to fix {target.name}: {e}[/red]")
        console.print(f"[green]✅ Batch apply completed! Fixed {applied_count} directories.[/green]")
    
    # Export JSON report if requested
    if args.export_json:
        export_batch_report(results, scan_path, args.export_json, args.max_length)
    
    return 0 if issues_found == 0 else 1

def find_audiobook_directories(root_path: Path) -> List[Path]:
    """Find all directories containing audio files"""
    audiobook_dirs = []
    
    # Skip known non-audiobook directories for performance
    SKIP_DIRS = {'.git', '__pycache__', '@eaDir', '.DS_Store', 'Thumbs.db'}
    
    for dir_path in root_path.rglob('*'):
        if any(part in SKIP_DIRS for part in dir_path.parts):
            continue
        if dir_path.is_dir() and has_audio_files(dir_path):
            audiobook_dirs.append(dir_path)
    
    return audiobook_dirs

def scan_directory_for_batch(dir_path: Path, max_length: int = 180) -> Dict[str, Any]:
    """Scan a single directory for batch analysis"""
    # Check if this is an audiobook directory
    if not has_audio_files(dir_path):
        return None
    
    # Get all files for renaming, but count audio files separately
    files = find_all_files(dir_path)
    audio_files = find_audio_files(dir_path)
    
    if not files:
        return None
    
    folder_name = dir_path.name
    analysis = analyze_path_compliance(dir_path, files, max_length)
    
    result = {
        'path': str(dir_path),
        'folder_name': folder_name,
        'files': files,
        'audio_files': audio_files,
        'total_files': len(files),
        'compliant': analysis['compliant'],
        'violations': analysis['violations'],
        'violation_count': analysis['violation_count'],
        'max_overage': analysis['max_overage'],
        'hard_linked_files': analysis.get('hard_linked_files', 0),
        'hard_link_groups': analysis.get('hard_link_groups', 0),
        'hard_link_details': analysis.get('hard_link_details', {})
    }
    
    # Estimate if fixable
    if not analysis['compliant']:
        result['fix_estimate'] = estimate_fix_potential(folder_name, files, max_length)
    else:
        result['fix_estimate'] = {'fixable': True}
    
    return result

def estimate_fix_potential(folder_name: str, files: List[str], max_length: int = 180) -> Dict[str, Any]:
    """Estimate if path fixer can resolve compliance issues"""
    try:
        config = ComplianceConfig(max_full_path=max_length, dry_run=True)
        fixer = PathFixer(tracker='red', config=config)
        
        new_folder, new_files, log_entries = fixer.fix_path(folder_name, files, apply_changes=False)
        
        # Check if fixes resolve all issues  
        # Create a path object for the new folder (parent doesn't matter for analysis)
        new_folder_path = Path(new_folder) 
        final_analysis = analyze_path_compliance(new_folder_path, new_files, max_length)
        
        return {
            'fixable': final_analysis['compliant'],
            'new_folder': new_folder,
            'new_files': new_files,
            'changes_made': len(log_entries),
            'total_chars_saved': sum(log.saved_chars for log in log_entries)
        }
    except Exception as e:
        return {
            'fixable': False,
            'error': str(e),
            'changes_made': 0,
            'total_chars_saved': 0
        }

def display_batch_summary_table(results: List[Dict[str, Any]], max_length: int, show_compliant: bool):
    """Display batch scan results in a table"""
    table = Table(title=f"Path Compliance Summary (Limit: {max_length} chars)")
    table.add_column("Directory", style="cyan", no_wrap=False)
    table.add_column("Files", justify="right", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Max Overage", justify="right", style="red")
    table.add_column("Fixable", justify="center", style="green")
    table.add_column("Hard Links", justify="center", style="magenta")
    table.add_column("Tracker", justify="center", style="yellow")
    table.add_column("Safe", justify="center", style="blue")
    
    for result in results:
        if not result['compliant'] or show_compliant:
            dir_name = Path(result['path']).name
            if len(dir_name) > 40:  # Reduced to make room for new columns
                dir_name = dir_name[:37] + "..."
            
            files_count = str(result['total_files'])
            
            if result['compliant']:
                status = "✅ PASS"
                overage = ""
                fixable = ""
            else:
                status = f"❌ FAIL ({result['violation_count']})"
                overage = f"+{result['max_overage']}"
                fixable = "✅" if result['fix_estimate'].get('fixable', False) else "❌"
            
            # Tracker detection info
            tracker_intent = result.get('tracker_intent', {})
            detected = tracker_intent.get('detected_trackers', [])
            primary = tracker_intent.get('primary_intent', 'unknown')
            
            if detected:
                tracker_display = primary.upper()
            else:
                tracker_display = "?"
            
            # Safety indicator
            safe_for_red = result.get('safe_for_red', True)
            safety_display = "✅" if safe_for_red else "⚠️"
            
            # Hard link info
            hard_linked_files = result.get('hard_linked_files', 0)
            hard_link_groups = result.get('hard_link_groups', 0)
            if hard_linked_files > 0:
                hard_link_display = f"🔗 {hard_linked_files}"
            else:
                hard_link_display = ""
            
            table.add_row(dir_name, files_count, status, overage, fixable, hard_link_display, tracker_display, safety_display)
    
    console.print(table)
    
    # Add legend
    console.print("\n[dim]Legend: Safe = ✅ RED-compatible, ⚠️ May affect other trackers[/dim]")

def generate_batch_script(results: List[Dict[str, Any]], script_path: str, force_risky: bool = False):
    """Generate batch fix script with safety considerations"""
    py = sys.executable  # Use same interpreter/venv
    me = Path(__file__).resolve()
    
    script_lines = [
        "#!/bin/bash",
        "# RED Path Compliance Batch Fix Script",
        f"# Generated by mk_torrent path compliance tool",
        ""
    ]
    
    safe_count = 0
    risky_count = 0
    
    for result in results:
        if not result['compliant'] and result['fix_estimate'].get('fixable', False):
            path = result['path']
            is_safe = result.get('safe_for_red', True)
            
            if is_safe or force_risky:
                if not is_safe:
                    script_lines.append(f'# WARNING: May affect other trackers!')
                    script_lines.append(f'# Detected: {result.get("tracker_intent", {}).get("primary_intent", "unknown")}')
                
                script_lines.append(f'echo "Fixing: {Path(path).name}"')
                
                # Add --force flag for risky changes
                force_flag = " --force" if not is_safe else ""
                script_lines.append(f'{py} "{me}" "{path}" --apply{force_flag}')
                script_lines.append("")
                
                if is_safe:
                    safe_count += 1
                else:
                    risky_count += 1
            else:
                script_lines.append(f'# SKIPPED (risky): {Path(path).name}')
                script_lines.append(f'# Detected tracker: {result.get("tracker_intent", {}).get("primary_intent", "unknown")}')
                script_lines.append(f'# Uncomment next line to include: {py} "{me}" "{path}" --apply --force')
                script_lines.append("")
    
    total_count = safe_count + risky_count
    script_lines.append(f"echo \"Batch fix completed: {total_count} directories processed ({safe_count} safe, {risky_count} risky)\"")
    
    with open(script_path, 'w') as f:
        f.write('\n'.join(script_lines))
    
    console.print(f"[green]📝 Batch script generated: {script_path}[/green]")
    console.print(f"[dim]   {safe_count} safe directories included[/dim]")
    if risky_count > 0:
        if force_risky:
            console.print(f"[dim]   {risky_count} risky directories included (--force used)[/dim]")
        else:
            console.print(f"[dim]   {risky_count} risky directories commented out (use --force to include)[/dim]")
    console.print(f"[dim]   Make executable with: chmod +x {script_path}[/dim]")

def export_batch_report(results: List[Dict[str, Any]], scan_path: Path, export_path: str, max_length: int):
    """Export detailed batch report as JSON"""
    issues_found = sum(1 for r in results if not r['compliant'])
    fixable_issues = sum(1 for r in results if not r['compliant'] and r['fix_estimate'].get('fixable', False))
    
    report_data = {
        'scan_path': str(scan_path),
        'max_length': max_length,
        'summary': {
            'total_directories': len(results),
            'compliant_directories': len(results) - issues_found,
            'non_compliant_directories': issues_found,
            'auto_fixable_directories': fixable_issues
        },
        'results': results
    }
    
    with open(export_path, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    console.print(f"[green]📄 Detailed report exported: {export_path}[/green]")

# === UTILITY FUNCTIONS ===

def save_detailed_log(log_path: str, folder_name: str, files: List[str], 
                     new_folder: str, new_files: List[str], log_entries: List[ComplianceLog], max_length: int):
    """Save detailed log to JSON file"""
    log_data = {
        'original_folder': folder_name,
        'original_files': files,
        'new_folder': new_folder,
        'new_files': new_files,
        'max_length': max_length,
        'changes': [
            {
                'scope': log.scope,
                'target': log.target,
                'priority': log.priority,
                'step': log.step,
                'before_len': log.before_len,
                'after_len': log.after_len,
                'saved_chars': log.saved_chars,
                'compliant': log.compliant,
                'before_text': log.before_text,
                'after_text': log.after_text
            }
            for log in log_entries
        ]
    }
    
    with open(log_path, 'w') as f:
        json.dump(log_data, f, indent=2)
    
    console.print(f"[dim]💾 Detailed log saved to: {log_path}[/dim]")

# === MAIN CLI ===

def main():
    parser = argparse.ArgumentParser(
        description="RED Path Compliance Tool - Unified audiobook path fixing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single audiobook analysis (dry-run)
  python path_compliance.py "/path/to/audiobook"
  
  # Single audiobook with detailed preview
  python path_compliance.py "/path/to/audiobook" --verbose
  
  # Apply changes to single audiobook (with safety check)
  python path_compliance.py "/path/to/audiobook" --apply
  
  # Override safety checks for other trackers
  python path_compliance.py "/path/to/audiobook" --apply --force
  
  # Batch scan multiple audiobooks
  python path_compliance.py "/path/to/audiobooks" --batch
  
  # Batch scan with filtering (only RED-related audiobooks)
  python path_compliance.py "/path/to/audiobooks" --batch --include red --include h2oking
  
  # Batch scan excluding other trackers
  python path_compliance.py "/path/to/audiobooks" --batch --exclude ops --exclude mam
  
  # Generate safe batch fix script (excludes risky changes)
  python path_compliance.py "/path/to/audiobooks" --batch --generate-script fixes.sh
  
  # Generate batch script including risky changes
  python path_compliance.py "/path/to/audiobooks" --batch --generate-script fixes.sh --force
  
  # Export detailed report with tracker detection
  python path_compliance.py "/path/to/audiobooks" --batch --export-json report.json
        """
    )
    
    parser.add_argument("path", help="Path to audiobook folder or parent directory for batch mode")
    parser.add_argument("--max-length", type=int, default=180,
                       help="Maximum path length (default: 180 for RED)")
    parser.add_argument("--apply", action="store_true",
                       help="Apply changes (default: dry-run only)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show detailed change preview")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Minimal output")
    
    # Safety and filtering options
    parser.add_argument("--force", action="store_true",
                       help="Override safety checks and include risky changes")
    parser.add_argument("--include", action="append", default=[],
                       help="Include directories matching pattern (can be used multiple times)")
    parser.add_argument("--exclude", action="append", default=[],
                       help="Exclude directories matching pattern (can be used multiple times)")
    
    # Mode selection
    parser.add_argument("--batch", action="store_true",
                       help="Batch mode: scan multiple audiobooks")
    
    # Single audiobook options
    parser.add_argument("--log-json", help="Save detailed log to JSON file")
    
    # Batch mode options  
    parser.add_argument("--apply-batch", action="store_true",
                       help="Apply fixes to each targeted directory (no script)")
    parser.add_argument("--generate-script", help="Generate bash script to fix all issues")
    parser.add_argument("--export-json", help="Export detailed report as JSON")
    parser.add_argument("--show-compliant", action="store_true",
                       help="Also show directories that are already compliant")
    
    args = parser.parse_args()
    
    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s"
    )
    
    try:
        if args.batch:
            return handle_batch_scan(args)
        else:
            return handle_single_audiobook(args)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if args.verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1

if __name__ == "__main__":
    sys.exit(main())
