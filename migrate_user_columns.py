#!/usr/bin/env python3
"""
Database migration script to add first_name and last_name columns to users table
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Load environment variables
load_dotenv()

def get_database_url():
    """Get the database URL from environment variables"""
    database_url = (os.environ.get('NILEDB_URL') or 
                   os.environ.get('POSTGRES_URL') or 
                   os.environ.get('DATABASE_URL'))
    
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    return database_url

def migrate_user_columns():
    """Add first_name and last_name columns to users table if they don't exist"""
    
    database_url = get_database_url()
    if not database_url:
        print("❌ No database URL found in environment variables")
        return False
    
    try:
        print("🔄 Connecting to database...")
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Connected to database successfully")
        
        # Check if first_name column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'first_name'
        """)
        
        first_name_exists = cursor.fetchone() is not None
        
        # Check if last_name column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'last_name'
        """)
        
        last_name_exists = cursor.fetchone() is not None
        
        # Check if updated_at column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'updated_at'
        """)
        
        updated_at_exists = cursor.fetchone() is not None
        
        migrations_needed = []
        
        if not first_name_exists:
            migrations_needed.append("first_name")
            
        if not last_name_exists:
            migrations_needed.append("last_name")
            
        if not updated_at_exists:
            migrations_needed.append("updated_at")
        
        if not migrations_needed:
            print("✅ All columns already exist, no migration needed")
            return True
        
        print(f"🔄 Adding missing columns: {', '.join(migrations_needed)}")
        
        # Add first_name column if it doesn't exist
        if not first_name_exists:
            print("🔄 Adding first_name column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN first_name VARCHAR(50)
            """)
            print("✅ Added first_name column")
        
        # Add last_name column if it doesn't exist
        if not last_name_exists:
            print("🔄 Adding last_name column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN last_name VARCHAR(50)
            """)
            print("✅ Added last_name column")
        
        # Add updated_at column if it doesn't exist
        if not updated_at_exists:
            print("🔄 Adding updated_at column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            print("✅ Added updated_at column")
        
        # Update existing users with default values based on username
        print("🔄 Updating existing users with default names...")
        cursor.execute("""
            UPDATE users 
            SET first_name = COALESCE(first_name, split_part(username, ' ', 1)),
                last_name = COALESCE(last_name, CASE 
                    WHEN position(' ' in username) > 0 
                    THEN substring(username from position(' ' in username) + 1)
                    ELSE ''
                END)
            WHERE first_name IS NULL OR last_name IS NULL
        """)
        
        print("✅ Updated existing users with default names")
        
        cursor.close()
        conn.close()
        
        print("🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate_user_columns()
    sys.exit(0 if success else 1)
