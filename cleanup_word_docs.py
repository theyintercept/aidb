#!/usr/bin/env python3
"""
Clean up redundant Word documents:
1. Convert Word docs to PDF where no PDF version exists
2. Delete Word docs only where a PDF version exists
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

def get_mime_type(filename):
    """Get MIME type from filename"""
    ext = os.path.splitext(filename)[1].lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }
    return mime_types.get(ext, 'application/octet-stream')

def is_word_doc(mime_type):
    """Check if file is a Word document"""
    return mime_type in [
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]

def convert_word_to_pdf(word_data, original_filename):
    """Convert Word document to PDF using LibreOffice"""
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save Word doc to temp file
        word_ext = os.path.splitext(original_filename)[1]
        word_path = os.path.join(temp_dir, f"input{word_ext}")
        
        with open(word_path, 'wb') as f:
            f.write(word_data)
        
        # Convert to PDF using LibreOffice
        try:
            subprocess.run([
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
        except Exception as e:
            print(f"    ⚠️  Conversion failed: {e}")
            return None

def analyze_word_documents():
    """Analyze all Word documents and their PDF equivalents"""
    db = get_db()
    
    # Get all Word documents
    word_docs = db.execute('''
        SELECT r.id, r.element_id, r.title, r.file_name, r.mime_type, r.file_data, r.file_path,
               r.resource_category_id, r.file_format_id, r.description, r.audience
        FROM resources r
        WHERE r.mime_type IN (
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/doc',
            'application/docx'
        )
        ORDER BY r.element_id, r.title
    ''').fetchall()
    
    print(f"Found {len(word_docs)} Word documents in database\n")
    
    # Categorize each Word doc
    to_convert = []
    to_delete = []
    
    for word_doc in word_docs:
        # Check if there's a PDF with the same title in the same element
        pdf_exists = db.execute('''
            SELECT id, title, file_name
            FROM resources
            WHERE element_id = ?
            AND title = ?
            AND mime_type = 'application/pdf'
            AND id != ?
        ''', [word_doc['element_id'], word_doc['title'], word_doc['id']]).fetchone()
        
        if pdf_exists:
            to_delete.append({
                'id': word_doc['id'],
                'title': word_doc['title'],
                'file_name': word_doc['file_name'],
                'pdf_file': pdf_exists['file_name']
            })
        else:
            to_convert.append(dict(word_doc))
    
    db.close()
    
    return to_convert, to_delete

def main():
    """Main execution"""
    print("=" * 80)
    print("WORD DOCUMENT CLEANUP")
    print("=" * 80)
    print()
    
    # Analyze
    print("Analyzing Word documents...")
    to_convert, to_delete = analyze_word_documents()
    
    print("\n" + "=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    print(f"\n📄 Word docs to convert to PDF: {len(to_convert)}")
    print(f"🗑️  Word docs to delete (PDF exists): {len(to_delete)}")
    
    # Show what will be deleted
    if to_delete:
        print("\n" + "-" * 80)
        print("WORD DOCUMENTS TO DELETE (PDF version exists):")
        print("-" * 80)
        for i, doc in enumerate(to_delete[:20], 1):
            print(f"{i}. {doc['title']}")
            print(f"   Word file: {doc['file_name']}")
            print(f"   PDF exists: {doc['pdf_file']}")
        if len(to_delete) > 20:
            print(f"   ... and {len(to_delete) - 20} more")
    
    # Show what will be converted
    if to_convert:
        print("\n" + "-" * 80)
        print("WORD DOCUMENTS TO CONVERT TO PDF:")
        print("-" * 80)
        for i, doc in enumerate(to_convert[:20], 1):
            print(f"{i}. {doc['title']}")
            print(f"   File: {doc['file_name']}")
        if len(to_convert) > 20:
            print(f"   ... and {len(to_convert) - 20} more")
    
    # Ask for confirmation
    print("\n" + "=" * 80)
    response = input("\nProceed with conversion and cleanup? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("Operation cancelled.")
        return
    
    db = get_db()
    
    # Step 1: Convert Word docs to PDF
    if to_convert:
        print("\n" + "=" * 80)
        print("CONVERTING WORD DOCUMENTS TO PDF")
        print("=" * 80)
        
        converted_count = 0
        failed_count = 0
        
        for i, doc in enumerate(to_convert, 1):
            print(f"\n[{i}/{len(to_convert)}] Converting: {doc['title']}")
            
            # Get Word doc data
            if doc['file_data']:
                word_data = doc['file_data']
            elif doc['file_path'] and os.path.exists(doc['file_path']):
                with open(doc['file_path'], 'rb') as f:
                    word_data = f.read()
            else:
                print("    ⚠️  No file data found, skipping")
                failed_count += 1
                continue
            
            # Convert to PDF
            pdf_data = convert_word_to_pdf(word_data, doc['file_name'])
            
            if pdf_data:
                # Get the PDF filename
                pdf_filename = os.path.splitext(doc['file_name'])[0] + '.pdf'
                
                # Insert new PDF resource
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
                    doc['description'] if 'description' in doc else '',
                    pdf_data,
                    pdf_filename,
                    'application/pdf',
                    len(pdf_data),
                    doc['audience'] if 'audience' in doc else 'both'
                ))
                db.commit()
                
                print(f"    ✅ Converted and saved as {pdf_filename}")
                converted_count += 1
                
                # Add to delete list (now that PDF exists)
                to_delete.append({
                    'id': doc['id'],
                    'title': doc['title'],
                    'file_name': doc['file_name'],
                    'pdf_file': pdf_filename
                })
            else:
                print("    ❌ Conversion failed")
                failed_count += 1
        
        print(f"\nConversion complete: {converted_count} succeeded, {failed_count} failed")
    
    # Step 2: Delete redundant Word docs
    if to_delete:
        print("\n" + "=" * 80)
        print("DELETING REDUNDANT WORD DOCUMENTS")
        print("=" * 80)
        
        deleted_count = 0
        
        for i, doc in enumerate(to_delete, 1):
            print(f"[{i}/{len(to_delete)}] Deleting: {doc['file_name']}")
            
            db.execute('DELETE FROM resources WHERE id = ?', [doc['id']])
            db.commit()
            deleted_count += 1
        
        print(f"\nDeleted {deleted_count} redundant Word documents")
    
    db.close()
    
    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    print(f"✅ Converted: {converted_count if to_convert else 0} Word docs to PDF")
    print(f"✅ Deleted: {len(to_delete)} redundant Word docs")
    print(f"⚠️  Failed: {failed_count if to_convert else 0} conversions")

if __name__ == '__main__':
    main()
