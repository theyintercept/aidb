#!/usr/bin/env python3
"""
Import reference materials to cluster rationale and attachments
"""

import os
import csv
import sqlite3
import re
from pathlib import Path

DATABASE = "learning_sequence_v2.db"

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def get_cluster_rationale(db, cluster_id):
    """Get current cluster rationale"""
    cursor = db.execute('SELECT rationale FROM clusters WHERE id = ?', (cluster_id,))
    result = cursor.fetchone()
    return result['rationale'] if result and result['rationale'] else ''

def update_cluster_rationale(db, cluster_id, new_content):
    """Append content to cluster rationale"""
    current = get_cluster_rationale(db, cluster_id)
    
    if current:
        # Add separator if there's existing content
        if not current.endswith('\n\n'):
            current += '\n\n'
        updated = current + new_content
    else:
        updated = new_content
    
    db.execute('UPDATE clusters SET rationale = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
               (updated, cluster_id))

def is_url_or_doi(file_path):
    """Check if the file path is actually a URL or DOI reference"""
    return '.com)' in file_path or '.org)' in file_path or 'doi.org' in file_path

def get_file_extension(filename):
    """Get file extension"""
    return os.path.splitext(filename)[1].lower()

def store_cluster_resource(db, cluster_id, resource_type, title, file_path):
    """Store file as cluster resource"""
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        extension = get_file_extension(file_path)
        mime_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.mp3': 'audio/mpeg',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        
        db.execute('''
            INSERT INTO cluster_resources 
            (cluster_id, resource_type, title, file_data, file_name, file_size_bytes, mime_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            cluster_id,
            resource_type.lower(),
            title,
            file_data,
            os.path.basename(file_path),
            len(file_data),
            mime_types.get(extension, 'application/octet-stream')
        ))
        return True
    except Exception as e:
        print(f"  ⚠️  Error storing file {file_path}: {e}")
        return False

def add_reference_link_to_rationale(db, cluster_id, resource_type, title, file_name):
    """Add a reference link to cluster rationale"""
    # Format as a reference entry
    reference = f"**{resource_type.upper()}**: {title}\n_(File attached: {file_name})_"
    update_cluster_rationale(db, cluster_id, reference)

def add_url_reference_to_rationale(db, cluster_id, resource_type, title):
    """Add a URL reference directly to rationale"""
    reference = f"**{resource_type.upper()}**: {title}"
    update_cluster_rationale(db, cluster_id, reference)

def main():
    """Process all reference materials"""
    print("=" * 80)
    print("IMPORTING REFERENCE MATERIALS TO CLUSTER RATIONALE")
    print("=" * 80)
    print()
    
    db = get_db()
    
    stats = {
        'processed': 0,
        'pdf_stored': 0,
        'image_stored': 0,
        'audio_stored': 0,
        'docx_stored': 0,
        'url_added': 0,
        'errors': []
    }
    
    # Read the CSV
    with open('reference_materials.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            stats['processed'] += 1
            
            resource_type = row['Type']
            title = row['Title']
            file_path = row['Path']
            cluster_id = int(row['Cluster ID'])
            cluster_title = row['Cluster Title']
            file_name = row['File']
            
            print(f"\n📄 Processing: {title[:60]}...")
            print(f"   Cluster: {cluster_title}")
            
            # Check if it's a URL reference (not an actual file)
            if is_url_or_doi(file_path):
                add_url_reference_to_rationale(db, cluster_id, resource_type, title)
                stats['url_added'] += 1
                print(f"   ✅ Added URL reference to rationale")
                db.commit()
                continue
            
            # Check if file exists
            if not os.path.exists(file_path):
                stats['errors'].append(f"File not found: {file_path}")
                print(f"   ❌ File not found")
                continue
            
            extension = get_file_extension(file_path)
            
            # Store file and add reference to rationale
            if extension == '.pdf':
                if store_cluster_resource(db, cluster_id, resource_type, title, file_path):
                    add_reference_link_to_rationale(db, cluster_id, resource_type, title, file_name)
                    stats['pdf_stored'] += 1
                    print(f"   ✅ Stored PDF as cluster resource")
                    db.commit()
                    
            elif extension in ['.png', '.jpg', '.jpeg']:
                if store_cluster_resource(db, cluster_id, resource_type, title, file_path):
                    add_reference_link_to_rationale(db, cluster_id, resource_type, title, file_name)
                    stats['image_stored'] += 1
                    print(f"   ✅ Stored image as cluster resource")
                    db.commit()
                    
            elif extension == '.mp3':
                if store_cluster_resource(db, cluster_id, resource_type, title, file_path):
                    add_reference_link_to_rationale(db, cluster_id, resource_type, title, file_name)
                    stats['audio_stored'] += 1
                    print(f"   ✅ Stored audio as cluster resource")
                    db.commit()
                    
            elif extension == '.docx':
                # Store Word docs as attachments too (content can be viewed/downloaded)
                if store_cluster_resource(db, cluster_id, resource_type, title, file_path):
                    add_reference_link_to_rationale(db, cluster_id, resource_type, title, file_name)
                    stats['docx_stored'] += 1
                    print(f"   ✅ Stored Word doc as cluster resource")
                    db.commit()
            else:
                stats['errors'].append(f"Unknown file type: {extension} ({file_path})")
                print(f"   ⚠️  Unknown file type: {extension}")
    
    db.close()
    
    # Print summary
    print("\n" + "=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print(f"Total processed: {stats['processed']}")
    print(f"✅ PDFs stored: {stats['pdf_stored']}")
    print(f"✅ Images stored: {stats['image_stored']}")
    print(f"✅ Audio stored: {stats['audio_stored']}")
    print(f"✅ Word docs stored: {stats['docx_stored']}")
    print(f"✅ URL references added: {stats['url_added']}")
    
    if stats['errors']:
        print(f"\n⚠️  Errors ({len(stats['errors'])}):")
        for error in stats['errors']:
            print(f"  - {error}")
    
    print("\n" + "=" * 80)
    print("✅ Reference materials imported to cluster rationale!")
    print("=" * 80)

if __name__ == '__main__':
    main()
