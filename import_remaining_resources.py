#!/usr/bin/env python3
"""
Import remaining resources with updated category mappings
"""

import os
import re
import sqlite3
from werkzeug.utils import secure_filename
import shutil

# Configuration
LEVEL_FOLDERS = ["LEVEL 00", "LEVEL 01", "LEVEL 02"]
DATABASE = "learning_sequence_v2.db"
UPLOADS_FOLDER = "uploads"

# Updated category mapping based on user decisions
CATEGORY_MAP = {
    'SANDBOX': 'SANDBOX',
    'INSTRUCTIONAL': 'INSTRUCTIONAL',
    'INSTRUCTION': 'INSTRUCTIONAL',
    'GUIDED': 'GUIDED',
    'GUIDED PRACTICE': 'GUIDED',
    'INDEPENDENT': 'INDEPENDENT',
    'INDEPENDENT PRACTICE': 'INDEPENDENT',
    'ACTIVITY': 'ACTIVITY',
    'ACTIVITIES': 'ACTIVITY',
    'EXTENSION': 'EXTENSION',
    'RETRIEVAL': 'RETRIEVAL',
    'QUIZ': 'QUIZ',
    'WARMUP': 'ACTIVITY',
    'WARM UP': 'ACTIVITY',
    'GAME': 'ACTIVITY',
    'RESOURCE': 'TEACHING_RESOURCE',
    'CONCRETE': 'TEACHING_RESOURCE',
    'CONCRETE PRACTICE': 'TEACHING_RESOURCE',
    'ONGOING': 'TEACHING_RESOURCE',
    'ONGOING REFERENCE': 'TEACHING_RESOURCE',
}

# Files to skip (references that go in rationale/notes)
SKIP_PREFIXES = ['READING_', 'PODCAST_', 'RESEARCH_', 'ARTICLE_']

# File size threshold for BLOB vs filesystem storage
BLOB_THRESHOLD = 5 * 1024 * 1024  # 5MB

# Allowed extensions
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.pptx', '.png', '.jpg', '.jpeg', '.gif', '.mp3', '.mp4'}

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def get_file_extension(filename):
    """Extract file extension"""
    return os.path.splitext(filename)[1].lower()

def allowed_file(filename):
    """Check if file extension is allowed"""
    return get_file_extension(filename) in ALLOWED_EXTENSIONS

def parse_cluster_folder_name(folder_name, year_level):
    """Extract cluster number from folder name"""
    match = re.match(r'^(\d{1,2})\s+(.+)$', folder_name)
    if match:
        cluster_num = int(match.group(1))
        if year_level == 0:
            return 100 + cluster_num
        elif year_level == 1:
            return 200 + cluster_num
        elif year_level == 2:
            return 300 + cluster_num
    return None

def parse_element_folder_name(folder_name):
    """Extract element number from folder name"""
    match = re.match(r'^(\d{1,2})\s+(.+)$', folder_name)
    if match:
        return int(match.group(1))
    return None

def parse_file_name(filename):
    """Extract category and title from filename"""
    base_name = os.path.splitext(filename)[0]
    
    # Remove any trailing numbers in parentheses (e.g., "(1)")
    base_name = re.sub(r'\(\d+\)$', '', base_name).strip()
    
    # Check for skip prefixes first
    for skip_prefix in SKIP_PREFIXES:
        if base_name.upper().startswith(skip_prefix) or skip_prefix in base_name.upper():
            return None, None
    
    # Check if it's an ONGOING file (special case)
    if 'ONGOING' in base_name.upper():
        return 'TEACHING_RESOURCE', 'Ongoing Reference'
    
    # Try to match numbered prefix (e.g., "01 SANDBOX Title")
    match = re.match(r'^(\d{1,2})\s+([A-Z\s]+)\s+(.+)$', base_name, re.IGNORECASE)
    if match:
        category_raw = match.group(2).strip().upper()
        title = match.group(3).strip()
    else:
        # Try to match category prefix without number
        match = re.match(r'^([A-Z\s]+)\s+(.+)$', base_name, re.IGNORECASE)
        if match:
            category_raw = match.group(1).strip().upper()
            title = match.group(2).strip()
        else:
            # No prefix - map to ACTIVITY
            return 'ACTIVITY', base_name.strip()
    
    # Map to database category
    category = CATEGORY_MAP.get(category_raw)
    if category:
        return category, title
    
    # If no mapping found, treat as NO_PREFIX -> ACTIVITY
    return 'ACTIVITY', base_name.strip()

def find_cluster_id(db, cluster_number):
    """Find cluster ID by cluster number"""
    cursor = db.execute('SELECT id FROM clusters WHERE cluster_number = ?', (cluster_number,))
    result = cursor.fetchone()
    return result['id'] if result else None

def find_element_id(db, cluster_id, element_sequence):
    """Find element ID by cluster and sequence order"""
    sequence_order = element_sequence - 1  # 0-indexed in DB
    cursor = db.execute('''
        SELECT element_id FROM cluster_elements 
        WHERE cluster_id = ? AND sequence_order = ?
    ''', (cluster_id, sequence_order))
    result = cursor.fetchone()
    return result['element_id'] if result else None

def get_category_id(db, category_code):
    """Get category ID from code"""
    cursor = db.execute('SELECT id FROM resource_categories WHERE code = ?', (category_code,))
    result = cursor.fetchone()
    return result['id'] if result else None

def resource_exists(db, element_id, title):
    """Check if resource already exists"""
    cursor = db.execute('''
        SELECT id FROM resources 
        WHERE element_id = ? AND title = ?
    ''', (element_id, title))
    return cursor.fetchone() is not None

def main():
    """Import remaining resources"""
    print("=" * 80)
    print("IMPORTING REMAINING RESOURCES")
    print("=" * 80)
    print()
    
    # Ensure uploads folder exists
    os.makedirs(UPLOADS_FOLDER, exist_ok=True)
    
    db = get_db()
    
    stats = {
        'processed': 0,
        'imported': 0,
        'skipped_reference': 0,
        'skipped_no_category': 0,
        'skipped_no_element': 0,
        'skipped_duplicate': 0,
        'skipped_extension': 0,
        'errors': []
    }
    
    # Process each level folder
    for level_idx, level_folder in enumerate(LEVEL_FOLDERS):
        if not os.path.exists(level_folder):
            continue
        
        print(f"\n📂 Processing {level_folder}...")
        
        for cluster_folder in sorted(os.listdir(level_folder)):
            cluster_path = os.path.join(level_folder, cluster_folder)
            
            if not os.path.isdir(cluster_path):
                continue
            
            # Skip research folders
            if cluster_folder == "00 RESEARCH":
                continue
            
            cluster_number = parse_cluster_folder_name(cluster_folder, level_idx)
            if not cluster_number:
                continue
            
            cluster_id = find_cluster_id(db, cluster_number)
            if not cluster_id:
                continue
            
            # Process element folders
            for element_folder in sorted(os.listdir(cluster_path)):
                element_path = os.path.join(cluster_path, element_folder)
                
                if not os.path.isdir(element_path):
                    continue
                
                # Skip research folders
                if element_folder == "00 RESEARCH":
                    continue
                
                element_sequence = parse_element_folder_name(element_folder)
                if not element_sequence:
                    continue
                
                element_id = find_element_id(db, cluster_id, element_sequence)
                if not element_id:
                    stats['skipped_no_element'] += 1
                    continue
                
                # Process files in element folder
                for file_name in os.listdir(element_path):
                    file_path = os.path.join(element_path, file_name)
                    
                    if not os.path.isfile(file_path):
                        continue
                    
                    stats['processed'] += 1
                    
                    # Check extension
                    if not allowed_file(file_name):
                        stats['skipped_extension'] += 1
                        continue
                    
                    # Parse filename
                    category_code, title = parse_file_name(file_name)
                    
                    # Skip reference materials
                    if category_code is None:
                        stats['skipped_reference'] += 1
                        continue
                    
                    # Get category ID
                    category_id = get_category_id(db, category_code)
                    if not category_id:
                        stats['skipped_no_category'] += 1
                        stats['errors'].append(f"No category found for: {category_code} ({file_name})")
                        continue
                    
                    # Check for duplicate
                    if resource_exists(db, element_id, title):
                        stats['skipped_duplicate'] += 1
                        continue
                    
                    try:
                        # Read file
                        with open(file_path, 'rb') as f:
                            file_data = f.read()
                        
                        file_size = len(file_data)
                        extension = get_file_extension(file_name)
                        
                        # Get file format ID (default to 1 for PDF/DOC)
                        file_format_id = 1  # Default
                        
                        # Decide storage method
                        if file_size <= BLOB_THRESHOLD:
                            # Store as BLOB
                            db.execute('''
                                INSERT INTO resources 
                                (element_id, resource_category_id, file_format_id, title, description, file_data, file_name, mime_type, file_size_bytes)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                element_id,
                                category_id,
                                file_format_id,
                                title,
                                '',
                                file_data,
                                secure_filename(file_name),
                                f'application/{extension[1:]}' if extension != '.pdf' else 'application/pdf',
                                file_size
                            ))
                            print(f"  ✅ BLOB: {title[:50]}...")
                        else:
                            # Store in filesystem
                            safe_name = secure_filename(file_name)
                            upload_path = os.path.join(UPLOADS_FOLDER, safe_name)
                            
                            # Handle duplicates
                            counter = 1
                            while os.path.exists(upload_path):
                                name_part, ext_part = os.path.splitext(safe_name)
                                upload_path = os.path.join(UPLOADS_FOLDER, f"{name_part}_{counter}{ext_part}")
                                counter += 1
                            
                            # Copy file
                            shutil.copy2(file_path, upload_path)
                            
                            # Store path in database
                            db.execute('''
                                INSERT INTO resources 
                                (element_id, resource_category_id, file_format_id, title, description, file_path, file_name, mime_type, file_size_bytes)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                element_id,
                                category_id,
                                file_format_id,
                                title,
                                '',
                                upload_path,
                                safe_name,
                                f'application/{extension[1:]}' if extension != '.pdf' else 'application/pdf',
                                file_size
                            ))
                            print(f"  ✅ FILE: {title[:50]}...")
                        
                        db.commit()
                        stats['imported'] += 1
                        
                    except Exception as e:
                        stats['errors'].append(f"Error importing {file_name}: {str(e)}")
                        print(f"  ❌ Error: {file_name}")
                        db.rollback()
    
    db.close()
    
    # Print summary
    print("\n" + "=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print(f"Total files processed: {stats['processed']}")
    print(f"✅ Successfully imported: {stats['imported']}")
    print(f"⏭️  Skipped (reference materials): {stats['skipped_reference']}")
    print(f"⏭️  Skipped (duplicate): {stats['skipped_duplicate']}")
    print(f"⏭️  Skipped (no element): {stats['skipped_no_element']}")
    print(f"⏭️  Skipped (no category): {stats['skipped_no_category']}")
    print(f"⏭️  Skipped (invalid extension): {stats['skipped_extension']}")
    
    if stats['errors']:
        print(f"\n❌ Errors ({len(stats['errors'])}):")
        for error in stats['errors'][:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(stats['errors']) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more")

if __name__ == '__main__':
    main()
