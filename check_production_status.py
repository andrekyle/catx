#!/usr/bin/env python3
"""
Diagnostic script to check production database settings
"""

import os
import sys

def check_production_settings():
    """Check current settings in production database"""
    try:
        from app import app, db, Settings, Product
        
        with app.app_context():
            print("🔍 Checking production database settings...")
            print("=" * 50)
            
            # Check settings
            settings = Settings.query.first()
            if settings:
                print(f"📋 Section order: {settings.section_order}")
                print(f"🎯 Hero enabled: {settings.hero_enabled}")
                print(f"📂 Categories enabled: {settings.categories_enabled}")
                print(f"🛍️ Products enabled: {settings.products_enabled}")
                
                # Check if just_launched is in section order
                if 'just_launched' in settings.section_order:
                    print("✅ just_launched found in section order")
                else:
                    print("❌ just_launched MISSING from section order")
                    print(f"🔧 Need to update from '{settings.section_order}' to 'hero,categories,just_launched,products'")
            else:
                print("❌ No settings found in database")
            
            print("\n" + "=" * 50)
            
            # Check just_launched products
            just_launched_products = Product.query.filter_by(just_launched=True).all()
            print(f"📦 Products marked as just_launched: {len(just_launched_products)}")
            
            if just_launched_products:
                print("✅ Just launched products available:")
                for i, product in enumerate(just_launched_products[:6], 1):
                    print(f"   {i}. {product.name}")
            else:
                print("❌ No products marked as just_launched")
            
            return len(just_launched_products) > 0 and ('just_launched' in settings.section_order if settings else False)
                
    except Exception as e:
        print(f"❌ Error checking production database: {e}")
        return False

if __name__ == "__main__":
    success = check_production_settings()
    print("\n" + "=" * 50)
    
    if success:
        print("✅ Production setup is correct - Just Launched section should be visible")
    else:
        print("⚠️ Production needs configuration update")
        print("💡 Run update_production_section_order.py to fix")
