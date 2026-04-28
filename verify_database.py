#!/usr/bin/env python3
"""
Quick verification script to test database connection and schema
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

def verify_database_schema():
    """Verify that the users table has the required columns"""
    
    database_url = (os.environ.get('NILEDB_URL') or 
                   os.environ.get('POSTGRES_URL') or 
                   os.environ.get('DATABASE_URL'))
    
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    if not database_url:
        print("❌ No database URL found")
        return False
    
    try:
        print("🔄 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("✅ Connected successfully")
        
        # Get all columns in users table
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        
        print("\n📋 Users table schema:")
        print("Column Name".ljust(20) + "Data Type".ljust(20) + "Nullable")
        print("-" * 60)
        
        required_columns = {'id', 'username', 'email', 'password_hash', 'first_name', 'last_name', 'is_admin', 'created_at', 'updated_at'}
        found_columns = set()
        
        for column_name, data_type, is_nullable in columns:
            print(f"{column_name}".ljust(20) + f"{data_type}".ljust(20) + f"{is_nullable}")
            found_columns.add(column_name)
        
        missing_columns = required_columns - found_columns
        
        if missing_columns:
            print(f"\n❌ Missing required columns: {', '.join(missing_columns)}")
            return False
        else:
            print(f"\n✅ All required columns present!")
        
        # Test a simple query
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"📊 Total users in database: {user_count}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = verify_database_schema()
    sys.exit(0 if success else 1)
