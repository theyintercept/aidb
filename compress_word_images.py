#!/usr/bin/env python3
"""
Compress images in Word documents to reduce file size.
Word .docx files are ZIP archives - we extract, compress images, and repackage.
"""

import os
import shutil
import zipfile
from PIL import Image
from io import BytesIO

UPLOADS_FOLDER = "uploads"
BACKUP_FOLDER = "uploads_backup"
TARGET_SIZE_MB = 5  # Try to get files under 5MB

# Image compression settings
MAX_IMAGE_WIDTH = 1024  # Maximum width in pixels
MAX_IMAGE_HEIGHT = 1024  # Maximum height in pixels
JPEG_QUALITY = 75  # Quality for JPEG compression (1-100)

def get_file_size_mb(filepath):
    """Get file size in MB"""
    return os.path.getsize(filepath) / (1024 * 1024)

def compress_image(image_data, image_format):
    """Compress a single image"""
    try:
        img = Image.open(BytesIO(image_data))
        
        # Convert RGBA to RGB if saving as JPEG
        if img.mode == 'RGBA' and image_format.upper() in ['JPEG', 'JPG']:
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background
        elif img.mode not in ['RGB', 'L']:
            img = img.convert('RGB')
        
        # Resize if too large
        if img.width > MAX_IMAGE_WIDTH or img.height > MAX_IMAGE_HEIGHT:
            img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.Resampling.LANCZOS)
        
        # Compress
        output = BytesIO()
        save_format = 'JPEG' if image_format.upper() in ['JPEG', 'JPG'] else image_format.upper()
        
        if save_format == 'JPEG':
            img.save(output, format=save_format, quality=JPEG_QUALITY, optimize=True)
        elif save_format == 'PNG':
            img.save(output, format=save_format, optimize=True, compress_level=9)
        else:
            img.save(output, format=save_format)
        
        compressed_data = output.getvalue()
        
        # Only return compressed if it's actually smaller
        if len(compressed_data) < len(image_data):
            return compressed_data
        else:
            return image_data
            
    except Exception as e:
        print(f"    Warning: Could not compress image: {e}")
        return image_data

def compress_docx_images(docx_path):
    """Compress images in a .docx file"""
    temp_dir = docx_path + "_temp"
    
    try:
        # Extract the docx (it's a ZIP file)
        with zipfile.ZipFile(docx_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Find and compress images in word/media/
        media_dir = os.path.join(temp_dir, 'word', 'media')
        if not os.path.exists(media_dir):
            shutil.rmtree(temp_dir)
            return 0, 0  # No images to compress
        
        images_compressed = 0
        bytes_saved = 0
        
        for filename in os.listdir(media_dir):
            filepath = os.path.join(media_dir, filename)
            
            # Check if it's an image file
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                continue
            
            # Read original image
            with open(filepath, 'rb') as f:
                original_data = f.read()
            
            original_size = len(original_data)
            
            # Compress
            compressed_data = compress_image(original_data, ext[1:])
            
            # Write compressed image
            with open(filepath, 'wb') as f:
                f.write(compressed_data)
            
            saved = original_size - len(compressed_data)
            if saved > 0:
                images_compressed += 1
                bytes_saved += saved
        
        # Repackage as .docx
        temp_output = docx_path + "_compressed"
        with zipfile.ZipFile(temp_output, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zip_ref.write(file_path, arc_name)
        
        # Replace original with compressed version
        os.remove(docx_path)
        os.rename(temp_output, docx_path)
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        return images_compressed, bytes_saved
        
    except Exception as e:
        print(f"    Error processing {os.path.basename(docx_path)}: {e}")
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return 0, 0

def main():
    print("=" * 80)
    print("COMPRESSING IMAGES IN WORD DOCUMENTS")
    print("=" * 80)
    print()
    
    # Create backup folder
    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER)
        print(f"✓ Created backup folder: {BACKUP_FOLDER}")
    
    # Get list of large Word documents
    large_docs = []
    for filename in os.listdir(UPLOADS_FOLDER):
        if filename.endswith('.docx'):
            filepath = os.path.join(UPLOADS_FOLDER, filename)
            size_mb = get_file_size_mb(filepath)
            if size_mb >= TARGET_SIZE_MB:
                large_docs.append((filepath, size_mb, filename))
    
    large_docs.sort(key=lambda x: x[1], reverse=True)
    
    print(f"✓ Found {len(large_docs)} Word documents >= {TARGET_SIZE_MB}MB")
    print()
    
    if not large_docs:
        print("No files to compress!")
        return
    
    total_saved = 0
    total_images = 0
    
    for idx, (filepath, original_size, filename) in enumerate(large_docs, 1):
        print(f"[{idx}/{len(large_docs)}] Processing: {filename}")
        print(f"    Original size: {original_size:.2f} MB")
        
        # Backup original
        backup_path = os.path.join(BACKUP_FOLDER, filename)
        shutil.copy2(filepath, backup_path)
        
        # Compress images
        images_compressed, bytes_saved = compress_docx_images(filepath)
        
        # Check new size
        new_size = get_file_size_mb(filepath)
        mb_saved = original_size - new_size
        
        print(f"    Images compressed: {images_compressed}")
        print(f"    New size: {new_size:.2f} MB")
        print(f"    Saved: {mb_saved:.2f} MB ({(mb_saved/original_size*100):.1f}%)")
        
        if new_size < TARGET_SIZE_MB:
            print(f"    ✅ Now under {TARGET_SIZE_MB}MB threshold!")
        
        print()
        
        total_saved += mb_saved
        total_images += images_compressed
    
    print("=" * 80)
    print("COMPRESSION COMPLETE")
    print("=" * 80)
    print(f"✅ Processed {len(large_docs)} documents")
    print(f"✅ Compressed {total_images} images")
    print(f"✅ Total space saved: {total_saved:.2f} MB")
    print(f"✅ Backups stored in: {BACKUP_FOLDER}/")
    print()
    print("Files now under 5MB will be stored as BLOBs on next import.")

if __name__ == '__main__':
    main()
