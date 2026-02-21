#!/usr/bin/env python3
"""
Import resources from LEVEL 00 folder structure into the database
"""

import os
import sqlite3
import re
from pathlib import Path

# Configuration
LEVEL_FOLDERS = ["LEVEL 00", "LEVEL 01", "LEVEL 02"]
DATABASE = "learning_sequence_v2.db"

# Category mapping - map file prefixes to database categories
CATEGORY_MAP = {
    'SANDBOX': 'SANDBOX',
    'INSTRUCTION': 'INSTRUCTIONAL',
    'INSTRUCTIONAL': 'INSTRUCTIONAL',
    'GUIDED PRACTICE': 'GUIDED',
    'GUIDED': 'GUIDED',
    'PRACTICE': 'INDEPENDENT',
    'INDEPENDENT PRACTICE': 'INDEPENDENT',
    'INDEPENDENT': 'INDEPENDENT',
    'EXTENSION': 'EXTENSION',
    'ACTIVITY': 'ACTIVITY',
    'RETRIEVAL': 'RETRIEVAL',
    'RETRIEVAL PRACTICE': 'RETRIEVAL',
    'QUIZ': 'QUIZ',
    'IN ACTION': 'IN_ACTION',
}

# File extension to format code mapping
EXTENSION_MAP = {
    '.pdf': 'PDF',
    '.doc': 'DOC',
    '.docx': 'DOC',
    '.ppt': 'PPTX',
    '.pptx': 'PPTX',
    '.png': 'IMG',
    '.jpg': 'IMG',
    '.jpeg': 'IMG',
    '.gif': 'IMG',
    '.webp': 'IMG',
}

# Files to store as BLOB
BLOB_EXTENSIONS = ['.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg', '.gif', '.webp']

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def parse_cluster_folder_name(folder_name, year_level):
    """Extract cluster number from folder name like '09 PART PART WHOLE PARTITIONING TO 10'"""
    match = re.match(r'^(\d{1,2})\s+(.+)$', folder_name)
    if match:
        cluster_num = int(match.group(1))
        cluster_title = match.group(2)
        # Foundation (Level 00) = 101-125, Year 1 (Level 01) = 201-225, Year 2 (Level 02) = 301-333
        if year_level == 0:
            return 100 + cluster_num, cluster_title
        elif year_level == 1:
            return 200 + cluster_num, cluster_title
        elif year_level == 2:
            return 300 + cluster_num, cluster_title
    return None, None

def parse_element_folder_name(folder_name):
    """Extract element number from folder name like '01 STORYTELLING PARTITIONING TO 10'"""
    match = re.match(r'^(\d{1,2})\s+(.+)$', folder_name)
    if match:
        element_num = int(match.group(1))
        element_title = match.group(2)
        return element_num, element_title
    return None, None

def parse_file_name(file_name):
    """Parse file name like '00 SANDBOX Storytelling partitioning to 10.docx'
    Returns: (order, category, title, extension)
    """
    # Remove extension
    name_without_ext = os.path.splitext(file_name)[0]
    extension = os.path.splitext(file_name)[1].lower()
    
    # Try to match pattern: NN CATEGORY Title
    match = re.match(r'^(\d{1,2})\s+([A-Z\s]+?)\s+(.+)$', name_without_ext)
    if match:
        order = int(match.group(1))
        category = match.group(2).strip()
        title = match.group(3).strip()
        return order, category, title, extension
    
    return None, None, name_without_ext, extension

def find_cluster_id(db, cluster_number):
    """Find cluster ID by cluster number"""
    cursor = db.execute('SELECT id FROM clusters WHERE cluster_number = ?', (cluster_number,))
    result = cursor.fetchone()
    return result['id'] if result else None

def find_element_id(db, cluster_id, element_sequence):
    """Find element ID by cluster and sequence order (0-indexed in DB)"""
    # Folder numbers are 1-indexed (01, 02, 03...)
    # But database sequence_order is 0-indexed (0, 1, 2...)
    sequence_order = element_sequence - 1
    cursor = db.execute('''
        SELECT element_id FROM cluster_elements 
        WHERE cluster_id = ? AND sequence_order = ?
    ''', (cluster_id, sequence_order))
    result = cursor.fetchone()
    return result['element_id'] if result else None

def get_category_id(db, category_code):
    """Get resource category ID by code"""
    cursor = db.execute('SELECT id FROM resource_categories WHERE code = ?', (category_code,))
    result = cursor.fetchone()
    return result['id'] if result else None

def get_format_id(db, format_code):
    """Get file format ID by code"""
    cursor = db.execute('SELECT id FROM file_formats WHERE code = ?', (format_code,))
    result = cursor.fetchone()
    return result['id'] if result else None

def import_file(db, file_path, element_id, category_id, format_id, title, description=''):
    """Import a single file into the database"""
    file_ext = os.path.splitext(file_path)[1].lower()
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    # Determine MIME type
    mime_types = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }
    mime_type = mime_types.get(file_ext, 'application/octet-stream')
    
    # Check if already exists
    cursor = db.execute('''
        SELECT id FROM resources 
        WHERE element_id = ? AND title = ?
    ''', (element_id, title))
    if cursor.fetchone():
        print(f"  ⚠️  Already exists: {title}")
        return False
    
    if file_ext in BLOB_EXTENSIONS:
        # Store in database as BLOB
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        db.execute('''
            INSERT INTO resources (element_id, title, description, resource_category_id,
                                 file_format_id, audience, file_data, file_size_bytes,
                                 file_name, mime_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (element_id, title, description, category_id, format_id,
              'both', file_data, file_size, file_name, mime_type))
    else:
        # Store file path only (for PPTX, etc.)
        # Copy to uploads folder
        import uuid
        import shutil
        unique_filename = f"{uuid.uuid4()}_{file_name}"
        dest_path = os.path.join('uploads', unique_filename)
        shutil.copy2(file_path, dest_path)
        
        db.execute('''
            INSERT INTO resources (element_id, title, description, resource_category_id,
                                 file_format_id, audience, file_path, file_size_bytes,
                                 file_name, mime_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (element_id, title, description, category_id, format_id,
              'both', unique_filename, file_size, file_name, mime_type))
    
    db.commit()
    return True

def main():
    """Main import function"""
    print("=" * 70)
    print("RESOURCE IMPORT SCRIPT - ALL LEVELS")
    print("=" * 70)
    print()
    
    db = get_db()
    
    stats = {
        'clusters': 0,
        'elements': 0,
        'files_found': 0,
        'files_imported': 0,
        'files_skipped': 0,
        'errors': 0,
    }
    
    # Process each level folder
    for level_idx, level_folder in enumerate(LEVEL_FOLDERS):
        if not os.path.exists(level_folder):
            print(f"⚠️  Skipping '{level_folder}' - not found")
            continue
        
        print(f"\n{'=' * 70}")
        print(f"PROCESSING {level_folder}")
        print(f"{'=' * 70}\n")
        
        # Walk through the folder structure
        for cluster_folder in sorted(os.listdir(level_folder)):
            cluster_path = os.path.join(level_folder, cluster_folder)
        
            if not os.path.isdir(cluster_path):
                continue
            
            # Parse cluster number
            cluster_number, cluster_title = parse_cluster_folder_name(cluster_folder, level_idx)
            if not cluster_number:
                print(f"⚠️  Skipping folder (can't parse cluster): {cluster_folder}")
                continue
            
            # Find cluster in database
            cluster_id = find_cluster_id(db, cluster_number)
            if not cluster_id:
                print(f"⚠️  Cluster {cluster_number} not found in database: {cluster_folder}")
                continue
            
            print(f"\n📁 Cluster {cluster_number}: {cluster_title}")
            stats['clusters'] += 1
            
            # Process element folders
            for element_folder in sorted(os.listdir(cluster_path)):
                element_path = os.path.join(cluster_path, element_folder)
                
                if not os.path.isdir(element_path):
                    continue
                
                # Parse element number
                element_sequence, element_title = parse_element_folder_name(element_folder)
                if not element_sequence:
                    print(f"  ⚠️  Skipping folder (can't parse element): {element_folder}")
                    continue
                
                # Find element in database
                element_id = find_element_id(db, cluster_id, element_sequence)
                if not element_id:
                    print(f"  ⚠️  Element {element_sequence} not found for cluster {cluster_number}: {element_folder}")
                    continue
                
                print(f"  📄 Element {element_sequence}: {element_title}")
                stats['elements'] += 1
                
                # Process files in element folder
                files = sorted([f for f in os.listdir(element_path) if os.path.isfile(os.path.join(element_path, f))])
                
                for file_name in files:
                    file_path = os.path.join(element_path, file_name)
                    stats['files_found'] += 1
                    
                    # Parse file name
                    order, category, title, extension = parse_file_name(file_name)
                    
                    if not category or category not in CATEGORY_MAP:
                        print(f"    ⚠️  Unknown category in file: {file_name}")
                        stats['files_skipped'] += 1
                        continue
                    
                    if extension not in EXTENSION_MAP:
                        print(f"    ⚠️  Unsupported file type: {file_name}")
                        stats['files_skipped'] += 1
                        continue
                    
                    # Get database IDs
                    category_code = CATEGORY_MAP[category]
                    category_id = get_category_id(db, category_code)
                    
                    format_code = EXTENSION_MAP[extension]
                    format_id = get_format_id(db, format_code)
                    
                    if not category_id or not format_id:
                        print(f"    ❌ Category or format not found in database: {file_name}")
                        stats['errors'] += 1
                        continue
                    
                    # Import the file
                    try:
                        if import_file(db, file_path, element_id, category_id, format_id, title):
                            print(f"    ✅ Imported: {title} ({category})")
                            stats['files_imported'] += 1
                        else:
                            stats['files_skipped'] += 1
                    except Exception as e:
                        print(f"    ❌ Error importing {file_name}: {e}")
                        stats['errors'] += 1
    
    db.close()
    
    # Print summary
    print()
    print("=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)
    print(f"Clusters processed:   {stats['clusters']}")
    print(f"Elements processed:   {stats['elements']}")
    print(f"Files found:          {stats['files_found']}")
    print(f"Files imported:       {stats['files_imported']} ✅")
    print(f"Files skipped:        {stats['files_skipped']} ⚠️")
    print(f"Errors:               {stats['errors']} ❌")
    print("=" * 70)
    print()
    
    if stats['files_imported'] > 0:
        print("✅ Import completed successfully!")
    else:
        print("⚠️  No files were imported. Check the warnings above.")

if __name__ == '__main__':
    main()
