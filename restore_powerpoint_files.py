#!/usr/bin/env python3
"""
Restore PowerPoint files from LEVEL folders
"""

import os
import re
import sqlite3
import shutil
from werkzeug.utils import secure_filename

LEVEL_FOLDERS = ["LEVEL 00", "LEVEL 01", "LEVEL 02"]
DATABASE = "learning_sequence_v2.db"
UPLOADS_FOLDER = "uploads"

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
    
    # Remove trailing (1), (2) etc.
    base_name = re.sub(r'\(\d+\)$', '', base_name).strip()
    
    # Try to match numbered prefix (e.g., "01 INSTRUCTION Title")
    match = re.match(r'^(\d{1,2})\s+([A-Z\s]+)\s+(.+)$', base_name, re.IGNORECASE)
    if match:
        category_raw = match.group(2).strip().upper()
        title = base_name  # Keep full title with number prefix
    else:
        # Try to match category prefix without number
        match = re.match(r'^([A-Z\s]+)\s+(.+)$', base_name, re.IGNORECASE)
        if match:
            category_raw = match.group(1).strip().upper()
            title = base_name
        else:
            # No prefix - default to ACTIVITY
            return 'ACTIVITY', base_name
    
    # Full category mapping (same as Word doc import)
    category_map = {
        'SANDBOX': 'SANDBOX',
        'INSTRUCTIONAL': 'INSTRUCTIONAL',
        'INSTRUCTION': 'INSTRUCTIONAL',
        'EXPLICIT': 'INSTRUCTIONAL',
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
        'CONCRETE': 'INDEPENDENT',
        'CONCRETE PRACTICE': 'INDEPENDENT',
        'ONGOING': 'TEACHING_RESOURCE',
        'ONGOING REFERENCE': 'TEACHING_RESOURCE',
    }
    
    category = category_map.get(category_raw)
    if category:
        return category, title
    
    # If no mapping found, treat as ACTIVITY
    return 'ACTIVITY', title

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

def main():
    print("=" * 80)
    print("RESTORING POWERPOINT FILES")
    print("=" * 80)
    print()
    
    os.makedirs(UPLOADS_FOLDER, exist_ok=True)
    db = get_db()
    
    imported = 0
    skipped = 0
    
    for level_idx, level_folder in enumerate(LEVEL_FOLDERS):
        if not os.path.exists(level_folder):
            continue
        
        for cluster_folder in sorted(os.listdir(level_folder)):
            cluster_path = os.path.join(level_folder, cluster_folder)
            if not os.path.isdir(cluster_path):
                continue
            
            cluster_number = parse_cluster_folder_name(cluster_folder, level_idx)
            if not cluster_number:
                continue
            
            cluster_id = find_cluster_id(db, cluster_number)
            if not cluster_id:
                continue
            
            for element_folder in sorted(os.listdir(cluster_path)):
                element_path = os.path.join(cluster_path, element_folder)
                if not os.path.isdir(element_path):
                    continue
                
                element_sequence = parse_element_folder_name(element_folder)
                if not element_sequence:
                    continue
                
                element_id = find_element_id(db, cluster_id, element_sequence)
                if not element_id:
                    continue
                
                for file_name in os.listdir(element_path):
                    if not file_name.endswith('.pptx'):
                        continue
                    
                    file_path = os.path.join(element_path, file_name)
                    
                    category_code, title = parse_file_name(file_name)
                    if not category_code:
                        skipped += 1
                        continue
                    
                    category_id = get_category_id(db, category_code)
                    if not category_id:
                        skipped += 1
                        continue
                    
                    # Copy to uploads folder
                    safe_name = secure_filename(file_name)
                    upload_path = os.path.join(UPLOADS_FOLDER, safe_name)
                    
                    counter = 1
                    while os.path.exists(upload_path):
                        name_part, ext_part = os.path.splitext(safe_name)
                        upload_path = os.path.join(UPLOADS_FOLDER, f"{name_part}_{counter}{ext_part}")
                        counter += 1
                    
                    shutil.copy2(file_path, upload_path)
                    file_size = os.path.getsize(upload_path)
                    
                    # Insert into database
                    db.execute('''
                        INSERT INTO resources 
                        (element_id, resource_category_id, file_format_id, title, description,
                         file_path, file_name, mime_type, file_size_bytes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        element_id,
                        category_id,
                        4,  # PowerPoint format
                        title,
                        '',
                        upload_path,
                        safe_name,
                        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                        file_size
                    ))
                    db.commit()
                    imported += 1
                    
                    if imported % 10 == 0:
                        print(f"Imported {imported} PowerPoint files...")
    
    db.close()
    
    print("\n" + "=" * 80)
    print(f"✅ Imported {imported} PowerPoint files")
    print(f"⏭️  Skipped {skipped} files")
    print("=" * 80)

if __name__ == '__main__':
    main()
