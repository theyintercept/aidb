#!/usr/bin/env python3
"""
Clean up database and prepare for fresh import
"""

import sqlite3

DATABASE = "learning_sequence_v2.db"

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def main():
    print("=" * 80)
    print("DATABASE CLEANUP")
    print("=" * 80)
    print()
    
    db = get_db()
    
    # Get current counts
    before = db.execute('SELECT COUNT(*) as count FROM resources').fetchone()
    
    print(f"Current resources in database: {before['count']}")
    print()
    
    # Show breakdown
    breakdown = db.execute('''
        SELECT ff.name, COUNT(*) as count
        FROM resources r
        JOIN file_formats ff ON r.file_format_id = ff.id
        GROUP BY ff.id
        ORDER BY count DESC
    ''').fetchall()
    
    print("Current breakdown:")
    for row in breakdown:
        print(f"  {row['name']}: {row['count']}")
    
    print("\n" + "=" * 80)
    print("This will DELETE all current resources and start fresh.")
    print("=" * 80)
    
    response = input("\nProceed with cleanup? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("Operation cancelled.")
        db.close()
        return
    
    # Delete all resources
    db.execute('DELETE FROM resources')
    db.commit()
    
    after = db.execute('SELECT COUNT(*) as count FROM resources').fetchone()
    
    print(f"\n✅ Deleted {before['count']} resources")
    print(f"✅ Database ready for fresh import")
    
    db.close()

if __name__ == '__main__':
    main()
