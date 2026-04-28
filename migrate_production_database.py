#!/usr/bin/env python3
"""
Production database migration to add is_available column to products table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Product

def migrate_production_is_available():
    """Add is_available column to products table in production"""
    with app.app_context():
        print("🔄 Production Migration: Adding is_available column to products table...")
        
        try:
            # Check if the column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('products')]
            
            if 'is_available' in columns:
                print("✅ Column 'is_available' already exists in production products table")
                
                # Verify all products have is_available set
                products_without_availability = db.session.execute(
                    db.text("SELECT COUNT(*) FROM products WHERE is_available IS NULL")
                ).scalar()
                
                if products_without_availability > 0:
                    print(f"🔄 Updating {products_without_availability} products with NULL is_available...")
                    db.session.execute(
                        db.text("UPDATE products SET is_available = TRUE WHERE is_available IS NULL")
                    )
                    db.session.commit()
                    print("✅ Updated products with NULL is_available to TRUE")
                
                return True
            
            # Add the column using raw SQL
            print("🔄 Adding is_available column to production database...")
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
            
            print("✅ Successfully added is_available column to production products table")
            print("✅ All existing products set to available by default")
            
            # Verify the migration
            updated_columns = [col['name'] for col in inspector.get_columns('products')]
            if 'is_available' in updated_columns:
                print("✅ Production migration verified successfully")
                
                # Count products
                total_products = Product.query.count()
                available_products = Product.query.filter_by(is_available=True).count()
                print(f"✅ Total products: {total_products}")
                print(f"✅ Available products: {available_products}")
                
                return True
            else:
                print("❌ Production migration verification failed")
                return False
            
        except Exception as e:
            print(f"❌ Production migration failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = migrate_production_is_available()
    if success:
        print("\n🎉 Production database migration completed successfully!")
        print("✅ The checkout system should now work on https://shopit-kappa.vercel.app/")
    else:
        print("\n❌ Production database migration failed!")
        sys.exit(1)
