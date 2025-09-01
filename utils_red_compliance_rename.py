#!/usr/bin/env python3
"""
Apply RED Compliance Renames

This script applies the compliance tool suggestions to actually rename
audiobook files and folders to be RED-compatible.

Based on compliance analysis:
- vol_01: 183 chars → 141 chars (42 chars saved)
- vol_02: 183 chars → 141 chars (42 chars saved)

Renames needed:
1. Remove (2023) (Dojyomaru) from folder names
2. Remove (2023) (Dojyomaru) from file names  
3. Compact vol_01 → 1, vol_02 → 2
4. Keep ASIN and full title intact
"""

import os
import shutil
from pathlib import Path

def apply_compliance_renames():
    """Apply the compliance renames to make files RED-uploadable"""
    
    print("🔧 Applying RED Compliance Renames")
    print("=" * 50)
    print("This will rename audiobook files to be RED-compatible")
    print("(Under 150 character path limit)")
    print()
    
    # Original paths
    original_dirs = [
        "/mnt/user/data/downloads/torrents/qbittorrent/seedvault/audiobooks/How a Realist Hero Rebuilt the Kingdom - vol_01 (2023) (Dojyomaru) {ASIN.B0C34GQRYZ} [H2OKing]",
        "/mnt/user/data/downloads/torrents/qbittorrent/seedvault/audiobooks/How a Realist Hero Rebuilt the Kingdom - vol_02 (2023) (Dojyomaru) {ASIN.B0C5S3W7MV} [H2OKing]"
    ]
    
    # Target compliant paths (based on compliance tool output)
    target_dirs = [
        "/mnt/user/data/downloads/torrents/qbittorrent/seedvault/audiobooks/How a Realist Hero Rebuilt the Kingdom - vol_01  {ASIN.B0C34GQRYZ} [H2OKing]",
        "/mnt/user/data/downloads/torrents/qbittorrent/seedvault/audiobooks/How a Realist Hero Rebuilt the Kingdom - vol_02  {ASIN.B0C5S3W7MV} [H2OKing]"
    ]
    
    # File rename mappings
    file_renames = {
        # vol_01 files
        "How a Realist Hero Rebuilt the Kingdom - vol_01 (2023) (Dojyomaru) {ASIN.B0C34GQRYZ}.cue": 
        "How a Realist Hero Rebuilt the Kingdom - 1 {ASIN.B0C34GQRYZ}.cue",
        
        "How a Realist Hero Rebuilt the Kingdom - vol_01 (2023) (Dojyomaru) {ASIN.B0C34GQRYZ}.jpg": 
        "How a Realist Hero Rebuilt the Kingdom - 1 {ASIN.B0C34GQRYZ}.jpg",
        
        "How a Realist Hero Rebuilt the Kingdom - vol_01 (2023) (Dojyomaru) {ASIN.B0C34GQRYZ}.m4b": 
        "How a Realist Hero Rebuilt the Kingdom - 1 {ASIN.B0C34GQRYZ}.m4b",
        
        # vol_02 files  
        "How a Realist Hero Rebuilt the Kingdom - vol_02 (2023) (Dojyomaru) {ASIN.B0C5S3W7MV}.jpg": 
        "How a Realist Hero Rebuilt the Kingdom - 2 {ASIN.B0C5S3W7MV}.jpg",
        
        "How a Realist Hero Rebuilt the Kingdom - vol_02 (2023) (Dojyomaru) {ASIN.B0C5S3W7MV}.m4b": 
        "How a Realist Hero Rebuilt the Kingdom - 2 {ASIN.B0C5S3W7MV}.m4b",
    }
    
    # Perform renames
    for i, (original_dir, target_dir) in enumerate(zip(original_dirs, target_dirs), 1):
        volume = f"vol_0{i}"
        print(f"\n📁 Renaming {volume}...")
        
        if not os.path.exists(original_dir):
            print(f"❌ Original directory not found: {original_dir}")
            continue
            
        if os.path.exists(target_dir):
            print(f"⚠️  Target directory already exists: {target_dir}")
            continue
        
        try:
            # Step 1: Rename directory
            print(f"   📂 Renaming directory...")
            print(f"      From: {os.path.basename(original_dir)}")
            print(f"      To:   {os.path.basename(target_dir)}")
            
            os.rename(original_dir, target_dir)
            print(f"   ✅ Directory renamed")
            
            # Step 2: Rename files within directory
            print(f"   📄 Renaming files...")
            
            for file_path in Path(target_dir).iterdir():
                if file_path.is_file():
                    old_name = file_path.name
                    
                    if old_name in file_renames:
                        new_name = file_renames[old_name]
                        new_path = file_path.parent / new_name
                        
                        print(f"      {old_name} → {new_name}")
                        file_path.rename(new_path)
                    else:
                        print(f"      ⚪ Keeping: {old_name}")
            
            print(f"   ✅ {volume} renamed successfully")
            
            # Verify compliance
            max_path_len = 0
            for file_path in Path(target_dir).iterdir():
                if file_path.is_file():
                    full_path = f"{os.path.basename(target_dir)}/{file_path.name}"
                    path_len = len(full_path)
                    max_path_len = max(max_path_len, path_len)
            
            if max_path_len <= 150:
                print(f"   🎉 {volume} is now RED-compliant ({max_path_len} ≤ 150 chars)")
            else:
                print(f"   ⚠️  {volume} still over limit ({max_path_len} > 150 chars)")
                
        except Exception as e:
            print(f"   ❌ Error renaming {volume}: {e}")
            # Try to rollback if directory was renamed but files failed
            if os.path.exists(target_dir) and not os.path.exists(original_dir):
                try:
                    os.rename(target_dir, original_dir)
                    print(f"   🔄 Rolled back directory rename")
                except:
                    pass
    
    print(f"\n📊 RENAME SUMMARY")
    print("=" * 30)
    
    success_count = 0
    for target_dir in target_dirs:
        volume = "vol_01" if "vol_01" in target_dir else "vol_02"
        
        if os.path.exists(target_dir):
            # Check compliance
            max_path_len = 0
            for file_path in Path(target_dir).iterdir():
                if file_path.is_file():
                    full_path = f"{os.path.basename(target_dir)}/{file_path.name}"
                    path_len = len(full_path)
                    max_path_len = max(max_path_len, path_len)
            
            status = "✅ READY" if max_path_len <= 150 else "❌ NEEDS WORK"
            print(f"  {volume}: {status} ({max_path_len} chars)")
            
            if max_path_len <= 150:
                success_count += 1
        else:
            print(f"  {volume}: ❌ NOT RENAMED")
    
    if success_count == 2:
        print(f"\n🎉 All audiobooks are now RED-compliant!")
        print(f"💡 Ready to run upload test with compliant files")
    else:
        print(f"\n⚠️  {2 - success_count} audiobooks still need work")

if __name__ == "__main__":
    # Safety confirmation
    print("🚨 RENAME CONFIRMATION")
    print("This will permanently rename audiobook files and folders:")
    print("- Remove (2023) (Dojyomaru) from names")
    print("- Compact vol_01 → 1, vol_02 → 2")  
    print("- Keep full title and ASIN intact")
    print()
    
    confirmation = input("Type 'RENAME' to confirm: ")
    if confirmation.strip().upper() == 'RENAME':
        apply_compliance_renames()
    else:
        print("❌ Rename cancelled")
