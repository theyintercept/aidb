#!/usr/bin/env python3
"""
Automatically convert all Word documents to PDF and delete originals
"""

import os
import sqlite3
import subprocess
import tempfile
import sys

DATABASE = "learning_sequence_v2.db"

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def convert_word_to_pdf(word_data, original_filename):
    """Convert Word document to PDF using LibreOffice"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save Word doc to temp file
        word_ext = os.path.splitext(original_filename)[1]
        word_path = os.path.join(temp_dir, f"input{word_ext}")
        
        with open(word_path, 'wb') as f:
            f.write(word_data)
        
        # Convert to PDF
        try:
            result = subprocess.run([
                'soffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', temp_dir,
                word_path
            ], check=True, capture_output=True, timeout=30)
            
            # Read the converted PDF
            pdf_path = os.path.join(temp_dir, 'input.pdf')
            
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
    """Main execution"""
    print("=" * 80)
    print("CONVERT ALL WORD DOCUMENTS TO PDF")
    print("=" * 80)
    print()
    
    db = get_db()
    
    # Get all Word documents
    word_docs = db.execute('''
        SELECT 
            r.id, r.element_id, r.title, r.file_name, r.file_data, r.file_path,
            r.resource_category_id, r.file_format_id, r.description, r.audience
        FROM resources r
        WHERE r.mime_type IN ('application/doc', 'application/docx')
        ORDER BY r.element_id, r.title
    ''').fetchall()
    
    print(f"Found {len(word_docs)} Word documents to convert")
    
    if len(word_docs) == 0:
        print("No Word documents found.")
        db.close()
        return
    
    print(f"\nStarting conversion...")
    print("=" * 80)
    
    converted_count = 0
    failed_count = 0
    deleted_count = 0
    
    for i, doc in enumerate(word_docs, 1):
        # Get Word doc data
        if doc['file_data']:
            word_data = doc['file_data']
        elif doc['file_path'] and os.path.exists(doc['file_path']):
            with open(doc['file_path'], 'rb') as f:
                word_data = f.read()
        else:
            failed_count += 1
            continue
        
        # Convert to PDF
        pdf_data = convert_word_to_pdf(word_data, doc['file_name'])
        
        if pdf_data:
            # Generate PDF filename
            pdf_filename = os.path.splitext(doc['file_name'])[0] + '.pdf'
            
            # Insert new PDF resource
            try:
                db.execute('''
                    INSERT INTO resources 
                    (element_id, resource_category_id, file_format_id, title, description, 
                     file_data, file_name, mime_type, file_size_bytes, audience)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    doc['element_id'],
                    doc['resource_category_id'],
                    doc['file_format_id'],
                    doc['title'],
                    doc['description'] if doc['description'] else '',
                    pdf_data,
                    pdf_filename,
                    'application/pdf',
                    len(pdf_data),
                    doc['audience'] if doc['audience'] else 'both'
                ))
                db.commit()
                
                converted_count += 1
                
                # Delete the Word document
                db.execute('DELETE FROM resources WHERE id = ?', [doc['id']])
                db.commit()
                deleted_count += 1
                
            except Exception as e:
                db.rollback()
                failed_count += 1
        else:
            failed_count += 1
        
        # Progress update
        if i % 10 == 0:
            print(f"Progress: {i}/{len(word_docs)} | Converted: {converted_count} | Failed: {failed_count}")
            sys.stdout.flush()
    
    db.close()
    
    print("\n" + "=" * 80)
    print("CONVERSION COMPLETE")
    print("=" * 80)
    print(f"✅ Successfully converted: {converted_count}")
    print(f"✅ Word docs deleted: {deleted_count}")
    print(f"❌ Failed conversions: {failed_count}")

if __name__ == '__main__':
    main()
