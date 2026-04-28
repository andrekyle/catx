#!/usr/bin/env python3
"""
Migration script to add banner settings to the Settings table

Adds the following fields:
- banner_enabled (Boolean, default=True)
- banner_image (Text, default='images/banner.png')
- banner_title (String(200), default='')
- banner_subtitle (String(255), default='')
- banner_button_text (String(50), default='')
- banner_button_url (String(255), default='')
- banner_link_url (String(255), default='')
- banner_target_blank (Boolean, default=True)
"""

import os
import sys

def migrate_banner_settings():
    """Add banner settings columns to the Settings table"""
    try:
        from app import app, db, Settings
        
        with app.app_context():
            print("🔧 Starting banner settings migration...")
            print("=" * 50)
            
            # Check if banner_enabled column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('settings')]
            
            if 'banner_enabled' in columns:
                print("✅ Banner settings columns already exist")
                return True
            
            print("📋 Adding banner settings columns to Settings table...")
            
            # Add the new columns using raw SQL
            sql_commands = [
                "ALTER TABLE settings ADD COLUMN banner_enabled BOOLEAN DEFAULT TRUE;",
                "ALTER TABLE settings ADD COLUMN banner_image TEXT DEFAULT 'images/banner.png';",
                "ALTER TABLE settings ADD COLUMN banner_title VARCHAR(200) DEFAULT '';",
                "ALTER TABLE settings ADD COLUMN banner_subtitle VARCHAR(255) DEFAULT '';",
                "ALTER TABLE settings ADD COLUMN banner_button_text VARCHAR(50) DEFAULT '';",
                "ALTER TABLE settings ADD COLUMN banner_button_url VARCHAR(255) DEFAULT '';",
                "ALTER TABLE settings ADD COLUMN banner_link_url VARCHAR(255) DEFAULT '';",
                "ALTER TABLE settings ADD COLUMN banner_target_blank BOOLEAN DEFAULT TRUE;"
            ]
            
            for sql in sql_commands:
                try:
                    with db.engine.connect() as connection:
                        connection.execute(db.text(sql))
                        connection.commit()
                    column_name = sql.split('ADD COLUMN ')[1].split(' ')[0]
                    print(f"✅ Added column: {column_name}")
                except Exception as e:
                    if 'already exists' in str(e):
                        column_name = sql.split('ADD COLUMN ')[1].split(' ')[0]
                        print(f"⚠️ Column {column_name} already exists, skipping")
                    else:
                        print(f"❌ Error adding column: {e}")
                        raise
            
            # Commit the changes
            db.session.commit()
            
            print("\n📊 Verifying migration...")
            
            # Verify the columns were added
            inspector = db.inspect(db.engine)
            new_columns = [col['name'] for col in inspector.get_columns('settings')]
            
            banner_columns = [
                'banner_enabled', 'banner_image', 'banner_title', 'banner_subtitle',
                'banner_button_text', 'banner_button_url', 'banner_link_url', 'banner_target_blank'
            ]
            
            missing_columns = [col for col in banner_columns if col not in new_columns]
            
            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
                return False
            else:
                print("✅ All banner columns successfully added")
            
            # Initialize banner settings for existing settings record
            settings = Settings.query.first()
            if settings:
                print("\n🔧 Initializing banner settings...")
                if not hasattr(settings, 'banner_enabled') or settings.banner_enabled is None:
                    settings.banner_enabled = True
                if not hasattr(settings, 'banner_image') or not settings.banner_image:
                    settings.banner_image = 'images/banner.png'
                if not hasattr(settings, 'banner_title'):
                    settings.banner_title = ''
                if not hasattr(settings, 'banner_subtitle'):
                    settings.banner_subtitle = ''
                if not hasattr(settings, 'banner_button_text'):
                    settings.banner_button_text = ''
                if not hasattr(settings, 'banner_button_url'):
                    settings.banner_button_url = ''
                if not hasattr(settings, 'banner_link_url'):
                    settings.banner_link_url = ''
                if not hasattr(settings, 'banner_target_blank') or settings.banner_target_blank is None:
                    settings.banner_target_blank = True
                
                db.session.commit()
                print("✅ Banner settings initialized")
            else:
                print("⚠️ No settings record found - banner settings will be created when needed")
            
            return True
                
    except Exception as e:
        print(f"❌ Error during banner settings migration: {e}")
        if 'db' in locals():
            db.session.rollback()
        return False

if __name__ == "__main__":
    print("🚀 Banner Settings Migration")
    print("=" * 60)
    
    success = migrate_banner_settings()
    
    print("\n" + "=" * 60)
    
    if success:
        print("✅ Banner settings migration completed successfully!")
        print("🎉 You can now configure banner settings in Admin > Settings")
        print("\n📖 New Features Available:")
        print("- Enable/disable banner section above footer")
        print("- Upload custom banner images")
        print("- Add title and subtitle overlays")
        print("- Configure clickable banner links")
        print("- Add action buttons on banners")
        print("- Control link behavior (new tab/same tab)")
    else:
        print("❌ Banner settings migration failed")
        print("🔧 Please check the errors above and try again")
        sys.exit(1)
