#!/usr/bin/env python3
"""
Final import of all resources - Word, PowerPoint, PDF, Images
NO CONVERSION - keep original formats
"""

import os
import re
import sqlite3
import shutil
from werkzeug.utils import secure_filename

LEVEL_FOLDERS = ["LEVEL 00", "LEVEL 01", "LEVEL 02"]
DATABASE = "learning_sequence_v2.db"
UPLOADS_FOLDER = "uploads"
BLOB_THRESHOLD = 5 * 1024 * 1024  # 5MB

# Category mapping
CATEGORY_MAP = {
    'SANDBOX': 'SANDBOX',
    'INSTRUCTIONAL': 'INSTRUCTIONAL',
    'INSTRUCTION': 'INSTRUCTIONAL',
    'EXPLICIT': 'INSTRUCTIONAL',
    'GUIDED': 'GUIDED',
    'GUIDED PRACTICE': 'GUIDED',
    'INDEPENDENT': 'INDEPENDENT',
    'INDEPENDENT PRACTICE': 'INDEPENDENT',
    'PRACTICE': 'INDEPENDENT',  # PRACTICE without GUIDED → INDEPENDENT
    'CONCRETE': 'INDEPENDENT',
    'CONCRETE PRACTICE': 'INDEPENDENT',
    'ACTIVITY': 'ACTIVITY',
    'ACTIVITIES': 'ACTIVITY',
    'WARMUP': 'ACTIVITY',
    'WARM UP': 'ACTIVITY',
    'GAME': 'ACTIVITY',
    'WORKSHEET': 'ACTIVITY',
    'HANDS ON': 'ACTIVITY',
    'EXTENSION': 'EXTENSION',
    'RETRIEVAL': 'RETRIEVAL',
    'QUIZ': 'QUIZ',
    'ONGOING': 'TEACHING_RESOURCE',
    'ONGOING REFERENCE': 'TEACHING_RESOURCE',
    'RESOURCE': 'TEACHING_RESOURCE',
}

# Skip reference materials (they go in cluster rationale)
SKIP_PREFIXES = ['READING_', 'PODCAST_', 'RESEARCH_', 'ARTICLE_']

# Allowed extensions
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.pptx', '.png', '.jpg', '.jpeg', '.gif', '.mp3', '.mp4'}

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def parse_cluster_folder_name(folder_name, year_level):
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
    match = re.match(r'^(\d{1,2})\s+(.+)$', folder_name)
    if match:
        return int(match.group(1))
    return None

def parse_file_name(filename):
    base_name = os.path.splitext(filename)[0]
    base_name = re.sub(r'\(\d+\)$', '', base_name).strip()
    
    # Skip reference materials
    for skip_prefix in SKIP_PREFIXES:
        if base_name.upper().startswith(skip_prefix) or skip_prefix in base_name.upper():
            return None, None
    
    # Skip Copy_of_ prefix (case insensitive)
    if base_name.lower().startswith('copy_of_'):
        base_name = base_name[8:]
    elif base_name.lower().startswith('copy of '):
        base_name = base_name[8:]
    
    # Normalize underscores to spaces for parsing
    parse_name = base_name.replace('_', ' ')
    
    # Check for ONGOING
    if 'ONGOING' in parse_name.upper():
        return 'TEACHING_RESOURCE', base_name
    
    # Try numbered prefix with known categories
    # Pattern: "01 INSTRUCTION ..." or "01 GUIDED PRACTICE ..."
    for cat_key in sorted(CATEGORY_MAP.keys(), key=len, reverse=True):
        # Try with number prefix
        if re.match(r'^\d{1,2}\s+' + re.escape(cat_key) + r'(?:\s|$)', parse_name, re.IGNORECASE):
            return CATEGORY_MAP[cat_key], base_name
        # Try without number prefix
        if re.match(r'^' + re.escape(cat_key) + r'(?:\s|$)', parse_name, re.IGNORECASE):
            return CATEGORY_MAP[cat_key], base_name
    
    # No match - default to ACTIVITY
    return 'ACTIVITY', base_name
    
    category = CATEGORY_MAP.get(category_raw)
    return category if category else 'ACTIVITY', title

def find_cluster_id(db, cluster_number):
    cursor = db.execute('SELECT id FROM clusters WHERE cluster_number = ?', (cluster_number,))
    result = cursor.fetchone()
    return result['id'] if result else None

def find_element_id(db, cluster_id, element_sequence):
    sequence_order = element_sequence - 1
    cursor = db.execute('''
        SELECT element_id FROM cluster_elements 
        WHERE cluster_id = ? AND sequence_order = ?
    ''', (cluster_id, sequence_order))
    result = cursor.fetchone()
    return result['element_id'] if result else None

def get_category_id(db, category_code):
    cursor = db.execute('SELECT id FROM resource_categories WHERE code = ?', (category_code,))
    result = cursor.fetchone()
    return result['id'] if result else None

def get_file_format_id(extension):
    """Map extension to file_format_id"""
    format_map = {
        '.pdf': 1,
        '.doc': 2,
        '.docx': 2,
        '.png': 3,
        '.jpg': 3,
        '.jpeg': 3,
        '.gif': 3,
        '.pptx': 4,
    }
    return format_map.get(extension, 5)

def get_mime_type(extension):
    """Get proper MIME type"""
    mime_map = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
    }
    return mime_map.get(extension, 'application/octet-stream')

def main():
    print("=" * 80)
    print("IMPORTING ALL RESOURCES - FINAL VERSION")
    print("=" * 80)
    print()
    
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
        'blob': 0,
        'filesystem': 0,
    }
    
    for level_idx, level_folder in enumerate(LEVEL_FOLDERS):
        if not os.path.exists(level_folder):
            continue
        
        print(f"📂 Processing {level_folder}...")
        
        for cluster_folder in sorted(os.listdir(level_folder)):
            cluster_path = os.path.join(level_folder, cluster_folder)
            
            if not os.path.isdir(cluster_path) or cluster_folder == "00 RESEARCH":
                continue
            
            cluster_number = parse_cluster_folder_name(cluster_folder, level_idx)
            if not cluster_number:
                continue
            
            cluster_id = find_cluster_id(db, cluster_number)
            if not cluster_id:
                continue
            
            for element_folder in sorted(os.listdir(cluster_path)):
                element_path = os.path.join(cluster_path, element_folder)
                
                if not os.path.isdir(element_path) or element_folder == "00 RESEARCH":
                    continue
                
                element_sequence = parse_element_folder_name(element_folder)
                if not element_sequence:
                    continue
                
                element_id = find_element_id(db, cluster_id, element_sequence)
                if not element_id:
                    stats['skipped_no_element'] += 1
                    continue
                
                for file_name in os.listdir(element_path):
                    file_path = os.path.join(element_path, file_name)
                    
                    if not os.path.isfile(file_path):
                        continue
                    
                    stats['processed'] += 1
                    
                    extension = os.path.splitext(file_name)[1].lower()
                    
                    if extension not in ALLOWED_EXTENSIONS:
                        stats['skipped_extension'] += 1
                        continue
                    
                    category_code, title = parse_file_name(file_name)
                    
                    if category_code is None:
                        stats['skipped_reference'] += 1
                        continue
                    
                    category_id = get_category_id(db, category_code)
                    if not category_id:
                        stats['skipped_no_category'] += 1
                        continue
                    
                    # Check for duplicate
                    existing = db.execute('''
                        SELECT id FROM resources 
                        WHERE element_id = ? AND title = ?
                    ''', (element_id, title)).fetchone()
                    
                    if existing:
                        stats['skipped_duplicate'] += 1
                        continue
                    
                    try:
                        file_size = os.path.getsize(file_path)
                        file_format_id = get_file_format_id(extension)
                        mime_type = get_mime_type(extension)
                        
                        # Store in DB (BLOB) for Railway compatibility. PPTX under 10MB also stored in DB.
                        pptx_limit = 10 * 1024 * 1024  # 10MB for PPTX
                        use_blob = (file_size <= BLOB_THRESHOLD) or (extension == '.pptx' and file_size <= pptx_limit)
                        if use_blob:
                            # Store as BLOB
                            with open(file_path, 'rb') as f:
                                file_data = f.read()
                            
                            db.execute('''
                                INSERT INTO resources 
                                (element_id, resource_category_id, file_format_id, title, description,
                                 file_data, file_name, mime_type, file_size_bytes)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                element_id, category_id, file_format_id, title, '',
                                file_data, secure_filename(file_name), mime_type, file_size
                            ))
                            stats['blob'] += 1
                        else:
                            # Store in filesystem
                            safe_name = secure_filename(file_name)
                            upload_path = os.path.join(UPLOADS_FOLDER, safe_name)
                            
                            counter = 1
                            while os.path.exists(upload_path):
                                name_part, ext_part = os.path.splitext(safe_name)
                                upload_path = os.path.join(UPLOADS_FOLDER, f"{name_part}_{counter}{ext_part}")
                                counter += 1
                            
                            shutil.copy2(file_path, upload_path)
                            
                            db.execute('''
                                INSERT INTO resources 
                                (element_id, resource_category_id, file_format_id, title, description,
                                 file_path, file_name, mime_type, file_size_bytes)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                element_id, category_id, file_format_id, title, '',
                                upload_path, safe_name, mime_type, file_size
                            ))
                            stats['filesystem'] += 1
                        
                        db.commit()
                        stats['imported'] += 1
                        
                        if stats['imported'] % 50 == 0:
                            print(f"  Imported {stats['imported']} resources...")
                        
                    except Exception as e:
                        print(f"  ❌ Error: {file_name} - {str(e)[:80]}")
                        db.rollback()
    
    db.close()
    
    print("\n" + "=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print(f"Total files processed: {stats['processed']}")
    print(f"✅ Successfully imported: {stats['imported']}")
    print(f"   - Stored as BLOB: {stats['blob']}")
    print(f"   - Stored in filesystem: {stats['filesystem']}")
    print(f"⏭️  Skipped (reference materials): {stats['skipped_reference']}")
    print(f"⏭️  Skipped (duplicate): {stats['skipped_duplicate']}")
    print(f"⏭️  Skipped (no element): {stats['skipped_no_element']}")
    print(f"⏭️  Skipped (no category): {stats['skipped_no_category']}")
    print(f"⏭️  Skipped (invalid extension): {stats['skipped_extension']}")

if __name__ == '__main__':
    main()
