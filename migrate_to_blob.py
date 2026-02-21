#!/usr/bin/env python3
"""
Migrate compressed Word documents under 5MB from filesystem to BLOB storage
"""

import os
import sqlite3

DATABASE = "learning_sequence_v2.db"
UPLOADS_FOLDER = "uploads"
BLOB_THRESHOLD = 5 * 1024 * 1024  # 5MB

def get_file_size(filepath):
    """Get file size in bytes"""
    return os.path.getsize(filepath)

def migrate_to_blob():
    print("=" * 80)
    print("MIGRATING SMALL WORD DOCUMENTS TO BLOB STORAGE")
    print("=" * 80)
    print()
    
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    
    # Find Word docs in filesystem that are now under 5MB
    cursor = db.execute('''
        SELECT id, file_name, file_path, file_size_bytes, title
        FROM resources 
        WHERE mime_type LIKE '%word%' 
          AND file_path IS NOT NULL 
          AND file_path != ''
    ''')
    
    candidates = []
    for row in cursor:
        filepath = row['file_path']
        if os.path.exists(filepath):
            current_size = get_file_size(filepath)
            if current_size < BLOB_THRESHOLD:
                candidates.append({
                    'id': row['id'],
                    'file_name': row['file_name'],
                    'file_path': filepath,
                    'old_size': row['file_size_bytes'],
                    'new_size': current_size,
                    'title': row['title']
                })
    
    print(f"✓ Found {len(candidates)} Word documents under 5MB to migrate")
    print()
    
    if not candidates:
        print("No files to migrate!")
        db.close()
        return
    
    migrated = 0
    freed_space = 0
    
    for idx, doc in enumerate(candidates, 1):
        print(f"[{idx}/{len(candidates)}] Migrating: {doc['file_name']}")
        print(f"    Title: {doc['title'][:60]}")
        print(f"    Size: {doc['new_size'] / 1024 / 1024:.2f} MB")
        
        try:
            # Read file content
            with open(doc['file_path'], 'rb') as f:
                file_data = f.read()
            
            # Update database - move to BLOB storage
            db.execute('''
                UPDATE resources 
                SET file_data = ?,
                    file_path = NULL,
                    file_size_bytes = ?
                WHERE id = ?
            ''', (file_data, doc['new_size'], doc['id']))
            
            db.commit()
            
            # Delete file from uploads folder
            os.remove(doc['file_path'])
            
            print(f"    ✅ Migrated to BLOB and removed from filesystem")
            print()
            
            migrated += 1
            freed_space += doc['new_size']
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            print()
            db.rollback()
    
    db.close()
    
    print("=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print(f"✅ Migrated {migrated} documents to BLOB storage")
    print(f"✅ Removed {migrated} files from filesystem")
    print(f"✅ Reduced filesystem usage by {freed_space / 1024 / 1024:.2f} MB")
    print(f"✅ Database BLOBs increased by {freed_space / 1024 / 1024:.2f} MB")
    print()
    print(f"Remaining Word docs in filesystem: {19 - migrated}")

if __name__ == '__main__':
    migrate_to_blob()
