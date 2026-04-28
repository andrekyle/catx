#!/usr/bin/env python3
"""
Banner Columns Migration Script
Adds missing banner columns to the Settings table in PostgreSQL database
"""

import os
from app import app, db, Settings

def migrate_banner_columns():
    """Add missing banner columns to the Settings table"""
    with app.app_context():
        try:
            print("🔄 Starting banner columns migration...")
            
            # Check if banner columns exist by trying to access them
            settings = Settings.query.first()
            if settings:
                try:
                    # Try to access banner_enabled column
                    _ = settings.banner_enabled
                    print("✅ Banner columns already exist in database")
                    return
                except AttributeError:
                    print("⚠️  Banner columns missing, proceeding with migration...")
            
            # Execute raw SQL to add banner columns
            banner_columns = [
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS banner_enabled BOOLEAN DEFAULT true",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS banner_image TEXT DEFAULT 'images/banner.png'",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS banner_title VARCHAR(200) DEFAULT ''",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS banner_subtitle VARCHAR(255) DEFAULT ''",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS banner_button_text VARCHAR(50) DEFAULT ''",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS banner_button_url VARCHAR(255) DEFAULT ''",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS banner_link_url VARCHAR(255) DEFAULT ''",
                "ALTER TABLE settings ADD COLUMN IF NOT EXISTS banner_target_blank BOOLEAN DEFAULT true"
            ]
            
            for sql in banner_columns:
                try:
                    db.session.execute(sql)
                    print(f"✅ Executed: {sql.split('ADD COLUMN')[1].split(' ')[3]}")
                except Exception as e:
                    print(f"⚠️  Column might already exist: {e}")
            
            db.session.commit()
            print("✅ Banner columns migration completed successfully!")
            
            # Verify the migration worked
            settings = Settings.query.first()
            if settings:
                print(f"✅ Verification: banner_enabled = {getattr(settings, 'banner_enabled', 'NOT FOUND')}")
                print(f"✅ Verification: banner_image = {getattr(settings, 'banner_image', 'NOT FOUND')}")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    migrate_banner_columns()
