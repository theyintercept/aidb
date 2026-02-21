#!/usr/bin/env python3
"""
Clean up duplicate files in uploads folder.
Keep only files that are referenced in the database.
"""

import os
import sqlite3

DATABASE = "learning_sequence_v2.db"
UPLOADS_FOLDER = "uploads"

def cleanup_file_type(file_extension, file_type_name):
    print(f"CLEANING UP DUPLICATE {file_type_name.upper()}")
    print("-" * 80)
    
    # Get list of files referenced in database
    db = sqlite3.connect(DATABASE)
    cursor = db.execute(f"SELECT file_path FROM resources WHERE file_path LIKE 'uploads/%{file_extension}'")
    db_files = set()
    for row in cursor:
        # Extract just the filename (remove "uploads/" prefix)
        filename = os.path.basename(row[0])
        db_files.add(filename)
    db.close()
    
    print(f"✓ Database references {len(db_files)} {file_type_name}")
    
    # Get list of all files in uploads folder
    all_files = []
    for filename in os.listdir(UPLOADS_FOLDER):
        if filename.endswith(file_extension):
            all_files.append(filename)
    
    print(f"✓ Found {len(all_files)} {file_type_name} in uploads folder")
    print()
    
    # Find files to delete (in uploads but not in database)
    files_to_delete = []
    for filename in all_files:
        if filename not in db_files:
            files_to_delete.append(filename)
    
    if not files_to_delete:
        print("✓ No duplicate files to delete. All files are referenced in database.")
        print()
        return 0, 0
    
    print(f"⚠️  Found {len(files_to_delete)} duplicate/orphaned files to delete")
    print()
    
    # Calculate space to be freed
    total_size = 0
    for filename in files_to_delete:
        file_path = os.path.join(UPLOADS_FOLDER, filename)
        total_size += os.path.getsize(file_path)
    
    print(f"💾 Space to be freed: {total_size / 1024 / 1024:.1f} MB")
    print()
    
    # Delete files
    deleted_count = 0
    for filename in files_to_delete:
        file_path = os.path.join(UPLOADS_FOLDER, filename)
        try:
            os.remove(file_path)
            deleted_count += 1
            if deleted_count % 100 == 0:
                print(f"  Deleted {deleted_count}/{len(files_to_delete)} files...")
        except Exception as e:
            print(f"  ❌ Error deleting {filename}: {e}")
    
    print()
    print(f"✅ Deleted {deleted_count} duplicate {file_type_name}")
    print(f"✅ Kept {len(db_files)} {file_type_name} referenced in database")
    print(f"✅ Freed {total_size / 1024 / 1024:.1f} MB of disk space")
    print()
    
    return deleted_count, total_size

def main():
    print("=" * 80)
    print("CLEANING UP DUPLICATE FILES IN UPLOADS FOLDER")
    print("=" * 80)
    print()
    
    total_deleted = 0
    total_freed = 0
    
    # Clean up PowerPoint files
    deleted, freed = cleanup_file_type('.pptx', 'PowerPoint files')
    total_deleted += deleted
    total_freed += freed
    
    # Clean up Word documents
    deleted, freed = cleanup_file_type('.docx', 'Word documents')
    total_deleted += deleted
    total_freed += freed
    
    print("=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    print(f"✅ Total files deleted: {total_deleted}")
    print(f"✅ Total disk space freed: {total_freed / 1024 / 1024:.1f} MB")

if __name__ == '__main__':
    main()
