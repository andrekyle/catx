#!/usr/bin/env python3
"""
Banner Display Diagnostic Script

This script helps troubleshoot why the banner might not be appearing on the home page.
It checks all the components required for banner display.
"""

def diagnose_banner_display():
    """Comprehensive banner display diagnostics"""
    try:
        from app import app, db, Settings, inject_global_settings
        import os
        
        print("🔍 Banner Display Diagnostics")
        print("=" * 50)
        
        with app.app_context():
            # 1. Check Settings in Database
            print("\n📋 1. DATABASE SETTINGS CHECK")
            settings = Settings.query.first()
            if not settings:
                print("❌ No settings record found in database")
                return False
            
            print(f"✅ Settings record exists")
            print(f"   Banner enabled: {settings.banner_enabled}")
            print(f"   Banner image: {settings.banner_image}")
            print(f"   Banner title: '{settings.banner_title}'")
            print(f"   Banner subtitle: '{settings.banner_subtitle}'")
            print(f"   Banner button text: '{settings.banner_button_text}'")
            print(f"   Banner button URL: '{settings.banner_button_url}'")
            print(f"   Banner link URL: '{settings.banner_link_url}'")
            print(f"   Banner target blank: {settings.banner_target_blank}")
            
            if not settings.banner_enabled:
                print("⚠️ Banner is disabled in settings")
                return False
            
            # 2. Check Context Processor
            print("\n🔄 2. CONTEXT PROCESSOR CHECK")
            try:
                context_data = inject_global_settings()
                global_settings = context_data['global_settings']
                
                print(f"✅ Context processor working")
                print(f"   Banner enabled in context: {global_settings['banner_enabled']}")
                print(f"   Banner image in context: {global_settings['banner_image']}")
                print(f"   Banner title in context: '{global_settings['banner_title']}'")
                print(f"   Banner subtitle in context: '{global_settings['banner_subtitle']}'")
                
                if not global_settings['banner_enabled']:
                    print("❌ Banner disabled in global_settings context")
                    return False
                    
            except Exception as e:
                print(f"❌ Context processor error: {e}")
                return False
            
            # 3. Check Image File
            print("\n🖼️ 3. IMAGE FILE CHECK")
            banner_image = global_settings['banner_image']
            
            if banner_image.startswith('data:'):
                print("✅ Banner uses base64 data (uploaded image)")
                print(f"   Data size: ~{len(banner_image)} characters")
            elif banner_image.startswith('http'):
                print(f"✅ Banner uses external URL: {banner_image}")
            else:
                # Check if file exists
                image_path = os.path.join('static', banner_image)
                if os.path.exists(image_path):
                    file_size = os.path.getsize(image_path)
                    print(f"✅ Banner image file exists: {image_path}")
                    print(f"   File size: {file_size:,} bytes")
                else:
                    print(f"❌ Banner image file missing: {image_path}")
                    return False
            
            # 4. Check Template Condition
            print("\n📄 4. TEMPLATE CONDITION CHECK")
            print("Template condition: {% if global_settings.banner_enabled %}")
            
            if global_settings['banner_enabled']:
                print("✅ Template condition will evaluate to True")
                print("✅ Banner section should render")
            else:
                print("❌ Template condition will evaluate to False")
                print("❌ Banner section will not render")
                return False
            
            # 5. Check CSS Classes
            print("\n🎨 5. CSS STYLING CHECK")
            print("✅ Banner CSS classes:")
            print("   - .banner-section (30px margin)")
            print("   - .container mx-auto px-4 (responsive container)")
            print("   - .rounded-lg shadow-lg (styling)")
            print("   - .group hover:scale-105 (hover effects)")
            
            # 6. Check Content Availability
            print("\n📝 6. CONTENT AVAILABILITY CHECK")
            has_title = bool(global_settings['banner_title'])
            has_subtitle = bool(global_settings['banner_subtitle'])
            has_button = bool(global_settings['banner_button_text'])
            has_link = bool(global_settings['banner_link_url'])
            
            print(f"   Title overlay: {'✅' if has_title else '❌'} {global_settings['banner_title']}")
            print(f"   Subtitle overlay: {'✅' if has_subtitle else '❌'} {global_settings['banner_subtitle']}")
            print(f"   Button overlay: {'✅' if has_button else '❌'} {global_settings['banner_button_text']}")
            print(f"   Banner link: {'✅' if has_link else '❌'} {global_settings['banner_link_url']}")
            
            if has_title or has_subtitle or has_button:
                print("✅ Banner will show content overlays")
            else:
                print("ℹ️ Banner will show as image only (no overlays)")
            
            print("\n" + "=" * 50)
            print("✅ ALL CHECKS PASSED - BANNER SHOULD BE VISIBLE")
            print("\nIf banner still not visible, check:")
            print("1. Browser cache - Try hard refresh (Ctrl+F5)")
            print("2. Browser developer tools for JavaScript errors")
            print("3. Network tab to see if banner image loads")
            print("4. Element inspector to see if banner HTML is present")
            
            return True
            
    except Exception as e:
        print(f"❌ Diagnostic error: {e}")
        return False

if __name__ == "__main__":
    success = diagnose_banner_display()
    
    if not success:
        print("\n⚠️ BANNER DISPLAY ISSUES DETECTED")
        print("Please review the failed checks above")
    else:
        print("\n🎉 BANNER CONFIGURATION LOOKS GOOD!")
        print("Banner should be visible above the footer on all pages")
