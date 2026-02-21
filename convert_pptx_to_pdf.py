#!/usr/bin/env python3
"""
Convert all PowerPoint files to PDF and delete originals
"""

import os
import sqlite3
import subprocess
import tempfile

DATABASE = "learning_sequence_v2.db"

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def convert_pptx_to_pdf(pptx_path):
    """Convert PowerPoint file to PDF using LibreOffice"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Convert to PDF
        try:
            subprocess.run([
                'soffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', temp_dir,
                pptx_path
            ], check=True, capture_output=True, timeout=30)
            
            # Read the converted PDF
            pdf_filename = os.path.splitext(os.path.basename(pptx_path))[0] + '.pdf'
            pdf_path = os.path.join(temp_dir, pdf_filename)
            
            if os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    return f.read()
            else:
                return None
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            return None

def main():
    """Convert all PowerPoint files to PDF"""
    print("=" * 80)
    print("CONVERT POWERPOINT FILES TO PDF")
    print("=" * 80)
    print()
    
    db = get_db()
    
    # Get all PowerPoint files from uploads folder
    pptx_files = db.execute('''
        SELECT 
            r.id, r.element_id, r.title, r.file_path, r.file_name,
            r.resource_category_id, r.file_format_id, r.description, r.audience
        FROM resources r
        WHERE r.mime_type IN ('application/pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation')
        ORDER BY r.element_id, r.title
    ''').fetchall()
    
    print(f"Found {len(pptx_files)} PowerPoint files to convert\n")
    
    if len(pptx_files) == 0:
        print("No PowerPoint files found.")
        db.close()
        return
    
    print("Starting conversion...")
    print("=" * 80)
    
    converted_count = 0
    failed_count = 0
    deleted_count = 0
    
    for i, pptx in enumerate(pptx_files, 1):
        # Check if file exists
        if not pptx['file_path'] or not os.path.exists(pptx['file_path']):
            print(f"[{i}/{len(pptx_files)}] ❌ File not found: {pptx['file_name']}")
            failed_count += 1
            continue
        
        # Convert to PDF
        pdf_data = convert_pptx_to_pdf(pptx['file_path'])
        
        if pdf_data:
            # Generate PDF filename
            pdf_filename = os.path.splitext(pptx['file_name'])[0] + '.pdf'
            
            # Insert new PDF resource
            try:
                db.execute('''
                    INSERT INTO resources 
                    (element_id, resource_category_id, file_format_id, title, description, 
                     file_data, file_name, mime_type, file_size_bytes, audience)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pptx['element_id'],
                    pptx['resource_category_id'],
                    1,  # PDF format
                    pptx['title'],
                    pptx['description'] if pptx['description'] else '',
                    pdf_data,
                    pdf_filename,
                    'application/pdf',
                    len(pdf_data),
                    pptx['audience'] if pptx['audience'] else 'both'
                ))
                db.commit()
                
                converted_count += 1
                
                # Delete the original PowerPoint file from uploads folder
                if os.path.exists(pptx['file_path']):
                    os.remove(pptx['file_path'])
                
                # Delete from database
                db.execute('DELETE FROM resources WHERE id = ?', [pptx['id']])
                db.commit()
                deleted_count += 1
                
            except Exception as e:
                print(f"[{i}/{len(pptx_files)}] ❌ Database error: {pptx['file_name']}")
                db.rollback()
                failed_count += 1
        else:
            print(f"[{i}/{len(pptx_files)}] ❌ Conversion failed: {pptx['file_name']}")
            failed_count += 1
        
        # Progress update every 10 files
        if i % 10 == 0:
            print(f"Progress: {i}/{len(pptx_files)} | Converted: {converted_count} | Failed: {failed_count}")
    
    db.close()
    
    print("\n" + "=" * 80)
    print("CONVERSION COMPLETE")
    print("=" * 80)
    print(f"✅ Successfully converted: {converted_count}")
    print(f"✅ PowerPoint files deleted: {deleted_count}")
    print(f"❌ Failed conversions: {failed_count}")

if __name__ == '__main__':
    main()
