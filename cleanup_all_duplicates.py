#!/usr/bin/env python3
"""
Clean up ALL duplicate/orphaned files in uploads folder.
Keep only files that are referenced in the database.
"""

import os
import sqlite3

DATABASE = "learning_sequence_v2.db"
UPLOADS_FOLDER = "uploads"

def cleanup_all_files():
    print("=" * 80)
    print("CLEANING UP ALL DUPLICATE/ORPHANED FILES IN UPLOADS FOLDER")
    print("=" * 80)
    print()
    
    # Get ALL files referenced in database
    db = sqlite3.connect(DATABASE)
    cursor = db.execute("SELECT file_path FROM resources WHERE file_path LIKE 'uploads/%'")
    db_files = set()
    for row in cursor:
        filename = os.path.basename(row[0])
        db_files.add(filename)
    db.close()
    
    print(f"✓ Database references {len(db_files)} files in uploads folder")
    print()
    
    # Get ALL files in uploads folder
    all_files = []
    file_types = {}
    
    for filename in os.listdir(UPLOADS_FOLDER):
        filepath = os.path.join(UPLOADS_FOLDER, filename)
        if os.path.isfile(filepath):
            all_files.append(filename)
            ext = os.path.splitext(filename)[1].lower()
            file_types[ext] = file_types.get(ext, 0) + 1
    
    print(f"✓ Found {len(all_files)} files in uploads folder:")
    for ext, count in sorted(file_types.items()):
        print(f"  - {ext}: {count} files")
    print()
    
    # Find files to delete
    files_to_delete = {}
    for filename in all_files:
        if filename not in db_files:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in files_to_delete:
                files_to_delete[ext] = []
            files_to_delete[ext].append(filename)
    
    if not files_to_delete:
        print("✓ No orphaned files found. All files are referenced in database.")
        return
    
    total_to_delete = sum(len(files) for files in files_to_delete.values())
    print(f"⚠️  Found {total_to_delete} orphaned files to delete:")
    for ext, files in sorted(files_to_delete.items()):
        print(f"  - {ext}: {len(files)} files")
    print()
    
    # Calculate space to be freed
    total_size = 0
    for ext, files in files_to_delete.items():
        for filename in files:
            file_path = os.path.join(UPLOADS_FOLDER, filename)
            total_size += os.path.getsize(file_path)
    
    print(f"💾 Space to be freed: {total_size / 1024 / 1024:.1f} MB")
    print()
    
    # Delete files by type
    deleted_count = 0
    for ext, files in sorted(files_to_delete.items()):
        print(f"Deleting {len(files)} {ext} files...")
        for filename in files:
            file_path = os.path.join(UPLOADS_FOLDER, filename)
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ Error deleting {filename}: {e}")
        print(f"  ✅ Deleted {len(files)} {ext} files")
    
    print()
    print("=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    print(f"✅ Deleted {deleted_count} orphaned files")
    print(f"✅ Kept {len(db_files)} files referenced in database")
    print(f"✅ Freed {total_size / 1024 / 1024:.1f} MB of disk space")
    print()
    
    # Show final summary
    remaining_files = {}
    for filename in os.listdir(UPLOADS_FOLDER):
        if os.path.isfile(os.path.join(UPLOADS_FOLDER, filename)):
            ext = os.path.splitext(filename)[1].lower()
            remaining_files[ext] = remaining_files.get(ext, 0) + 1
    
    print("REMAINING FILES IN UPLOADS FOLDER:")
    for ext, count in sorted(remaining_files.items()):
        print(f"  {ext}: {count} files")

if __name__ == '__main__':
    cleanup_all_files()
