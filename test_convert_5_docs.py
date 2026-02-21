#!/usr/bin/env python3
"""
Test conversion of 5 Word documents to PDF
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
            print(f"      ⚠️  Error: {str(e)[:80]}")
            return None

def main():
    """Test conversion of 5 docs"""
    print("=" * 80)
    print("TEST CONVERSION: 5 WORD DOCUMENTS TO PDF")
    print("=" * 80)
    print()
    
    db = get_db()
    
    # Get first 5 Word documents
    word_docs = db.execute('''
        SELECT 
            r.id, r.element_id, r.title, r.file_name, r.file_data,
            r.resource_category_id, r.file_format_id, r.description, r.audience
        FROM resources r
        WHERE r.mime_type IN ('application/doc', 'application/docx')
        ORDER BY r.element_id, r.title
        LIMIT 5
    ''').fetchall()
    
    print(f"Converting {len(word_docs)} test documents:\n")
    
    for i, doc in enumerate(word_docs, 1):
        print(f"{i}. {doc['title']}")
        print(f"   File: {doc['file_name']}")
    
    print("\n" + "=" * 80)
    print("Starting conversion...")
    print("=" * 80 + "\n")
    
    converted_ids = []
    
    for i, doc in enumerate(word_docs, 1):
        print(f"[{i}/5] Converting: {doc['title']}")
        
        # Get Word doc data
        if not doc['file_data']:
            print("    ❌ No file data found")
            continue
        
        # Convert to PDF
        print("    Converting...", end=" ", flush=True)
        pdf_data = convert_word_to_pdf(doc['file_data'], doc['file_name'])
        
        if pdf_data:
            # Generate PDF filename
            pdf_filename = os.path.splitext(doc['file_name'])[0] + '.pdf'
            
            # Insert new PDF resource
            try:
                cursor = db.execute('''
                    INSERT INTO resources 
                    (element_id, resource_category_id, file_format_id, title, description, 
                     file_data, file_name, mime_type, file_size_bytes, audience)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    doc['element_id'],
                    doc['resource_category_id'],
                    1,  # PDF format
                    doc['title'],
                    doc['description'] if doc['description'] else '',
                    pdf_data,
                    pdf_filename,
                    'application/pdf',
                    len(pdf_data),
                    doc['audience'] if doc['audience'] else 'both'
                ))
                new_pdf_id = cursor.lastrowid
                db.commit()
                
                print(f"✅")
                print(f"    Created PDF: {pdf_filename}")
                print(f"    Size: {len(pdf_data)/1024:.1f} KB")
                print(f"    New resource ID: {new_pdf_id}")
                
                converted_ids.append((doc['id'], new_pdf_id))
                
            except Exception as e:
                print(f"❌")
                print(f"    Database error: {str(e)[:80]}")
                db.rollback()
        else:
            print(f"❌")
        
        print()
    
    db.close()
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print(f"\n✅ Successfully converted: {len(converted_ids)}/5 documents")
    
    if converted_ids:
        print("\nPDF resources created:")
        for word_id, pdf_id in converted_ids:
            print(f"  - Word doc ID {word_id} → PDF ID {pdf_id}")
        
        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print("\n1. Check the web interface to verify the PDFs look correct")
        print("   URL: http://127.0.0.1:8080")
        print("\n2. If PDFs look good, the Word documents can be safely deleted:")
        for word_id, pdf_id in converted_ids:
            print(f"   DELETE FROM resources WHERE id = {word_id};")
        
        print("\n3. If everything looks good, run the full conversion for all 704 docs")

if __name__ == '__main__':
    main()
