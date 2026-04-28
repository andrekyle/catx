#!/usr/bin/env python3
"""
Script to update section order in production database to include just_launched section
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_section_order():
    """Update the section order to include just_launched"""
    
    database_url = (os.environ.get('NILEDB_URL') or 
                   os.environ.get('POSTGRES_URL') or 
                   os.environ.get('DATABASE_URL'))
    
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    if not database_url:
        print("❌ No database URL found in environment variables")
        return False
    
    try:
        import psycopg2
        print("🔄 Connecting to database...")
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ Connected to database successfully")
        
        # Check current section order
        cursor.execute("SELECT section_order FROM settings LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            current_order = result[0]
            print(f"📋 Current section order: {current_order}")
            
            # Update to include just_launched if not present
            if 'just_launched' not in current_order:
                new_order = "hero,categories,just_launched,products"
                cursor.execute("UPDATE settings SET section_order = %s", (new_order,))
                print(f"✅ Updated section order to: {new_order}")
            else:
                print("✅ Section order already includes just_launched")
        else:
            print("⚠️ No settings found in database")
            # Create initial settings
            cursor.execute("""
                INSERT INTO settings (section_order, hero_enabled, categories_enabled, products_enabled)
                VALUES (%s, %s, %s, %s)
            """, ("hero,categories,just_launched,products", True, True, True))
            print("✅ Created initial settings with just_launched section")
        
        cursor.close()
        conn.close()
        
        print("🎉 Section order update completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating section order: {str(e)}")
        return False

if __name__ == "__main__":
    success = update_section_order()
    sys.exit(0 if success else 1)
