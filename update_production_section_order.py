#!/usr/bin/env python3
"""
Production Database Fix: Update section order to include just_launched

This script can be run on Vercel or any production environment to fix
the missing Just Launched section on the home page.
"""

import os
import sys

def update_production_section_order():
    """Update section order in production database"""
    try:
        # Import after setting up the environment
        from app import app, db, Settings
        
        with app.app_context():
            settings = Settings.query.first()
            
            if not settings:
                print("❌ No settings found in production database")
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
                print(f"✅ Production section order updated to: {new_section_order}")
                return True
                
            except Exception as e:
                print(f"❌ Error updating production section order: {e}")
                db.session.rollback()
                return False
                
    except Exception as e:
        print(f"❌ Error connecting to production database: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Updating production database section order...")
    print("=" * 50)
    
    success = update_production_section_order()
    
    print("=" * 50)
    if success:
        print("✅ Production database updated successfully!")
        print("🎉 Just Launched section should now appear on live site")
    else:
        print("❌ Failed to update production database")
        sys.exit(1)
