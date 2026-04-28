#!/usr/bin/env python3
"""
Migration script to add is_available column to products table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Product

def migrate_product_is_available():
    """Add is_available column to products table"""
    with app.app_context():
        print("🔄 Migrating: Adding is_available column to products table...")
        
        try:
            # Check if the column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('products')]
            
            if 'is_available' in columns:
                print("✅ Column 'is_available' already exists in products table")
                return True
            
            # Add the column using raw SQL
            with db.engine.connect() as conn:
                # Add the column with default value TRUE
                conn.execute(db.text("""
                    ALTER TABLE products 
                    ADD COLUMN is_available BOOLEAN DEFAULT TRUE
                """))
                
                # Update all existing products to be available by default
                conn.execute(db.text("""
                    UPDATE products 
                    SET is_available = TRUE 
                    WHERE is_available IS NULL
                """))
                
                conn.commit()
            
            print("✅ Successfully added is_available column to products table")
            print("✅ All existing products set to available by default")
            
            # Verify the migration
            updated_columns = [col['name'] for col in inspector.get_columns('products')]
            if 'is_available' in updated_columns:
                print("✅ Migration verified successfully")
                return True
            else:
                print("❌ Migration verification failed")
                return False
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return False

if __name__ == "__main__":
    success = migrate_product_is_available()
    if success:
        print("\n🎉 Product is_available migration completed successfully!")
    else:
        print("\n❌ Product is_available migration failed!")
        sys.exit(1)
