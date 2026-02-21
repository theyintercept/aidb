#!/usr/bin/env python3
"""
Extract READING/PODCAST/RESEARCH/ARTICLE files and prepare them for adding to cluster rationale or element teacher notes
"""

import os
import re
import sqlite3
from pathlib import Path

LEVEL_FOLDERS = ["LEVEL 00", "LEVEL 01", "LEVEL 02"]
DATABASE = "learning_sequence_v2.db"

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

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

def main():
    """Extract reference files"""
    print("=" * 80)
    print("REFERENCE MATERIALS EXTRACTOR")
    print("=" * 80)
    print()
    
    db = get_db()
    references = []
    
    # Walk through all level folders
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
            
            # Get cluster info
            cluster_info = db.execute('SELECT cluster_number, title FROM clusters WHERE id = ?', (cluster_id,)).fetchone()
            
            # Check for 00 RESEARCH folder at cluster level
            research_folder_path = os.path.join(cluster_path, "00 RESEARCH")
            if os.path.isdir(research_folder_path):
                for file_name in os.listdir(research_folder_path):
                    if not os.path.isfile(os.path.join(research_folder_path, file_name)):
                        continue
                    
                    # Check if it's a reference file
                    upper_name = file_name.upper()
                    ref_type = None
                    
                    if 'READING_' in upper_name or file_name.startswith('READING_'):
                        ref_type = 'READING'
                    elif 'PODCAST_' in upper_name or file_name.startswith('PODCAST_'):
                        ref_type = 'PODCAST'
                    elif 'RESEARCH_' in upper_name or file_name.startswith('RESEARCH_'):
                        ref_type = 'RESEARCH'
                    elif 'ARTICLE_' in upper_name or file_name.startswith('ARTICLE_'):
                        ref_type = 'ARTICLE'
                    
                    if ref_type:
                        # Extract title (remove prefix and extension)
                        title = re.sub(r'^(READING_|PODCAST_|RESEARCH_|ARTICLE_)\s*', '', file_name, flags=re.IGNORECASE)
                        title = os.path.splitext(title)[0]
                        
                        references.append({
                            'type': ref_type,
                            'file': file_name,
                            'title': title,
                            'cluster_number': cluster_info['cluster_number'],
                            'cluster_title': cluster_info['title'],
                            'cluster_id': cluster_id,
                            'element_number': None,
                            'element_title': None,
                            'element_id': None,
                            'path': os.path.join(research_folder_path, file_name)
                        })
            
            # Process element folders
            for element_folder in sorted(os.listdir(cluster_path)):
                element_path = os.path.join(cluster_path, element_folder)
                
                if not os.path.isdir(element_path):
                    continue
                
                element_sequence = parse_element_folder_name(element_folder)
                if not element_sequence:
                    continue
                
                element_id = find_element_id(db, cluster_id, element_sequence)
                
                # Get element info if found
                element_info = None
                if element_id:
                    element_info = db.execute('SELECT element_number, title FROM elements WHERE id = ?', (element_id,)).fetchone()
                
                # Process files in element folder
                for file_name in os.listdir(element_path):
                    if not os.path.isfile(os.path.join(element_path, file_name)):
                        continue
                    
                    # Check if it's a reference file
                    upper_name = file_name.upper()
                    ref_type = None
                    
                    if 'READING_' in upper_name or file_name.startswith('READING_'):
                        ref_type = 'READING'
                    elif 'PODCAST_' in upper_name or file_name.startswith('PODCAST_'):
                        ref_type = 'PODCAST'
                    elif 'RESEARCH_' in upper_name or file_name.startswith('RESEARCH_'):
                        ref_type = 'RESEARCH'
                    elif 'ARTICLE_' in upper_name or file_name.startswith('ARTICLE_'):
                        ref_type = 'ARTICLE'
                    
                    if ref_type:
                        # Extract title (remove prefix and extension)
                        title = re.sub(r'^(READING_|PODCAST_|RESEARCH_|ARTICLE_)\s*', '', file_name, flags=re.IGNORECASE)
                        title = os.path.splitext(title)[0]
                        
                        references.append({
                            'type': ref_type,
                            'file': file_name,
                            'title': title,
                            'cluster_number': cluster_info['cluster_number'],
                            'cluster_title': cluster_info['title'],
                            'cluster_id': cluster_id,
                            'element_number': element_info['element_number'] if element_info else None,
                            'element_title': element_info['title'] if element_info else None,
                            'element_id': element_id,
                            'path': os.path.join(element_path, file_name)
                        })
    
    db.close()
    
    # Group by type
    by_type = {'READING': [], 'PODCAST': [], 'RESEARCH': [], 'ARTICLE': []}
    for ref in references:
        by_type[ref['type']].append(ref)
    
    # Print summary
    print(f"Found {len(references)} reference files:\n")
    for ref_type, refs in by_type.items():
        print(f"  {ref_type}: {len(refs)} files")
    
    print("\n" + "=" * 80)
    print("REFERENCE FILES BY TYPE")
    print("=" * 80)
    
    for ref_type, refs in by_type.items():
        if not refs:
            continue
        
        print(f"\n\n{'=' * 80}")
        print(f"{ref_type} MATERIALS ({len(refs)} files)")
        print(f"{'=' * 80}\n")
        
        for ref in refs:
            print(f"📄 {ref['title']}")
            print(f"   Location: Cluster {ref['cluster_number']} - {ref['cluster_title']}")
            if ref['element_title']:
                print(f"             Element {ref['element_number']} - {ref['element_title']}")
            print(f"   File: {ref['file']}")
            print(f"   Suggest: Add to {'Element Teacher Notes' if ref['element_id'] else 'Cluster Rationale'}")
            print()
    
    # Export to CSV for easy processing
    with open('reference_materials.csv', 'w', encoding='utf-8') as f:
        f.write("Type,Title,File,Cluster Number,Cluster Title,Cluster ID,Element Number,Element Title,Element ID,Add To,Path\n")
        for ref in references:
            add_to = 'element_teacher_notes' if ref['element_id'] else 'cluster_rationale'
            f.write(f'"{ref["type"]}","{ref["title"]}","{ref["file"]}",{ref["cluster_number"]},"{ref["cluster_title"]}",{ref["cluster_id"]},{ref["element_number"] or ""},"{ref["element_title"] or ""}",{ref["element_id"] or ""},"{add_to}","{ref["path"]}"\n')
    
    print("\n" + "=" * 80)
    print("✅ Complete list exported to: reference_materials.csv")
    print("=" * 80)

if __name__ == '__main__':
    main()
