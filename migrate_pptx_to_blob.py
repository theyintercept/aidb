#!/usr/bin/env python3
"""
Migrate PPTX files under 10MB from filesystem to BLOB storage for Railway compatibility
"""

import os
import sqlite3

DATABASE = "learning_sequence_v2.db"
PPTX_LIMIT = 10 * 1024 * 1024  # 10MB

def migrate_pptx_to_blob():
    print("=" * 80)
    print("MIGRATING PPTX FILES TO BLOB STORAGE (for Railway)")
    print("=" * 80)
    print()
    
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    
    cursor = db.execute('''
        SELECT r.id, r.file_name, r.file_path, r.file_size_bytes, r.title
        FROM resources r
        JOIN file_formats ff ON r.file_format_id = ff.id
        WHERE ff.code = 'PPTX'
          AND r.file_path IS NOT NULL AND r.file_path != ''
          AND (r.file_data IS NULL OR length(r.file_data) = 0)
    ''')
    
    candidates = []
    for row in cursor:
        filepath = row['file_path']
        if os.path.exists(filepath):
            current_size = os.path.getsize(filepath)
            if current_size <= PPTX_LIMIT:
                candidates.append({
                    'id': row['id'],
                    'file_name': row['file_name'],
                    'file_path': filepath,
                    'old_size': row['file_size_bytes'],
                    'new_size': current_size,
                    'title': row['title']
                })
    
    print(f"✓ Found {len(candidates)} PPTX files under 10MB to migrate")
    print()
    
    if not candidates:
        print("No PPTX files to migrate!")
        db.close()
        return
    
    migrated = 0
    for idx, doc in enumerate(candidates, 1):
        print(f"[{idx}/{len(candidates)}] Migrating: {doc['file_name']}")
        print(f"    Title: {doc['title'][:60]}")
        print(f"    Size: {doc['new_size'] / 1024 / 1024:.2f} MB")
        
        try:
            with open(doc['file_path'], 'rb') as f:
                file_data = f.read()
            
            db.execute('''
                UPDATE resources 
                SET file_data = ?,
                    file_path = NULL,
                    file_size_bytes = ?
                WHERE id = ?
            ''', (file_data, doc['new_size'], doc['id']))
            
            db.commit()
            os.remove(doc['file_path'])
            print(f"    ✅ Migrated to BLOB")
            migrated += 1
        except Exception as e:
            print(f"    ❌ Error: {e}")
            db.rollback()
        print()
    
    db.close()
    
    print("=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print(f"✅ Migrated {migrated} PPTX files to BLOB storage")
    print()

if __name__ == '__main__':
    migrate_pptx_to_blob()
