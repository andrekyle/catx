#!/usr/bin/env python3
"""
Fix for Just Launched Section Missing from Home Page

ISSUE: The "Just Launched" section was not appearing on the home page despite:
- Template code being correctly implemented
- Database having 6 products with just_launched=True
- Backend logic properly querying and passing recent_products

ROOT CAUSE: The section_order in Settings table was "hero,categories,products" 
but did not include "just_launched", so the template condition failed.

SOLUTION: Update section_order to include "just_launched" between categories and products.
"""

from app import app, db, Settings

def fix_just_launched_section():
    """Update settings to include just_launched in section order"""
    with app.app_context():
        settings = Settings.query.first()
        
        if not settings:
            print("❌ No settings found in database")
            return False
            
        current_order = settings.section_order
        print(f"📋 Current section order: {current_order}")
        
        # Check if just_launched is already included
        if 'just_launched' in current_order:
            print("✅ just_launched already included in section order")
            return True
            
        # Update section order to include just_launched
        new_section_order = 'hero,categories,just_launched,products'
        settings.section_order = new_section_order
        
        try:
            db.session.commit()
            print(f"✅ Updated section order to: {new_section_order}")
            
            # Verify the change
            settings.refresh()
            if settings.section_order == new_section_order:
                print("✅ Section order successfully updated in database")
                return True
            else:
                print("❌ Failed to verify section order update")
                return False
                
        except Exception as e:
            print(f"❌ Error updating section order: {e}")
            db.session.rollback()
            return False

def verify_just_launched_products():
    """Verify we have products marked as just_launched"""
    with app.app_context():
        recent_products = Product.query.filter_by(just_launched=True).all()
        print(f"📦 Products marked as just_launched: {len(recent_products)}")
        
        if recent_products:
            print("✅ Products available for Just Launched section:")
            for i, product in enumerate(recent_products, 1):
                print(f"   {i}. {product.name}")
            return True
        else:
            print("❌ No products marked as just_launched")
            return False

if __name__ == "__main__":
    print("🔧 Fixing Just Launched Section...")
    print("=" * 50)
    
    # Import here to avoid circular imports
    from app import Product
    
    # Step 1: Verify we have just_launched products
    products_ok = verify_just_launched_products()
    
    # Step 2: Fix section order
    section_ok = fix_just_launched_section()
    
    print("=" * 50)
    if products_ok and section_ok:
        print("✅ Just Launched section fix completed successfully!")
        print("🚀 The section should now appear on the home page")
    else:
        print("❌ Fix incomplete - please check the issues above")
