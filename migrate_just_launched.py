#!/usr/bin/env python3
"""
Migration script to add just_launched column to products table
"""

import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from app import app, db, Product

def add_just_launched_column():
    """Add just_launched column to products table"""
    
    with app.app_context():
        try:
            # Check if the column already exists
            inspector = db.inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('products')]
            
            if 'just_launched' in columns:
                print("✅ Column 'just_launched' already exists in products table")
                return True
            
            print("🔄 Adding 'just_launched' column to products table...")
            
            # Add the column with default value False
            with db.engine.begin() as connection:
                connection.execute(db.text("""
                    ALTER TABLE products 
                    ADD COLUMN just_launched BOOLEAN DEFAULT FALSE
                """))
            
            print("✅ Successfully added 'just_launched' column to products table")
            
            # Optional: Set some recent products as "just_launched" for testing
            recent_products = Product.query.order_by(Product.id.desc()).limit(3).all()
            for product in recent_products:
                product.just_launched = True
                
            db.session.commit()
            print(f"✅ Set {len(recent_products)} recent products as 'just_launched' for testing")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding just_launched column: {e}")
            db.session.rollback()
            return False

def main():
    """Main function to run the migration"""
    print("Starting migration: Adding just_launched column to products table")
    print("=" * 60)
    
    success = add_just_launched_column()
    
    print("=" * 60)
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
