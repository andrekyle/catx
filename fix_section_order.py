#!/usr/bin/env python3
"""
Script to update the section order in production database to include just_launched
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_section_order():
    """Update the section order to include just_launched section"""
    
    # Import after loading env vars
    from app import app, Settings, db
    
    with app.app_context():
        try:
            # Get or create settings
            settings = Settings.query.first()
            if not settings:
                print("Creating new settings...")
                settings = Settings()
                db.session.add(settings)
                db.session.commit()
                print("✅ Settings created")
            
            # Update section order to include just_launched
            new_section_order = "hero,categories,just_launched,products"
            old_section_order = settings.section_order
            
            print(f"Current section order: {old_section_order}")
            print(f"New section order: {new_section_order}")
            
            settings.section_order = new_section_order
            db.session.commit()
            
            print("✅ Section order updated successfully!")
            
            # Verify the change
            settings = Settings.query.first()
            print(f"Verified section order: {settings.section_order}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating section order: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = update_section_order()
    sys.exit(0 if success else 1)
