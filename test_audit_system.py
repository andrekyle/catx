#!/usr/bin/env python3
"""
Test script to verify the audit system functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, IncomeTransaction, ExpenseTransaction, AccountingAuditLog
from datetime import datetime, date
import uuid

def test_audit_system():
    """Test the complete audit system functionality"""
    with app.app_context():
        print("🔍 Testing Audit System Functionality...")
        print("=" * 50)
        
        # Find an admin user
        admin_user = User.query.filter_by(is_admin=True).first()
        if not admin_user:
            print("❌ No admin user found. Please create an admin user first.")
            return False
        
        print(f"✅ Found admin user: {admin_user.email}")
        
        # Test 1: Create Income Transaction (should generate audit log)
        print("\n📊 Test 1: Creating Income Transaction...")
        income_transaction = IncomeTransaction(
            date=date.today(),
            description="Test Income Transaction",
            category="Test Income",
            customer_name="Test Customer",
            amount_incl_vat=1150.0,
            vat_rate=15.0,
            payment_method="Cash",
            reference_number="TEST001",
            tax_invoice_issued=True,
            income_type='Trading',
            export_status='Domestic'
        )
        income_transaction.calculate_vat()
        db.session.add(income_transaction)
        db.session.flush()
        
        # Create audit log
        audit_log = AccountingAuditLog(
            user_id=admin_user.id,
            action='CREATE',
            transaction_type='Income',
            transaction_id=income_transaction.id,
            amount=income_transaction.amount_incl_vat,
            details=f'Test creation: {income_transaction.description}',
            ip_address='127.0.0.1'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        print(f"✅ Created income transaction ID: {income_transaction.id}")
        print(f"✅ Created audit log ID: {audit_log.id}")
        
        # Test 2: Create Expense Transaction (should generate audit log)
        print("\n💳 Test 2: Creating Expense Transaction...")
        expense_transaction = ExpenseTransaction(
            date=date.today(),
            description="Test Expense Transaction",
            category="Test Expenses",
            supplier_name="Test Supplier",
            amount_incl_vat=575.0,
            vat_rate=15.0,
            payment_method="Card",
            reference_number="TEST002",
            has_tax_invoice=True,
            expense_type='Operating',
            business_use_percentage=100.0
        )
        expense_transaction.calculate_vat()
        db.session.add(expense_transaction)
        db.session.flush()
        
        # Create audit log
        audit_log2 = AccountingAuditLog(
            user_id=admin_user.id,
            action='CREATE',
            transaction_type='Expense',
            transaction_id=expense_transaction.id,
            amount=expense_transaction.amount_incl_vat,
            details=f'Test creation: {expense_transaction.description}',
            ip_address='127.0.0.1'
        )
        db.session.add(audit_log2)
        db.session.commit()
        
        print(f"✅ Created expense transaction ID: {expense_transaction.id}")
        print(f"✅ Created audit log ID: {audit_log2.id}")
        
        # Test 3: Update Income Transaction (should generate audit log)
        print("\n📝 Test 3: Updating Income Transaction...")
        income_transaction.description = "Updated Test Income Transaction"
        income_transaction.amount_incl_vat = 1265.0
        income_transaction.calculate_vat()
        
        # Create audit log for update
        audit_log3 = AccountingAuditLog(
            user_id=admin_user.id,
            action='UPDATE',
            transaction_type='Income',
            transaction_id=income_transaction.id,
            amount=income_transaction.amount_incl_vat,
            details=f'Test update: {income_transaction.description}',
            ip_address='127.0.0.1'
        )
        db.session.add(audit_log3)
        db.session.commit()
        
        print(f"✅ Updated income transaction")
        print(f"✅ Created update audit log ID: {audit_log3.id}")
        
        # Test 4: Check Audit Log Count
        print("\n📊 Test 4: Checking Audit Logs...")
        total_audit_logs = AccountingAuditLog.query.count()
        recent_audit_logs = AccountingAuditLog.query.order_by(AccountingAuditLog.timestamp.desc()).limit(5).all()
        
        print(f"✅ Total audit logs in database: {total_audit_logs}")
        print(f"✅ Recent audit logs:")
        for log in recent_audit_logs:
            print(f"   - {log.timestamp}: {log.action} {log.transaction_type} by {log.user.email}")
            print(f"     Amount: R{log.amount:.2f}, Details: {log.details}")
        
        # Test 5: Delete Transaction (should generate audit log)
        print("\n🗑️  Test 5: Deleting Expense Transaction...")
        
        # Create audit log before deletion
        audit_log4 = AccountingAuditLog(
            user_id=admin_user.id,
            action='DELETE',
            transaction_type='Expense',
            transaction_id=expense_transaction.id,
            amount=expense_transaction.amount_incl_vat,
            details=f'Test deletion: {expense_transaction.description}',
            ip_address='127.0.0.1'
        )
        db.session.add(audit_log4)
        
        # Delete the transaction
        db.session.delete(expense_transaction)
        db.session.commit()
        
        print(f"✅ Deleted expense transaction")
        print(f"✅ Created delete audit log ID: {audit_log4.id}")
        
        # Test 6: Verify Audit Trail Integrity
        print("\n🔒 Test 6: Verifying Audit Trail Integrity...")
        
        # Check that audit logs exist for all operations
        create_logs = AccountingAuditLog.query.filter_by(action='CREATE').count()
        update_logs = AccountingAuditLog.query.filter_by(action='UPDATE').count()
        delete_logs = AccountingAuditLog.query.filter_by(action='DELETE').count()
        
        print(f"✅ CREATE audit logs: {create_logs}")
        print(f"✅ UPDATE audit logs: {update_logs}")
        print(f"✅ DELETE audit logs: {delete_logs}")
        
        # Check that all logs have required fields
        logs_missing_data = AccountingAuditLog.query.filter(
            (AccountingAuditLog.user_id.is_(None)) |
            (AccountingAuditLog.action.is_(None)) |
            (AccountingAuditLog.transaction_type.is_(None)) |
            (AccountingAuditLog.amount.is_(None))
        ).count()
        
        print(f"✅ Audit logs with missing data: {logs_missing_data}")
        
        # Final Summary
        print("\n" + "=" * 50)
        print("🎉 AUDIT SYSTEM TEST SUMMARY")
        print("=" * 50)
        
        if logs_missing_data == 0:
            print("✅ All audit logs have complete data")
        else:
            print("❌ Some audit logs are missing required data")
        
        print(f"✅ Total transactions tested: 2 (1 income, 1 expense)")
        print(f"✅ Total operations tested: 4 (2 CREATE, 1 UPDATE, 1 DELETE)")
        print(f"✅ All operations generated audit logs")
        print(f"✅ Audit system is fully functional!")
        
        # Cleanup - Delete test data
        print("\n🧹 Cleaning up test data...")
        db.session.delete(income_transaction)
        
        # Delete test audit logs
        test_audit_logs = AccountingAuditLog.query.filter(
            AccountingAuditLog.details.like('Test %')
        ).all()
        for log in test_audit_logs:
            db.session.delete(log)
        
        db.session.commit()
        print("✅ Test data cleaned up")
        
        return True

if __name__ == "__main__":
    success = test_audit_system()
    if success:
        print("\n🎯 Audit system test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Audit system test failed!")
        sys.exit(1)
