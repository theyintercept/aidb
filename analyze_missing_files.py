#!/usr/bin/env python3
"""
Analyze all files that were NOT imported and categorize them
"""

import os
import re
from collections import defaultdict

LEVEL_FOLDERS = ["LEVEL 00", "LEVEL 01", "LEVEL 02"]

# Files we recognize
KNOWN_PREFIXES = [
    'SANDBOX', 'INSTRUCTION', 'INSTRUCTIONAL', 'GUIDED PRACTICE', 'GUIDED',
    'PRACTICE', 'INDEPENDENT PRACTICE', 'INDEPENDENT', 'EXTENSION',
    'ACTIVITY', 'RETRIEVAL PRACTICE', 'RETRIEVAL', 'QUIZ', 'IN ACTION'
]

def parse_file_name(file_name):
    """Parse file name to extract prefix pattern"""
    name_without_ext = os.path.splitext(file_name)[0]
    
    # Try to match pattern: NN CATEGORY Title
    match = re.match(r'^(\d{1,2})\s+([A-Z\s_]+?)\s+(.+)$', name_without_ext)
    if match:
        order = match.group(1)
        category = match.group(2).strip()
        title = match.group(3).strip()
        return f"{order} {category}", title
    
    # No number prefix - just extract first part
    parts = name_without_ext.split()
    if len(parts) > 0 and parts[0].isupper():
        return parts[0], name_without_ext
    
    return "NO_PREFIX", name_without_ext

def main():
    """Analyze all files"""
    print("=" * 80)
    print("MISSING FILES ANALYSIS")
    print("=" * 80)
    print()
    
    files_by_pattern = defaultdict(list)
    total_files = 0
    
    # Walk through all level folders
    for level_folder in LEVEL_FOLDERS:
        if not os.path.exists(level_folder):
            continue
        
        for root, dirs, files in os.walk(level_folder):
            for file_name in files:
                # Skip non-document files
                if not file_name.lower().endswith(('.docx', '.doc', '.pptx', '.ppt', '.pdf', '.png', '.jpg', '.jpeg')):
                    continue
                
                # Skip system files
                if file_name.startswith('.') or file_name.startswith('~$'):
                    continue
                
                total_files += 1
                
                # Parse the file name
                pattern, title = parse_file_name(file_name)
                
                # Check if it's a known category
                is_known = any(prefix in pattern.upper() for prefix in KNOWN_PREFIXES)
                
                if not is_known:
                    relative_path = os.path.relpath(os.path.join(root, file_name), ".")
                    files_by_pattern[pattern].append({
                        'file': file_name,
                        'path': relative_path,
                        'title': title
                    })
    
    print(f"Total files found: {total_files}")
    print(f"Files with unknown patterns: {sum(len(v) for v in files_by_pattern.values())}")
    print()
    print("=" * 80)
    print("UNKNOWN FILE PATTERNS (grouped by prefix)")
    print("=" * 80)
    print()
    
    # Sort by frequency
    sorted_patterns = sorted(files_by_pattern.items(), key=lambda x: len(x[1]), reverse=True)
    
    for pattern, files in sorted_patterns[:50]:  # Show top 50 patterns
        print(f"\n📁 Pattern: '{pattern}' ({len(files)} files)")
        print("-" * 80)
        
        # Show first 3 examples
        for i, file_info in enumerate(files[:3]):
            print(f"  • {file_info['file']}")
            if i == 2 and len(files) > 3:
                print(f"  ... and {len(files) - 3} more")
                break
    
    # Export full list to file for review
    with open('missing_files_full_list.txt', 'w') as f:
        f.write("COMPLETE LIST OF FILES NOT IMPORTED\n")
        f.write("=" * 80 + "\n\n")
        
        for pattern, files in sorted_patterns:
            f.write(f"\nPattern: {pattern} ({len(files)} files)\n")
            f.write("-" * 80 + "\n")
            for file_info in files:
                f.write(f"  {file_info['path']}\n")
    
    print("\n\n" + "=" * 80)
    print("Full list exported to: missing_files_full_list.txt")
    print("=" * 80)

if __name__ == '__main__':
    main()
