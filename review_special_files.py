#!/usr/bin/env python3
"""
Review ONGOING REFERENCE and CONCRETE PRACTICE files to decide categorization
"""

import os
import sqlite3

LEVEL_FOLDERS = ["LEVEL 00", "LEVEL 01", "LEVEL 02"]
DATABASE = "learning_sequence_v2.db"

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def main():
    """Find and list files for review"""
    print("=" * 80)
    print("FILES FOR MANUAL REVIEW")
    print("=" * 80)
    print()
    
    ongoing_files = []
    concrete_files = []
    
    # Find all ONGOING and CONCRETE PRACTICE files
    for level_folder in LEVEL_FOLDERS:
        if not os.path.exists(level_folder):
            continue
        
        for root, dirs, files in os.walk(level_folder):
            for file_name in files:
                full_path = os.path.join(root, file_name)
                if "ONGOING" in file_name.upper():
                    ongoing_files.append(full_path)
                elif "CONCRETE PRACTICE" in file_name.upper():
                    concrete_files.append(full_path)
    
    print(f"📋 ONGOING REFERENCE FILES ({len(ongoing_files)} files)")
    print("=" * 80)
    for i, path in enumerate(sorted(ongoing_files), 1):
        # Extract context from path
        parts = path.split(os.sep)
        if len(parts) >= 3:
            cluster = parts[-3]
            element = parts[-2]
            print(f"\n{i}. {os.path.basename(path)}")
            print(f"   Cluster: {cluster}")
            print(f"   Element: {element}")
            print(f"   Path: {path}")
    
    print(f"\n\n{'=' * 80}")
    print(f"🧱 CONCRETE PRACTICE FILES ({len(concrete_files)} files)")
    print("=" * 80)
    for i, path in enumerate(sorted(concrete_files), 1):
        # Extract context from path
        parts = path.split(os.sep)
        if len(parts) >= 3:
            cluster = parts[-3]
            element = parts[-2]
            print(f"\n{i}. {os.path.basename(path)}")
            print(f"   Cluster: {cluster}")
            print(f"   Element: {element}")
            print(f"   Path: {path}")
    
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"ONGOING files: {len(ongoing_files)}")
    print(f"CONCRETE PRACTICE files: {len(concrete_files)}")
    print()
    print("Please review these files and decide:")
    print("  - Should they be imported as resources?")
    print("  - If yes, which category?")
    print("  - Or should they be added to element teacher notes?")

if __name__ == '__main__':
    main()
