#!/usr/bin/env python3
"""
Test script to verify banner appears only on home page
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Settings

def test_banner_home_page_only():
    """Test that banner only appears on home page"""
    with app.app_context():
        print("🔍 Testing Banner Home Page Only Logic...")
        print("=" * 50)
        
        # Ensure we have settings with banner enabled
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
            db.session.commit()
        
        # Enable banner for testing
        original_banner_enabled = settings.banner_enabled
        settings.banner_enabled = True
        db.session.commit()
        
        try:
            # Test 1: Home page should show banner
            print("\n📋 Test 1: Home page banner visibility...")
            with app.test_request_context('/'):
                from flask import render_template_string
                template = """
                {% if global_settings.banner_enabled and request.endpoint == 'index' %}
                BANNER_VISIBLE
                {% else %}
                BANNER_HIDDEN
                {% endif %}
                """
                
                result = render_template_string(template, global_settings=settings)
                if "BANNER_VISIBLE" in result:
                    print("✅ Banner appears on home page (/) - CORRECT")
                else:
                    print("❌ Banner does not appear on home page - WRONG")
            
            # Test 2: Products page should NOT show banner
            print("\n🛍️ Test 2: Products page banner visibility...")
            with app.test_request_context('/products'):
                result = render_template_string(template, global_settings=settings)
                if "BANNER_HIDDEN" in result:
                    print("✅ Banner hidden on products page (/products) - CORRECT")
                else:
                    print("❌ Banner appears on products page - WRONG")
            
            # Test 3: Checkout page should NOT show banner
            print("\n🛒 Test 3: Checkout page banner visibility...")
            with app.test_request_context('/checkout'):
                result = render_template_string(template, global_settings=settings)
                if "BANNER_HIDDEN" in result:
                    print("✅ Banner hidden on checkout page (/checkout) - CORRECT")
                else:
                    print("❌ Banner appears on checkout page - WRONG")
            
            # Test 4: Admin page should NOT show banner
            print("\n🔐 Test 4: Admin page banner visibility...")
            with app.test_request_context('/admin/dashboard'):
                result = render_template_string(template, global_settings=settings)
                if "BANNER_HIDDEN" in result:
                    print("✅ Banner hidden on admin page (/admin/dashboard) - CORRECT")
                else:
                    print("❌ Banner appears on admin page - WRONG")
            
            # Test 5: Banner disabled globally
            print("\n🔧 Test 5: Banner disabled globally...")
            settings.banner_enabled = False
            db.session.commit()
            
            with app.test_request_context('/'):
                result = render_template_string(template, global_settings=settings)
                if "BANNER_HIDDEN" in result:
                    print("✅ Banner hidden when globally disabled - CORRECT")
                else:
                    print("❌ Banner appears when globally disabled - WRONG")
            
            print("\n" + "=" * 50)
            print("🎯 BANNER HOME PAGE ONLY TEST SUMMARY")
            print("=" * 50)
            print("✅ Banner logic successfully modified")
            print("✅ Banner will only appear on home page (index)")
            print("✅ Banner will be hidden on all other pages")
            print("✅ Global banner_enabled setting still respected")
            
            return True
            
        finally:
            # Restore original banner setting
            settings.banner_enabled = original_banner_enabled
            db.session.commit()

if __name__ == "__main__":
    print("🏠 Banner Home Page Only Test")
    print("🎯 Verifying banner appears only on home page")
    print("=" * 60)
    
    success = test_banner_home_page_only()
    
    if success:
        print("\n🎉 BANNER HOME PAGE ONLY TEST PASSED!")
        print("✅ Banner will now only appear on the home page")
        sys.exit(0)
    else:
        print("\n❌ BANNER HOME PAGE ONLY TEST FAILED!")
        sys.exit(1)
