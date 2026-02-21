#!/usr/bin/env python3
"""
Convert all Word documents in the database to PDF format
"""

import os
import sqlite3
import subprocess
import tempfile
import shutil
from pathlib import Path

DATABASE = "learning_sequence_v2.db"
SOFFICE_PATH = "/Applications/LibreOffice.app/Contents/MacOS/soffice"

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def convert_doc_to_pdf(doc_path, output_dir):
    """
    Convert a Word document to PDF using LibreOffice
    Returns the path to the converted PDF or None if failed
    """
    try:
        # Run LibreOffice in headless mode to convert
        result = subprocess.run([
            SOFFICE_PATH,
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            doc_path
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"    ❌ Conversion failed: {result.stderr}")
            return None
        
        # Get the PDF filename (same as doc but with .pdf extension)
        doc_filename = os.path.basename(doc_path)
        pdf_filename = os.path.splitext(doc_filename)[0] + '.pdf'
        pdf_path = os.path.join(output_dir, pdf_filename)
        
        if os.path.exists(pdf_path):
            return pdf_path
        else:
            print(f"    ❌ PDF not found after conversion: {pdf_path}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"    ❌ Conversion timed out")
        return None
    except Exception as e:
        print(f"    ❌ Error during conversion: {e}")
        return None

def main():
    """Main conversion function"""
    print("=" * 70)
    print("WORD TO PDF CONVERTER")
    print("=" * 70)
    print()
    
    if not os.path.exists(SOFFICE_PATH):
        print(f"❌ LibreOffice not found at {SOFFICE_PATH}")
        print("   Please install LibreOffice first.")
        return
    
    db = get_db()
    
    # Get PDF format ID
    pdf_format = db.execute('SELECT id FROM file_formats WHERE code = ?', ('PDF',)).fetchone()
    if not pdf_format:
        print("❌ PDF format not found in database")
        return
    pdf_format_id = pdf_format['id']
    
    # Get all Word documents from database
    word_docs = db.execute('''
        SELECT r.id, r.element_id, r.title, r.file_name, r.file_data, 
               r.resource_category_id, r.audience, r.description,
               e.element_number, e.title as element_title
        FROM resources r
        JOIN elements e ON r.element_id = e.id
        JOIN file_formats ff ON r.file_format_id = ff.id
        WHERE ff.code = 'DOC' AND r.file_data IS NOT NULL
        ORDER BY r.id
    ''').fetchall()
    
    if not word_docs:
        print("ℹ️  No Word documents found in database")
        return
    
    print(f"Found {len(word_docs)} Word documents to convert\n")
    
    stats = {
        'total': len(word_docs),
        'converted': 0,
        'failed': 0,
        'skipped': 0
    }
    
    # Create temporary directory for conversions
    with tempfile.TemporaryDirectory() as temp_dir:
        for doc in word_docs:
            print(f"Converting: {doc['title']}")
            print(f"  Element: #{doc['element_number']} - {doc['element_title']}")
            print(f"  Original file: {doc['file_name']}")
            
            # Save Word doc to temp file
            doc_filename = doc['file_name']
            doc_path = os.path.join(temp_dir, doc_filename)
            
            try:
                with open(doc_path, 'wb') as f:
                    f.write(doc['file_data'])
                
                # Convert to PDF
                pdf_path = convert_doc_to_pdf(doc_path, temp_dir)
                
                if pdf_path and os.path.exists(pdf_path):
                    # Read the PDF data
                    with open(pdf_path, 'rb') as f:
                        pdf_data = f.read()
                    
                    # Update database - replace Word doc with PDF
                    pdf_filename = os.path.basename(pdf_path)
                    pdf_size = len(pdf_data)
                    
                    db.execute('''
                        UPDATE resources
                        SET file_data = ?,
                            file_format_id = ?,
                            file_name = ?,
                            file_size_bytes = ?,
                            mime_type = 'application/pdf'
                        WHERE id = ?
                    ''', (pdf_data, pdf_format_id, pdf_filename, pdf_size, doc['id']))
                    
                    db.commit()
                    
                    print(f"  ✅ Converted successfully: {pdf_filename} ({pdf_size / 1024:.1f} KB)")
                    stats['converted'] += 1
                    
                    # Clean up temp files
                    os.remove(doc_path)
                    os.remove(pdf_path)
                else:
                    print(f"  ❌ Conversion failed")
                    stats['failed'] += 1
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                stats['failed'] += 1
            
            print()
    
    db.close()
    
    # Print summary
    print("=" * 70)
    print("CONVERSION SUMMARY")
    print("=" * 70)
    print(f"Total documents:      {stats['total']}")
    print(f"Successfully converted: {stats['converted']} ✅")
    print(f"Failed:               {stats['failed']} ❌")
    print(f"Skipped:              {stats['skipped']} ⚠️")
    print("=" * 70)
    print()
    
    if stats['converted'] > 0:
        print("✅ Conversion completed!")
        print("   All Word documents have been replaced with PDFs in the database.")
        print("   Restart the Flask app to see the changes.")
    else:
        print("⚠️  No documents were converted.")

if __name__ == '__main__':
    main()
