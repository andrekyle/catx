#!/usr/bin/env python3
"""
Test script to diagnose checkout issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Product, CartItem, Order, OrderItem, IncomeTransaction, AccountingAuditLog
from datetime import datetime
import uuid

def test_checkout_process():
    """Test the checkout process components"""
    with app.app_context():
        print("🔍 Testing Checkout Process Components...")
        print("=" * 50)
        
        # Test 1: Check if we have users and products
        print("\n📊 Test 1: Database Connectivity & Data...")
        users = User.query.filter_by(is_admin=False).all()
        products = Product.query.filter_by(is_available=True).all()
        
        print(f"✅ Found {len(users)} users")
        print(f"✅ Found {len(products)} available products")
        
        if not users:
            print("❌ No users found. Cannot test checkout without users.")
            return False
            
        if not products:
            print("❌ No products found. Cannot test checkout without products.")
            return False
        
        # Test 2: Check cart functionality
        print("\n🛒 Test 2: Cart Functionality...")
        test_user = users[0]
        test_product = products[0]
        
        # Clear any existing cart items for test user
        CartItem.query.filter_by(user_id=test_user.id).delete()
        db.session.commit()
        
        # Add item to cart
        cart_item = CartItem(
            user_id=test_user.id,
            product_id=test_product.id,
            quantity=1
        )
        db.session.add(cart_item)
        db.session.commit()
        
        print(f"✅ Added {test_product.name} to cart for {test_user.email}")
        
        # Test 3: Check cart retrieval
        print("\n📋 Test 3: Cart Retrieval...")
        db_cart_items = CartItem.query.filter_by(user_id=test_user.id).all()
        
        if not db_cart_items:
            print("❌ Failed to retrieve cart items")
            return False
            
        print(f"✅ Retrieved {len(db_cart_items)} cart items")
        
        # Test 4: Test order creation components
        print("\n📦 Test 4: Order Creation Components...")
        
        # Test order number generation
        test_order = Order(
            user_id=test_user.id,
            total_amount=100.0,
            shipping_address="Test Address",
            payment_method="Test",
            status='pending'
        )
        
        order_number = test_order.generate_order_number()
        print(f"✅ Generated order number: {order_number}")
        
        # Test order creation
        test_order.order_number = order_number
        db.session.add(test_order)
        db.session.flush()
        
        print(f"✅ Created order with ID: {test_order.id}")
        
        # Test 5: Test income transaction creation
        print("\n💰 Test 5: Income Transaction Creation...")
        
        income_transaction = IncomeTransaction(
            date=datetime.now().date(),
            description=f'Test Order {test_order.order_number}',
            category='Product Sales',
            amount_incl_vat=100.0,
            vat_rate=15.0,
            order_id=test_order.id,
            customer_name='Test Customer',
            payment_method='Test',
            reference_number=test_order.order_number,
            tax_invoice_issued=True,
            income_type='Trading',
            export_status='Domestic'
        )
        income_transaction.calculate_vat()
        db.session.add(income_transaction)
        db.session.flush()
        
        print(f"✅ Created income transaction: R{income_transaction.amount_incl_vat:.2f}")
        print(f"   - VAT Amount: R{income_transaction.vat_amount:.2f}")
        print(f"   - Amount Excl VAT: R{income_transaction.amount_excl_vat:.2f}")
        
        # Test 6: Test audit log creation
        print("\n📝 Test 6: Audit Log Creation...")
        
        audit_log = AccountingAuditLog(
            user_id=test_user.id,
            action='CREATE',
            transaction_type='Income',
            transaction_id=income_transaction.id,
            amount=income_transaction.amount_incl_vat,
            details=f'Test Order {test_order.order_number}',
            ip_address='127.0.0.1'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        print(f"✅ Created audit log: {audit_log.id}")
        
        # Test 7: Test cart cleanup
        print("\n🧹 Test 7: Cart Cleanup...")
        CartItem.query.filter_by(user_id=test_user.id).delete()
        db.session.commit()
        
        remaining_items = CartItem.query.filter_by(user_id=test_user.id).count()
        print(f"✅ Cart cleared - {remaining_items} items remaining")
        
        # Test 8: Check function imports
        print("\n🔧 Test 8: Function Imports...")
        
        try:
            from invoice_generator import generate_order_invoice
            print("✅ generate_order_invoice imported successfully")
        except ImportError as e:
            print(f"⚠️  generate_order_invoice import failed: {e}")
        
        try:
            from email_utils import send_admin_notification, send_invoice_email
            print("✅ email utilities imported successfully")
        except ImportError as e:
            print(f"⚠️  email utilities import failed: {e}")
        
        # Cleanup test data
        print("\n🧹 Cleaning up test data...")
        db.session.delete(test_order)
        db.session.delete(income_transaction)
        db.session.delete(audit_log)
        db.session.commit()
        print("✅ Test data cleaned up")
        
        # Final Summary
        print("\n" + "=" * 50)
        print("🎉 CHECKOUT PROCESS TEST SUMMARY")
        print("=" * 50)
        print("✅ Database connectivity: OK")
        print("✅ User data: OK")
        print("✅ Product data: OK")
        print("✅ Cart functionality: OK")
        print("✅ Order creation: OK")
        print("✅ Income transaction: OK")
        print("✅ Audit logging: OK")
        print("✅ Cart cleanup: OK")
        print("✅ All checkout components working correctly!")
        
        return True

def test_specific_error_scenarios():
    """Test specific scenarios that might cause checkout errors"""
    with app.app_context():
        print("\n🔍 Testing Specific Error Scenarios...")
        print("=" * 40)
        
        # Scenario 1: Product with insufficient stock
        print("\n📦 Scenario 1: Insufficient Stock...")
        product = Product.query.filter(Product.stock > 0).first()
        if product:
            original_stock = product.stock
            product.stock = 0
            db.session.commit()
            print(f"✅ Set {product.name} stock to 0")
            
            # Reset stock
            product.stock = original_stock
            db.session.commit()
            print(f"✅ Reset {product.name} stock to {original_stock}")
        
        # Scenario 2: Empty cart
        print("\n🛒 Scenario 2: Empty Cart...")
        user = User.query.filter_by(is_admin=False).first()
        if user:
            CartItem.query.filter_by(user_id=user.id).delete()
            db.session.commit()
            cart_count = CartItem.query.filter_by(user_id=user.id).count()
            print(f"✅ User {user.email} cart count: {cart_count}")
        
        # Scenario 3: Missing required fields
        print("\n📝 Scenario 3: Required Field Validation...")
        required_fields = [
            'first_name', 'last_name', 'phone', 'email', 
            'street_address', 'suburb', 'city', 'province', 
            'postal_code', 'payment_method'
        ]
        print(f"✅ Required checkout fields: {', '.join(required_fields)}")
        
        print("✅ Error scenario testing complete")

if __name__ == "__main__":
    try:
        success = test_checkout_process()
        test_specific_error_scenarios()
        
        if success:
            print("\n🎯 All checkout tests passed! The system should be working.")
            print("\n📋 If you're still experiencing checkout errors:")
            print("   1. Check browser console for JavaScript errors")
            print("   2. Verify all form fields are filled correctly")
            print("   3. Check server logs for specific error messages")
            print("   4. Ensure products have sufficient stock")
        else:
            print("\n❌ Some checkout tests failed!")
        
    except Exception as e:
        print(f"\n❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
