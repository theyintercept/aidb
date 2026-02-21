#!/usr/bin/env python3
"""
Convert all Word documents to PDF and then delete the Word docs
"""

import os
import sqlite3
import subprocess
import tempfile
from pathlib import Path

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
            print(f"      ⏱️  Timeout after 30s")
            return None
        except Exception as e:
            print(f"      ⚠️  Error: {str(e)[:50]}")
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
    
    print(f"Found {len(word_docs)} Word documents to convert\n")
    
    if len(word_docs) == 0:
        print("No Word documents found.")
        db.close()
        return
    
    # Show sample
    print("Sample files:")
    for doc in word_docs[:5]:
        print(f"  - {doc['title']}")
    if len(word_docs) > 5:
        print(f"  ... and {len(word_docs) - 5} more")
    
    print("\n" + "=" * 80)
    print(f"This will:")
    print(f"  1. Convert {len(word_docs)} Word documents to PDF")
    print(f"  2. Delete the original Word documents")
    print("=" * 80)
    
    response = input("\nProceed? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("Operation cancelled.")
        db.close()
        return
    
    print("\n" + "=" * 80)
    print("CONVERTING WORD DOCUMENTS")
    print("=" * 80)
    
    converted_count = 0
    failed_count = 0
    deleted_count = 0
    
    for i, doc in enumerate(word_docs, 1):
        print(f"\n[{i}/{len(word_docs)}] {doc['title']}")
        print(f"    File: {doc['file_name']}")
        
        # Get Word doc data
        if doc['file_data']:
            word_data = doc['file_data']
        elif doc['file_path'] and os.path.exists(doc['file_path']):
            with open(doc['file_path'], 'rb') as f:
                word_data = f.read()
        else:
            print("    ❌ No file data found")
            failed_count += 1
            continue
        
        # Convert to PDF
        print("    Converting to PDF...", end=" ", flush=True)
        pdf_data = convert_word_to_pdf(word_data, doc['file_name'])
        
        if pdf_data:
            # Generate PDF filename (change extension)
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
                
                print(f"✅")
                print(f"    Created: {pdf_filename}")
                converted_count += 1
                
                # Delete the Word document
                print("    Deleting Word doc...", end=" ", flush=True)
                db.execute('DELETE FROM resources WHERE id = ?', [doc['id']])
                db.commit()
                print("✅")
                deleted_count += 1
                
            except Exception as e:
                print(f"❌")
                print(f"    Database error: {str(e)[:80]}")
                db.rollback()
                failed_count += 1
        else:
            print(f"❌")
            failed_count += 1
        
        # Progress update every 50 files
        if i % 50 == 0:
            print(f"\n--- Progress: {i}/{len(word_docs)} processed, {converted_count} converted, {failed_count} failed ---\n")
    
    db.close()
    
    print("\n" + "=" * 80)
    print("CONVERSION COMPLETE")
    print("=" * 80)
    print(f"✅ Successfully converted: {converted_count}")
    print(f"✅ Word docs deleted: {deleted_count}")
    print(f"❌ Failed conversions: {failed_count}")
    print(f"\nTotal resources now: {converted_count} new PDFs")

if __name__ == '__main__':
    main()
