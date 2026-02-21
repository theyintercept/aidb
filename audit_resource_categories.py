#!/usr/bin/env python3
"""
Audit resource categories to ensure file names match assigned categories
"""

import sqlite3
import re
from collections import defaultdict

DATABASE = "learning_sequence_v2.db"

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def extract_category_from_filename(file_name):
    """Extract the category prefix from a file name"""
    # Remove file extension
    base_name = re.sub(r'\.[^.]+$', '', file_name)
    
    # Remove trailing (1), (2) etc.
    base_name = re.sub(r'\(\d+\)$', '', base_name).strip()
    
    # Try to match numbered prefix (e.g., "01 INSTRUCTION Title")
    match = re.match(r'^(\d{1,2})\s+([A-Z_\s]+)', base_name, re.IGNORECASE)
    if match:
        return match.group(2).strip().upper()
    
    # Try to match category prefix without number (e.g., "INSTRUCTION_ Title")
    match = re.match(r'^([A-Z_]+)[_\s]', base_name, re.IGNORECASE)
    if match:
        return match.group(1).strip().upper()
    
    # Check for special patterns anywhere in name
    upper_name = base_name.upper()
    if 'INSTRUCTION' in upper_name or 'INSTRUCTIONAL' in upper_name:
        return 'INSTRUCTION'
    if 'GUIDED' in upper_name:
        return 'GUIDED'
    if 'INDEPENDENT' in upper_name:
        return 'INDEPENDENT'
    if 'SANDBOX' in upper_name:
        return 'SANDBOX'
    if 'ACTIVITY' in upper_name or 'ACTIVITIES' in upper_name:
        return 'ACTIVITY'
    if 'EXTENSION' in upper_name:
        return 'EXTENSION'
    if 'RETRIEVAL' in upper_name:
        return 'RETRIEVAL'
    if 'WARMUP' in upper_name or 'WARM UP' in upper_name:
        return 'WARMUP'
    if 'GAME' in upper_name:
        return 'GAME'
    if 'CONCRETE' in upper_name:
        return 'CONCRETE'
    if 'ONGOING' in upper_name:
        return 'ONGOING'
    if 'RESOURCE' in upper_name:
        return 'RESOURCE'
    if 'EXPLICIT' in upper_name:
        return 'EXPLICIT'
    if 'WORKSHEET' in upper_name:
        return 'WORKSHEET'
    if 'HANDS ON' in upper_name:
        return 'HANDS_ON'
    if 'QUIZ' in upper_name:
        return 'QUIZ'
    
    return 'NO_PREFIX'

def expected_category_for_prefix(prefix):
    """Map prefix to expected category code"""
    mapping = {
        'SANDBOX': 'SANDBOX',
        'INSTRUCTION': 'INSTRUCTIONAL',
        'INSTRUCTIONAL': 'INSTRUCTIONAL',
        'EXPLICIT': 'INSTRUCTIONAL',
        'GUIDED': 'GUIDED',
        'GUIDED PRACTICE': 'GUIDED',
        'INDEPENDENT': 'INDEPENDENT',
        'INDEPENDENT PRACTICE': 'INDEPENDENT',
        'CONCRETE': 'INDEPENDENT',
        'CONCRETE PRACTICE': 'INDEPENDENT',
        'ACTIVITY': 'ACTIVITY',
        'ACTIVITIES': 'ACTIVITY',
        'WARMUP': 'ACTIVITY',
        'WARM UP': 'ACTIVITY',
        'GAME': 'ACTIVITY',
        'WORKSHEET': 'ACTIVITY',
        'HANDS ON': 'ACTIVITY',
        'HANDS_ON': 'ACTIVITY',
        'EXTENSION': 'EXTENSION',
        'RETRIEVAL': 'RETRIEVAL',
        'QUIZ': 'QUIZ',
        'ONGOING': 'TEACHING_RESOURCE',
        'ONGOING REFERENCE': 'TEACHING_RESOURCE',
        'RESOURCE': 'TEACHING_RESOURCE',
        'NO_PREFIX': 'ACTIVITY',  # Default for files without prefix
    }
    return mapping.get(prefix, None)

def main():
    """Audit all resource categories"""
    print("=" * 100)
    print("RESOURCE CATEGORY AUDIT")
    print("=" * 100)
    print()
    
    db = get_db()
    
    # Get all resources with their categories
    resources = db.execute('''
        SELECT 
            r.id,
            r.title,
            r.file_name,
            rc.code as category_code,
            rc.name as category_name,
            e.element_number,
            e.title as element_title,
            c.cluster_number,
            c.title as cluster_title
        FROM resources r
        JOIN resource_categories rc ON r.resource_category_id = rc.id
        JOIN elements e ON r.element_id = e.id
        JOIN cluster_elements ce ON e.id = ce.element_id
        JOIN clusters c ON ce.cluster_id = c.id
        ORDER BY r.file_name
    ''').fetchall()
    
    db.close()
    
    print(f"Total resources in database: {len(resources)}\n")
    
    # Track mismatches
    mismatches = []
    correct = []
    unknown_prefix = []
    prefix_stats = defaultdict(lambda: defaultdict(int))
    
    # Analyze each resource
    for resource in resources:
        file_name = resource['file_name']
        actual_category = resource['category_code']
        
        # Extract prefix from filename
        prefix = extract_category_from_filename(file_name)
        
        # Get expected category
        expected_category = expected_category_for_prefix(prefix)
        
        # Track prefix -> actual category mapping
        prefix_stats[prefix][actual_category] += 1
        
        if expected_category is None:
            unknown_prefix.append({
                'resource': resource,
                'prefix': prefix,
                'file_name': file_name
            })
        elif expected_category != actual_category:
            mismatches.append({
                'resource': resource,
                'prefix': prefix,
                'expected': expected_category,
                'actual': actual_category,
                'file_name': file_name
            })
        else:
            correct.append(resource)
    
    # Print prefix statistics
    print("=" * 100)
    print("PREFIX → CATEGORY MAPPING STATISTICS")
    print("=" * 100)
    print()
    
    for prefix in sorted(prefix_stats.keys()):
        print(f"\n📋 {prefix}:")
        for category, count in sorted(prefix_stats[prefix].items(), key=lambda x: -x[1]):
            expected = expected_category_for_prefix(prefix)
            marker = "✅" if category == expected else "❌"
            print(f"   {marker} {category}: {count} files")
    
    # Print mismatches
    print("\n\n" + "=" * 100)
    print(f"CATEGORY MISMATCHES ({len(mismatches)} files)")
    print("=" * 100)
    print()
    
    if mismatches:
        # Group by prefix
        by_prefix = defaultdict(list)
        for mismatch in mismatches:
            by_prefix[mismatch['prefix']].append(mismatch)
        
        for prefix in sorted(by_prefix.keys()):
            items = by_prefix[prefix]
            expected = expected_category_for_prefix(prefix)
            print(f"\n{'=' * 100}")
            print(f"PREFIX: {prefix} (Expected category: {expected})")
            print(f"Found {len(items)} mismatches")
            print('=' * 100)
            
            # Show first 10 examples
            for item in items[:10]:
                r = item['resource']
                print(f"\n❌ MISMATCH:")
                print(f"   File: {item['file_name']}")
                print(f"   Title: {r['title']}")
                print(f"   Location: Cluster {r['cluster_number']} - {r['cluster_title']}")
                print(f"              Element {r['element_number']} - {r['element_title']}")
                print(f"   Expected: {item['expected']}")
                print(f"   Actual: {item['actual']}")
                print(f"   Resource ID: {r['id']}")
            
            if len(items) > 10:
                print(f"\n   ... and {len(items) - 10} more")
    else:
        print("✅ No mismatches found! All files are correctly categorized.")
    
    # Print unknown prefixes
    if unknown_prefix:
        print("\n\n" + "=" * 100)
        print(f"UNKNOWN/UNMAPPED PREFIXES ({len(unknown_prefix)} files)")
        print("=" * 100)
        print()
        
        by_prefix = defaultdict(list)
        for item in unknown_prefix:
            by_prefix[item['prefix']].append(item)
        
        for prefix in sorted(by_prefix.keys()):
            items = by_prefix[prefix]
            print(f"\n⚠️  PREFIX: {prefix} ({len(items)} files)")
            print(f"   Currently categorized as:")
            categories = defaultdict(int)
            for item in items:
                categories[item['resource']['category_code']] += 1
            for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
                print(f"      - {cat}: {count} files")
            
            # Show a few examples
            for item in items[:3]:
                print(f"      Example: {item['file_name']}")
    
    # Summary
    print("\n\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Total resources: {len(resources)}")
    print(f"✅ Correctly categorized: {len(correct)} ({len(correct)/len(resources)*100:.1f}%)")
    print(f"❌ Mismatches: {len(mismatches)} ({len(mismatches)/len(resources)*100:.1f}%)")
    print(f"⚠️  Unknown prefixes: {len(unknown_prefix)} ({len(unknown_prefix)/len(resources)*100:.1f}%)")
    
    if mismatches:
        print("\n" + "=" * 100)
        print("RECOMMENDATIONS")
        print("=" * 100)
        print("\nThe following SQL commands will fix the mismatches:")
        print()
        
        # Group mismatches by expected category
        by_expected = defaultdict(list)
        for mismatch in mismatches:
            by_expected[mismatch['expected']].append(mismatch['resource']['id'])
        
        for expected_cat, resource_ids in sorted(by_expected.items()):
            print(f"-- Move {len(resource_ids)} resources to {expected_cat}")
            ids_str = ','.join(map(str, resource_ids))
            print(f"UPDATE resources SET resource_category_id = (SELECT id FROM resource_categories WHERE code = '{expected_cat}') WHERE id IN ({ids_str});")
            print()

if __name__ == '__main__':
    main()
