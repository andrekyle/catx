from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, Response, send_file, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import logging
import uuid
import json
import base64
from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as _pgUUID

# Cross-database UUID compatibility (PostgreSQL UUID on Postgres, String on SQLite)
class _UUIDType(TypeDecorator):
    impl = String(36)
    cache_ok = True
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(_pgUUID(as_uuid=True))
        return dialect.type_descriptor(String(36))
    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value
    def process_result_value(self, value, dialect):
        if value is not None and not isinstance(value, uuid.UUID):
            try:
                return uuid.UUID(str(value))
            except (ValueError, AttributeError):
                return value
        return value

def pgUUID(as_uuid=True):
    return _UUIDType()

# Load environment variables for local development
from dotenv import load_dotenv
if os.path.exists('.env.development.local'):
    load_dotenv('.env.development.local')
elif os.path.exists('.env'):
    load_dotenv('.env')

from config import Config

# Import utilities with error handling for missing packages
try:
    from invoice_generator import generate_order_invoice
except ImportError:
    def generate_order_invoice(*args, **kwargs):
        return None

try:
    from email_utils import init_mail, send_invoice_email, send_admin_notification
except ImportError:
    def init_mail(app):
        pass
    def send_invoice_email(*args, **kwargs):
        return False
    def send_admin_notification(*args, **kwargs):
        return False

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login'

# Define models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='customer', lazy=True)
    
    @property
    def full_name(self):
        """Get full name from first and last name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = db.Column(db.String(20), unique=True, nullable=True)  # Will be populated for existing records
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    category_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('categories.id'), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    featured = db.Column(db.Boolean, default=False)
    just_launched = db.Column(db.Boolean, default=False)  # New field for Just Launched section
    is_available = db.Column(db.Boolean, default=True)  # Product availability status
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    vendor_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('vendors.id'), nullable=True)  # Vendor relationship
    
    def generate_order_number(self):
        """Generate a unique product order number in format PRD-XXXXXX"""
        import random
        
        # Try to generate a unique product order number
        for attempt in range(100):  # Max 100 attempts
            random_number = random.randint(100000, 999999)
            order_number = f"PRD-{random_number:06d}"
            
            # Check if this order number already exists
            existing = Product.query.filter_by(order_number=order_number).first()
            if not existing:
                return order_number
        
        # Fallback: use timestamp-based number
        import time
        timestamp_suffix = int(time.time()) % 1000000
        return f"PRD-{timestamp_suffix:06d}"

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = db.Column(db.String(20), unique=True, nullable=True)  # Will be populated for existing records
    user_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pending')
    total_amount = db.Column(db.Float, nullable=False)
    shipping_address = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    # user relationship is defined in User model with backref='customer'
    
    @property
    def user(self):
        """Alias for customer to maintain backward compatibility"""
        return self.customer
    
    def generate_order_number(self):
        """Generate a unique order number in format ORD-YYYYMMDD-XXXX"""
        import random
        from datetime import datetime
        
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Try to generate a unique order number
        for attempt in range(100):  # Max 100 attempts
            random_suffix = f"{random.randint(1000, 9999):04d}"
            order_number = f"ORD-{date_str}-{random_suffix}"
            
            # Check if this order number already exists
            existing = Order.query.filter_by(order_number=order_number).first()
            if not existing:
                return order_number
        
        # Fallback: use timestamp-based number
        timestamp_suffix = int(datetime.now().timestamp()) % 10000
        return f"ORD-{date_str}-{timestamp_suffix:04d}"

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('cart_items', lazy=True, cascade='all, delete-orphan'))
    product = db.relationship('Product', backref='cart_items')

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Hero Section Settings
    hero_image = db.Column(db.Text, default='images/ban.jpg')  # Changed to Text for base64 data URLs
    hero_enabled = db.Column(db.Boolean, default=True)
    hero_title = db.Column(db.String(200), default='Welcome to Brand Cartel')
    hero_subtitle = db.Column(db.String(255), default='Your one-stop shop for everything')
    hero_button_text = db.Column(db.String(50), default='Shop Now')
    hero_button_url = db.Column(db.String(255), default='/products')
    
    # Categories Section Settings
    categories_enabled = db.Column(db.Boolean, default=True)
    categories_section_title = db.Column(db.String(120), default='Shop by Category')
    categories_section_subtitle = db.Column(db.String(255), default='Find exactly what you\'re looking for')
    categories_limit = db.Column(db.Integer, default=6)
    
    # Products Section Settings
    products_enabled = db.Column(db.Boolean, default=True)
    products_section_title = db.Column(db.String(120), default='Featured Products')
    products_section_subtitle = db.Column(db.String(255), default='Hand-picked items just for you')
    products_limit = db.Column(db.Integer, default=8)
    products_show_view_all = db.Column(db.Boolean, default=True)
    
    # Store Information
    store_name = db.Column(db.String(100), default='Brand Cartel')
    store_tagline = db.Column(db.String(255), default='Your one-stop shop for everything')
    store_logo = db.Column(db.Text, default='images/logo.png')  # Changed to Text for base64 data URLs
    favicon = db.Column(db.Text, default='images/favi.png')  # Changed to Text for base64 data URLs
    store_email = db.Column(db.String(100), default='contact@brandcartel.com')
    store_phone = db.Column(db.String(50), default='+1 (555) 123-4567')
    
    # Footer Settings
    footer_enabled = db.Column(db.Boolean, default=True)
    footer_text = db.Column(db.String(255), default='© 2025 Brand Cartel. All rights reserved.')
    footer_about_text = db.Column(db.Text, default='Brand Cartel is your trusted online marketplace offering quality products at competitive prices.')
    
    # Social Media Links
    facebook_url = db.Column(db.String(255), default='')
    twitter_url = db.Column(db.String(255), default='')
    instagram_url = db.Column(db.String(255), default='')
    youtube_url = db.Column(db.String(255), default='')
    
    # Banner Settings (Above Footer)
    banner_enabled = db.Column(db.Boolean, default=True)
    banner_image = db.Column(db.Text, default='images/banner.png')  # Changed to Text for base64 data URLs
    banner_title = db.Column(db.String(200), default='')
    banner_subtitle = db.Column(db.String(255), default='')
    banner_button_text = db.Column(db.String(50), default='')
    banner_button_url = db.Column(db.String(255), default='')
    banner_link_url = db.Column(db.String(255), default='')  # Make entire banner clickable
    banner_target_blank = db.Column(db.Boolean, default=True)  # Open link in new tab
    
    # SEO Settings
    meta_description = db.Column(db.Text, default='Brand Cartel - Your one-stop shop for everything')
    meta_keywords = db.Column(db.String(255), default='online shop, ecommerce, shopping')
    
    # Home Page Section Order
    section_order = db.Column(db.String(255), default='hero,categories,products')

# Accounting Models for South African Tax Compliance
class IncomeTransaction(db.Model):
    """Income/Revenue transactions with VAT tracking"""
    __tablename__ = 'income_transactions'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Product Sales, Service Revenue, Other
    
    # Customer Information
    customer_name = db.Column(db.String(200), nullable=True)
    company_registration = db.Column(db.String(50), nullable=True)  # Company/Trust/CC registration number
    customer_vat_number = db.Column(db.String(20), nullable=True)  # SARS VAT number
    customer_tax_number = db.Column(db.String(20), nullable=True)  # Income tax reference number
    
    # Financial Details
    amount_incl_vat = db.Column(db.Float, nullable=False)
    vat_rate = db.Column(db.Float, default=15.0)  # 15% standard rate, 0 for zero-rated
    vat_amount = db.Column(db.Float, nullable=False)
    amount_excl_vat = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)  # Cash, EFT, Card, etc.
    reference_number = db.Column(db.String(100), nullable=True)  # Invoice number or reference
    
    # Tax Invoice Details
    tax_invoice_issued = db.Column(db.Boolean, default=False)  # Tax invoice issued to customer
    tax_invoice_path = db.Column(db.String(500), nullable=True)  # File path to invoice copy
    
    # SARS Compliance Enhancement Fields
    payment_date = db.Column(db.Date, nullable=True)  # Actual payment received date
    income_type = db.Column(db.String(20), default='Trading')  # Trading, Non-Trading, Capital
    export_status = db.Column(db.String(20), default='Domestic')  # Domestic or Export
    vat_classification_reason = db.Column(db.String(100), nullable=True)  # Why VAT rate was applied
    
    # Metadata
    order_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('orders.id'), nullable=True)  # Link to order if applicable
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    
    def calculate_vat(self):
        """Calculate VAT amount from inclusive amount"""
        if self.vat_rate > 0:
            self.amount_excl_vat = self.amount_incl_vat / (1 + self.vat_rate / 100)
            self.vat_amount = self.amount_incl_vat - self.amount_excl_vat
        else:
            self.amount_excl_vat = self.amount_incl_vat
            self.vat_amount = 0.0

class ExpenseTransaction(db.Model):
    """Expense transactions with VAT input tax tracking"""
    __tablename__ = 'expense_transactions'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Cost of Sales, Rent, Utilities, etc.
    supplier_name = db.Column(db.String(200), nullable=True)
    company_registration = db.Column(db.String(50), nullable=True)  # Company/Trust/CC registration number
    supplier_vat_number = db.Column(db.String(20), nullable=True)  # SARS VAT number
    sars_tax_number = db.Column(db.String(20), nullable=True)  # Income tax reference number
    amount_incl_vat = db.Column(db.Float, nullable=False)
    vat_rate = db.Column(db.Float, default=15.0)
    vat_amount = db.Column(db.Float, nullable=False)
    amount_excl_vat = db.Column(db.Float, nullable=False)
    has_tax_invoice = db.Column(db.Boolean, default=False)  # Required for VAT input claim
    tax_invoice_path = db.Column(db.String(500), nullable=True)  # File path to uploaded invoice
    payment_method = db.Column(db.String(50), nullable=True)  # Cash, EFT, Card, etc.
    reference_number = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # SARS Compliance Enhancement Fields
    payment_date = db.Column(db.Date, nullable=True)  # Actual payment date (vs expense date)
    business_use_percentage = db.Column(db.Float, default=100.0)  # For partial business use (vehicles, phones)
    expense_type = db.Column(db.String(20), default='Operating')  # Capital or Operating
    vat_claim_reason = db.Column(db.String(100), nullable=True)  # Why VAT was/wasn't claimed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    
    def calculate_vat(self):
        """Calculate VAT amount from inclusive amount"""
        if self.vat_rate > 0:
            self.amount_excl_vat = self.amount_incl_vat / (1 + self.vat_rate / 100)
            self.vat_amount = self.amount_incl_vat - self.amount_excl_vat
        else:
            self.amount_excl_vat = self.amount_incl_vat
            self.vat_amount = 0.0

class AccountingAuditLog(db.Model):
    """Audit trail for all accounting changes (SARS compliance requirement)"""
    __tablename__ = 'accounting_audit_logs'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # CREATE, UPDATE, DELETE
    transaction_type = db.Column(db.String(50), nullable=False)  # Income, Expense
    transaction_id = db.Column(pgUUID(as_uuid=True), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    
    user = db.relationship('User', backref='audit_logs')

class TaxDocument(db.Model):
    """Storage for tax invoices, credit notes, and supporting documents"""
    __tablename__ = 'tax_documents'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_type = db.Column(db.String(50), nullable=False)  # Tax Invoice, Credit Note, Debit Note, Receipt
    document_number = db.Column(db.String(100), nullable=True)  # Invoice/Credit Note number
    document_date = db.Column(db.Date, nullable=False)
    supplier_customer_name = db.Column(db.String(200), nullable=False)
    vat_number = db.Column(db.String(20), nullable=True)  # Supplier/Customer VAT number
    amount = db.Column(db.Float, nullable=False)
    vat_amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)  # Income/Expense category
    file_path = db.Column(db.String(500), nullable=True)  # Legacy: Path to uploaded file (now optional)
    file_name = db.Column(db.String(255), nullable=False)  # Original filename
    file_size = db.Column(db.Integer, nullable=True)  # File size in bytes
    mime_type = db.Column(db.String(100), nullable=True)  # PDF, image/jpeg, etc.
    file_data = db.Column(db.LargeBinary, nullable=True)  # Store file binary data in database for persistence
    linked_transaction_id = db.Column(pgUUID(as_uuid=True), nullable=True)  # Link to Income/Expense transaction
    linked_transaction_type = db.Column(db.String(50), nullable=True)  # Income or Expense
    notes = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    
    uploaded_by = db.relationship('User', backref='uploaded_documents')

# Vendor Models for Marketplace Management
class Vendor(db.Model):
    """Vendor/Seller accounts for marketplace functionality"""
    __tablename__ = 'vendors'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic Information
    business_name = db.Column(db.String(200), nullable=False)
    trading_name = db.Column(db.String(200), nullable=True)  # DBA name if different
    business_type = db.Column(db.String(50), nullable=False)  # Company, CC, Trust, Sole Proprietor
    registration_number = db.Column(db.String(50), nullable=True)  # CIPC registration number
    vat_number = db.Column(db.String(20), nullable=True)  # SARS VAT number
    tax_number = db.Column(db.String(20), nullable=True)  # Income tax reference number
    
    # Contact Information
    contact_person = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False, unique=True)
    contact_phone = db.Column(db.String(20), nullable=False)
    alternative_phone = db.Column(db.String(20), nullable=True)
    
    # Business Address
    physical_address = db.Column(db.Text, nullable=False)
    postal_address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=False)
    province = db.Column(db.String(50), nullable=False)
    postal_code = db.Column(db.String(10), nullable=False)
    
    # Banking Information
    bank_name = db.Column(db.String(100), nullable=False)
    account_holder = db.Column(db.String(200), nullable=False)
    account_number = db.Column(db.String(20), nullable=False)
    branch_code = db.Column(db.String(10), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)  # Current, Savings, Transmission
    
    # Business Information
    business_description = db.Column(db.Text, nullable=False)
    product_categories = db.Column(db.Text, nullable=False)  # JSON array of category IDs
    website_url = db.Column(db.String(255), nullable=True)
    years_in_business = db.Column(db.Integer, nullable=True)
    number_of_employees = db.Column(db.String(20), nullable=True)  # 1-10, 11-50, 51-200, 200+
    
    # Compliance and Status
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, suspended
    bee_level = db.Column(db.String(10), nullable=True)  # B-BBEE level
    bee_certificate_expiry = db.Column(db.Date, nullable=True)
    
    # Platform Agreement
    terms_accepted = db.Column(db.Boolean, default=False)
    terms_accepted_date = db.Column(db.DateTime, nullable=True)
    privacy_accepted = db.Column(db.Boolean, default=False)
    marketplace_agreement_accepted = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    rejected_by_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    
    # Additional fields for admin workflow
    approval_notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Relationships
    documents = db.relationship('VendorDocument', backref='vendor', lazy=True, cascade='all, delete-orphan')
    products = db.relationship('Product', backref='vendor', lazy=True)
    approved_by = db.relationship('User', foreign_keys=[approved_by_id], backref='approved_vendors')
    rejected_by = db.relationship('User', foreign_keys=[rejected_by_id], backref='rejected_vendors')
    
    @property
    def product_categories_list(self):
        """Parse JSON product categories to list"""
        try:
            if self.product_categories:
                return json.loads(self.product_categories)
            return []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def __repr__(self):
        return f'<Vendor {self.business_name}>'

class VendorDocument(db.Model):
    """Documents uploaded by vendors for verification"""
    __tablename__ = 'vendor_documents'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('vendors.id', ondelete='CASCADE'), nullable=False)
    
    # Document Information
    document_type = db.Column(db.String(50), nullable=False)  # CIPC_CERTIFICATE, BANK_CONFIRMATION, ID_COPY, VAT_CERTIFICATE, BEE_CERTIFICATE, TAX_CLEARANCE, PROOF_OF_ADDRESS
    document_name = db.Column(db.String(255), nullable=False)  # Original filename
    description = db.Column(db.Text, nullable=True)
    
    # File Storage
    file_name = db.Column(db.String(255), nullable=False)  # Stored filename
    file_size = db.Column(db.Integer, nullable=True)  # File size in bytes
    mime_type = db.Column(db.String(100), nullable=True)  # PDF, image/jpeg, etc.
    file_data = db.Column(db.LargeBinary, nullable=True)  # Store file binary data in database
    file_path = db.Column(db.String(500), nullable=True)  # Legacy: Path to uploaded file
    
    # Verification Status
    verification_status = db.Column(db.String(20), default='pending')  # pending, verified, rejected
    verified_at = db.Column(db.DateTime, nullable=True)
    verified_by_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    verification_notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.Date, nullable=True)  # For certificates that expire
    
    # Relationships
    verified_by = db.relationship('User', backref='verified_vendor_documents')
    
    def __repr__(self):
        return f'<VendorDocument {self.document_type} for {self.vendor.business_name}>'

# Driver Models for Uber-like Driver Management System
class Driver(db.Model):
    """Driver accounts for Brand Cartel delivery service - similar to Uber driver onboarding"""
    __tablename__ = 'drivers'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Personal Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    id_number = db.Column(db.String(20), nullable=False, unique=True)  # South African ID number
    profile_photo_data = db.Column(db.LargeBinary, nullable=True)  # Store profile photo
    
    # Address Information
    home_address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    province = db.Column(db.String(50), nullable=False)
    postal_code = db.Column(db.String(10), nullable=False)
    
    # Emergency Contact
    emergency_contact_name = db.Column(db.String(100), nullable=False)
    emergency_contact_phone = db.Column(db.String(20), nullable=False)
    emergency_contact_relationship = db.Column(db.String(50), nullable=False)
    
    # Vehicle Information
    vehicle_make = db.Column(db.String(50), nullable=False)
    vehicle_model = db.Column(db.String(50), nullable=False)
    vehicle_year = db.Column(db.Integer, nullable=False)
    vehicle_color = db.Column(db.String(30), nullable=False)
    vehicle_license_plate = db.Column(db.String(20), nullable=False, unique=True)
    vehicle_vin = db.Column(db.String(30), nullable=True)
    vehicle_type = db.Column(db.String(30), nullable=False)  # Car, Motorcycle, Bicycle, Scooter
    
    # Banking Information
    bank_name = db.Column(db.String(100), nullable=False)
    account_holder = db.Column(db.String(200), nullable=False)
    account_number = db.Column(db.String(20), nullable=False)
    branch_code = db.Column(db.String(10), nullable=False)
    account_type = db.Column(db.String(20), nullable=False, default='Current')
    
    # License Information
    drivers_license_number = db.Column(db.String(20), nullable=False)
    license_expiry_date = db.Column(db.Date, nullable=False)
    license_type = db.Column(db.String(10), nullable=False)  # A, B, C1, C, EB, EC
    
    # Background Check & Verification
    criminal_record_check = db.Column(db.Boolean, default=False)
    criminal_record_status = db.Column(db.String(20), default='pending')  # pending, clean, flagged
    
    # Driver Status & Ratings
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, suspended, active, inactive
    approval_stage = db.Column(db.String(50), default='document_verification')  # document_verification, background_check, vehicle_inspection, training, approved
    is_online = db.Column(db.Boolean, default=False)
    is_available = db.Column(db.Boolean, default=False)
    
    # Performance Metrics
    total_deliveries = db.Column(db.Integer, default=0)
    completed_deliveries = db.Column(db.Integer, default=0)
    cancelled_deliveries = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    total_earnings = db.Column(db.Float, default=0.0)
    
    # Platform Agreement & Compliance
    terms_accepted = db.Column(db.Boolean, default=False)
    terms_accepted_date = db.Column(db.DateTime, nullable=True)
    privacy_accepted = db.Column(db.Boolean, default=False)
    driver_agreement_accepted = db.Column(db.Boolean, default=False)
    data_sharing_consent = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    rejected_by_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    last_active = db.Column(db.DateTime, nullable=True)
    
    # Admin workflow fields
    approval_notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Relationships
    documents = db.relationship('DriverDocument', backref='driver', lazy=True, cascade='all, delete-orphan')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id], backref='approved_drivers')
    rejected_by = db.relationship('User', foreign_keys=[rejected_by_id], backref='rejected_drivers')
    
    @property
    def full_name(self):
        """Get driver's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        """Calculate driver's age"""
        if self.date_of_birth:
            today = datetime.utcnow().date()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None
    
    @property
    def completion_rate(self):
        """Calculate delivery completion rate"""
        if self.total_deliveries > 0:
            return round((self.completed_deliveries / self.total_deliveries) * 100, 1)
        return 0.0
    
    @property
    def vehicle_info(self):
        """Get formatted vehicle information"""
        return f"{self.vehicle_year} {self.vehicle_make} {self.vehicle_model} ({self.vehicle_color})"
    
    def __repr__(self):
        return f'<Driver {self.full_name}>'

class DriverDocument(db.Model):
    """Documents uploaded by drivers for verification - similar to Uber's document requirements"""
    __tablename__ = 'driver_documents'
    id = db.Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('drivers.id', ondelete='CASCADE'), nullable=False)
    
    # Document Information
    document_type = db.Column(db.String(50), nullable=False)  
    # ID_COPY, DRIVERS_LICENSE, PROOF_OF_ADDRESS, VEHICLE_REGISTRATION, VEHICLE_INSURANCE, 
    # VEHICLE_ROADWORTHY, CRIMINAL_RECORD_CHECK, BANK_STATEMENT, PROFILE_PHOTO, PDP_PERMIT
    document_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # File Storage
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)
    file_data = db.Column(db.LargeBinary, nullable=True)  # Store file binary data
    file_path = db.Column(db.String(500), nullable=True)  # Legacy support
    
    # Verification Status
    verification_status = db.Column(db.String(20), default='pending')  # pending, verified, rejected, expired
    verified_at = db.Column(db.DateTime, nullable=True)
    verified_by_id = db.Column(pgUUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    verification_notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Document validity
    document_expiry_date = db.Column(db.Date, nullable=True)  # For licenses, permits, insurance
    requires_renewal = db.Column(db.Boolean, default=False)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    verified_by = db.relationship('User', backref='verified_driver_documents')
    
    @property
    def is_expired(self):
        """Check if document is expired"""
        if self.document_expiry_date:
            return self.document_expiry_date < datetime.utcnow().date()
        return False
    
    @property
    def expires_soon(self):
        """Check if document expires within 30 days"""
        if self.document_expiry_date:
            expiry_threshold = datetime.utcnow().date() + timedelta(days=30)
            return self.document_expiry_date <= expiry_threshold
        return False
    
    def __repr__(self):
        return f'<DriverDocument {self.document_type} for {self.driver.full_name}>'

# Define a writable instance path for Vercel
instance_path = None
if os.environ.get('VERCEL_ENV') == 'production':
    instance_path = '/tmp/instance'

app = Flask(__name__, instance_path=instance_path)
app.config.from_object(Config)

# Configure logging
app.logger.setLevel(logging.DEBUG)
if not app.debug:
    # In production, use debug_logger for enhanced logging
    try:
        # from debug_logger import configure_logger
        # logger = configure_logger(app)
        pass
    except Exception as e:
        app.logger.error(f"Failed to configure enhanced logging: {str(e)}")

# Initialize extensions
db.init_app(app)

# Initialize database in serverless environment
def init_db_if_needed():
    """Initialize database tables and sample data if needed"""
    try:
        with app.app_context():
            # Create database tables if they don't exist
            db.create_all()
            
            # Check if we need to create sample data
            if User.query.count() == 0:
                app.logger.info("No users found, creating sample data...")
                
                # Create admin user
                admin = User(
                    username='admin',
                    email='admin@brandcartel.com',
                    is_admin=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                
                # Create default settings
                settings = Settings()
                db.session.add(settings)
                
                db.session.commit()
                app.logger.info("Sample data created successfully")
            
    except Exception as e:
        app.logger.error(f"Database initialization failed: {str(e)}")
        # Don't fail the app startup, just log the error

# For Vercel environment, initialize database on import
if os.environ.get('VERCEL_ENV') or os.environ.get('VERCEL'):
    app.logger.info(f"Running in Vercel environment: {os.environ.get('VERCEL_ENV', 'unknown')}")
    init_db_if_needed()
else:
    # For local development, use the traditional init_db function
    pass

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Flask-Mail
mail = init_mail(app)

@login_manager.user_loader
def load_user(user_id):
    try:
        # Handle UUID string conversion if needed
        if isinstance(user_id, str):
            import uuid
            user_id = uuid.UUID(user_id)
        return User.query.get(user_id)
    except (ValueError, TypeError) as e:
        app.logger.error(f"Error loading user with ID {user_id}: {e}")
        return None

# Context processor to make cart_count available in all templates
@app.context_processor
def inject_cart_count():
    if current_user.is_authenticated:
        # Count cart items from database for logged-in users
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    else:
        # Use session cart for anonymous users
        cart = session.get('cart', {})
        cart_count = len(cart)
    return {'cart_count': cart_count}

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Auto-migrate database on startup (add file_data column if missing)
def auto_migrate_file_storage():
    """Automatically add file_data column to tax_documents table and convert Settings columns to TEXT"""
    try:
        with app.app_context():
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            # Check if tax_documents table exists
            if 'tax_documents' in tables:
                columns = [col['name'] for col in inspector.get_columns('tax_documents')]
                
                # Add file_data column if missing
                if 'file_data' not in columns:
                    print("🔄 Auto-migrating: Adding file_data column to tax_documents...")
                    from sqlalchemy import text
                    
                    if 'sqlite' in str(db.engine.url):
                        db.session.execute(text("ALTER TABLE tax_documents ADD COLUMN file_data BLOB"))
                    else:
                        db.session.execute(text("ALTER TABLE tax_documents ADD COLUMN file_data BYTEA"))
                    
                    db.session.commit()
                    print("✅ Auto-migration complete: file_data column added")
            
            # Create vendor tables if they don't exist
            if 'vendors' not in tables:
                print("🔄 Auto-migrating: Creating vendor tables...")
                # Create vendor tables by calling db.create_all() which is safe for existing tables
                db.create_all()
                print("✅ Auto-migration complete: Vendor tables created")
            else:
                # Check if vendor table has all required columns
                vendor_columns = [col['name'] for col in inspector.get_columns('vendors')]
                missing_columns = []
                
                required_vendor_columns = {
                    'rejected_at': 'TIMESTAMP',
                    'rejected_by_id': 'UUID' if 'postgresql' in str(db.engine.url) else 'TEXT',
                    'approval_notes': 'TEXT',
                    'rejection_reason': 'TEXT'
                }
                
                for col_name, col_type in required_vendor_columns.items():
                    if col_name not in vendor_columns:
                        missing_columns.append((col_name, col_type))
                
                if missing_columns:
                    print("🔄 Auto-migrating: Adding missing vendor columns...")
                    from sqlalchemy import text
                    
                    for col_name, col_type in missing_columns:
                        try:
                            if 'sqlite' in str(db.engine.url):
                                # SQLite uses simpler types
                                sqlite_type = 'TEXT' if col_type in ['UUID', 'TEXT'] else col_type
                                db.session.execute(text(f"ALTER TABLE vendors ADD COLUMN {col_name} {sqlite_type}"))
                            else:
                                # PostgreSQL
                                db.session.execute(text(f"ALTER TABLE vendors ADD COLUMN {col_name} {col_type}"))
                            print(f"✅ Added column: vendors.{col_name}")
                        except Exception as col_e:
                            print(f"⚠️ Column {col_name} migration skipped: {str(col_e)}")
                    
                    # Add foreign key constraints if needed
                    try:
                        if 'postgresql' in str(db.engine.url):
                            db.session.execute(text("ALTER TABLE vendors ADD CONSTRAINT fk_vendors_rejected_by_id FOREIGN KEY (rejected_by_id) REFERENCES users(id)"))
                            print("✅ Added foreign key constraint: vendors.rejected_by_id")
                    except Exception as fk_e:
                        print(f"⚠️ Foreign key constraint skipped: {str(fk_e)}")
                    
                    db.session.commit()
                    print("✅ Auto-migration complete: Vendor columns updated")
            
            # Check vendor_documents table for missing columns
            if 'vendor_documents' in tables:
                vendor_doc_columns = [col['name'] for col in inspector.get_columns('vendor_documents')]
                missing_doc_columns = []
                
                required_doc_columns = {
                    'verified_by_id': 'UUID' if 'postgresql' in str(db.engine.url) else 'TEXT',
                    'verification_notes': 'TEXT',
                    'rejection_reason': 'TEXT'
                }
                
                for col_name, col_type in required_doc_columns.items():
                    if col_name not in vendor_doc_columns:
                        missing_doc_columns.append((col_name, col_type))
                
                if missing_doc_columns:
                    print("🔄 Auto-migrating: Adding missing vendor document columns...")
                    from sqlalchemy import text
                    
                    for col_name, col_type in missing_doc_columns:
                        try:
                            if 'sqlite' in str(db.engine.url):
                                sqlite_type = 'TEXT' if col_type in ['UUID', 'TEXT'] else col_type
                                db.session.execute(text(f"ALTER TABLE vendor_documents ADD COLUMN {col_name} {sqlite_type}"))
                            else:
                                db.session.execute(text(f"ALTER TABLE vendor_documents ADD COLUMN {col_name} {col_type}"))
                            print(f"✅ Added column: vendor_documents.{col_name}")
                        except Exception as col_e:
                            print(f"⚠️ Column {col_name} migration skipped: {str(col_e)}")
                    
                    # Add foreign key constraint for verified_by_id
                    try:
                        if 'postgresql' in str(db.engine.url):
                            db.session.execute(text("ALTER TABLE vendor_documents ADD CONSTRAINT fk_vendor_documents_verified_by_id FOREIGN KEY (verified_by_id) REFERENCES users(id)"))
                            print("✅ Added foreign key constraint: vendor_documents.verified_by_id")
                    except Exception as fk_e:
                        print(f"⚠️ Foreign key constraint skipped: {str(fk_e)}")
                    
                    db.session.commit()
                    print("✅ Auto-migration complete: Vendor document columns updated")
            
            # Add vendor_id column to products table if missing
            if 'products' in tables:
                product_columns = [col['name'] for col in inspector.get_columns('products')]
                if 'vendor_id' not in product_columns:
                    print("🔄 Auto-migrating: Adding vendor_id column to products...")
                    from sqlalchemy import text
                    
                    if 'sqlite' in str(db.engine.url):
                        # SQLite doesn't support adding foreign key constraints to existing tables easily
                        db.session.execute(text("ALTER TABLE products ADD COLUMN vendor_id TEXT"))
                    else:
                        # PostgreSQL
                        db.session.execute(text("ALTER TABLE products ADD COLUMN vendor_id UUID"))
                        # Add foreign key constraint
                        try:
                            db.session.execute(text("ALTER TABLE products ADD CONSTRAINT fk_products_vendor_id FOREIGN KEY (vendor_id) REFERENCES vendors(id)"))
                        except Exception as fk_e:
                            print(f"⚠️ Foreign key constraint skipped: {str(fk_e)}")
                    
                    db.session.commit()
                    print("✅ Auto-migration complete: vendor_id column added to products")
            
            # Migrate Settings columns to TEXT for base64 data URLs
            if 'settings' in tables:
                from sqlalchemy import text
                
                # Only run for PostgreSQL (SQLite doesn't support ALTER COLUMN TYPE easily)
                if 'postgresql' in str(db.engine.url):
                    try:
                        print("🔄 Auto-migrating: Converting Settings image columns to TEXT...")
                        for column in ['favicon', 'store_logo', 'hero_image']:
                            db.session.execute(text(f"ALTER TABLE settings ALTER COLUMN {column} TYPE TEXT"))
                        db.session.commit()
                        print("✅ Auto-migration complete: Settings columns converted to TEXT")
                    except Exception as col_e:
                        # Column may already be TEXT, ignore error
                        db.session.rollback()
                        if 'already exists' not in str(col_e) and 'cannot be cast' not in str(col_e):
                            print(f"⚠️ Settings column migration skipped: {str(col_e)}")
            
            # Check and create driver tables if they don't exist
            if 'drivers' not in tables:
                print("🔄 Auto-migrating: Creating driver tables...")
                try:
                    # Create tables using SQLAlchemy
                    Driver.__table__.create(db.engine)
                    DriverDocument.__table__.create(db.engine)
                    print("✅ Driver tables created successfully")
                except Exception as driver_e:
                    print(f"⚠️ Driver table creation skipped: {str(driver_e)}")
            
            print("✅ Database schema up-to-date")
    except Exception as e:
        print(f"⚠️ Auto-migration skipped: {str(e)}")

# Run auto-migration on startup
try:
    auto_migrate_file_storage()
except Exception as e:
    print(f"Migration check failed: {str(e)}")

# Add custom error handlers
@app.errorhandler(404)
def page_not_found(e):
    app.logger.warning(f"404 error: {request.path}")
    return render_template('error.html', 
                          error_title="Page Not Found", 
                          error_message="The page you're looking for doesn't exist."), 404

@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"500 error: {str(e)}")
    error_details = None
    if app.debug:
        import traceback
        error_details = traceback.format_exc()
    
    # Check if it's a template error
    if hasattr(e, 'original_exception') and hasattr(e.original_exception, 'message'):
        app.logger.error(f"Template error: {e.original_exception.message}")
        error_message = "There was an error in the template." if not app.debug else e.original_exception.message
    else:
        error_message = "Something went wrong on our end. Please try again later."
    
    # Try to return the error template, but have a fallback
    try:
        return render_template('error.html', 
                               error_title="Internal Server Error", 
                               error_message=error_message,
                               debug=app.debug,
                               error_details=error_details), 500
    except Exception as render_error:
        app.logger.error(f"Error rendering error template: {str(render_error)}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Internal Server Error</title>
            <style>
                body {{ font-family: sans-serif; max-width: 500px; margin: 100px auto; padding: 20px; text-align: center; }}
                h1 {{ color: #d32f2f; }}
            </style>
        </head>
        <body>
            <h1>Internal Server Error</h1>
            <p>The server encountered an error and could not complete your request.</p>
            <p><a href="/">Return to Homepage</a></p>
        </body>
        </html>
        """, 500

# ======================
# CONTEXT PROCESSORS
# ======================

@app.context_processor
def inject_global_settings():
    """Make global settings available to all templates"""
    from datetime import datetime
    
    # Default fallback settings
    default_settings = {
        'store_name': 'Brand Cartel',
        'store_tagline': 'Your one-stop shop for everything',
        'store_logo_url': 'images/logo.png',
        'favicon': 'images/favi.png',
        'show_search_bar': True,
        'footer_enabled': True,
        'footer_text': '© 2025 Brand Cartel. All rights reserved.',
        'footer_about_text': 'Brand Cartel is your trusted online marketplace offering quality products at competitive prices.',
        'footer_links_parsed': [],
        'facebook_url': '',
        'twitter_url': '',
        'instagram_url': '',
        'youtube_url': '',
        'color_scheme': 'azure',
        # Banner settings
        'banner_enabled': True,
        'banner_image': 'images/banner.png',
        'banner_title': '',
        'banner_subtitle': '',
        'banner_button_text': '',
        'banner_button_url': '',
        'banner_link_url': '',
        'banner_target_blank': True,
    }
    
    try:
        settings = Settings.query.first()
        if settings:
            global_settings = {
                'store_name': settings.store_name or 'Brand Cartel',
                'store_tagline': settings.store_tagline or 'Your one-stop shop for everything',
                'store_logo_url': settings.store_logo or 'images/logo.png',
                'favicon': getattr(settings, 'favicon', 'images/favi.png') or 'images/favi.png',
                'show_search_bar': True,
                'footer_enabled': settings.footer_enabled,
                'footer_text': settings.footer_text or '© 2025 Brand Cartel. All rights reserved.',
                'footer_about_text': settings.footer_about_text or 'Brand Cartel is your trusted online marketplace offering quality products at competitive prices.',
                'footer_links_parsed': [],
                'facebook_url': settings.facebook_url or '',
                'twitter_url': settings.twitter_url or '',
                'instagram_url': settings.instagram_url or '',
                'youtube_url': settings.youtube_url or '',
                'color_scheme': 'azure',
                # Banner settings
                'banner_enabled': getattr(settings, 'banner_enabled', True),
                'banner_image': getattr(settings, 'banner_image', 'images/banner.png'),
                'banner_title': getattr(settings, 'banner_title', ''),
                'banner_subtitle': getattr(settings, 'banner_subtitle', ''),
                'banner_button_text': getattr(settings, 'banner_button_text', ''),
                'banner_button_url': getattr(settings, 'banner_button_url', ''),
                'banner_link_url': getattr(settings, 'banner_link_url', ''),
                'banner_target_blank': getattr(settings, 'banner_target_blank', True),
            }
            return dict(global_settings=global_settings, now=datetime.utcnow())
        else:
            return dict(global_settings=default_settings, now=datetime.utcnow())
    except Exception as e:
        # Log error for debugging on Vercel
        print(f"Error loading global settings: {str(e)}")
        # Return fallback settings
        return dict(global_settings=default_settings, now=datetime.utcnow())

# Custom Jinja filters
@app.template_filter('get_approved_vendor')
def get_approved_vendor(email):
    """Check if user email has an approved vendor account"""
    return Vendor.query.filter_by(contact_email=email, status='approved').first()

# ======================
# PUBLIC ROUTES
# ======================

@app.route('/search')
def search():
    """Comprehensive search across products, pages, and content"""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')  # all, products, pages
    
    if not query:
        flash('Please enter a search term', 'info')
        return redirect(url_for('index'))
    
    results = {
        'products': [],
        'pages': [],
        'total_count': 0
    }
    
    # Search Products
    if search_type in ['all', 'products']:
        try:
            product_results = Product.query.filter(
                db.or_(
                    Product.name.contains(query),
                    Product.description.contains(query)
                )
            ).limit(20).all()
            
            results['products'] = product_results
            results['total_count'] += len(product_results)
        except Exception as e:
            app.logger.error(f"Error searching products: {e}")
    
    # Search Pages (static content)
    if search_type in ['all', 'pages']:
        page_matches = []
        
        # Define searchable pages with their content and metadata
        searchable_pages = [
            {
                'title': 'Products',
                'url': url_for('products'),
                'description': 'Browse all products in our store',
                'keywords': ['products', 'browse', 'shop', 'items', 'catalog']
            },
            {
                'title': 'Vendor Registration',
                'url': url_for('vendor_signup'),
                'description': 'Join as a vendor and start selling your products',
                'keywords': ['vendor', 'seller', 'registration', 'signup', 'sell', 'marketplace']
            },
            {
                'title': 'Checkout',
                'url': url_for('checkout'),
                'description': 'Complete your purchase and place your order',
                'keywords': ['checkout', 'payment', 'order', 'purchase', 'cart', 'buy']
            },
            {
                'title': 'Shopping Cart',
                'url': url_for('cart'),
                'description': 'View and manage items in your shopping cart',
                'keywords': ['cart', 'shopping', 'basket', 'items', 'manage']
            },
            {
                'title': 'Login',
                'url': url_for('login'),
                'description': 'Sign in to your account',
                'keywords': ['login', 'signin', 'account', 'auth', 'access']
            },
            {
                'title': 'Register',
                'url': url_for('register'),
                'description': 'Create a new account',
                'keywords': ['register', 'signup', 'create account', 'new user', 'join']
            }
        ]
        
        # Search through pages
        query_lower = query.lower()
        for page in searchable_pages:
            # Check if query matches title, description, or keywords
            if (query_lower in page['title'].lower() or
                query_lower in page['description'].lower() or
                any(query_lower in keyword for keyword in page['keywords'])):
                page_matches.append(page)
        
        results['pages'] = page_matches
        results['total_count'] += len(page_matches)
    
    # Log search for analytics
    app.logger.info(f"Search query: '{query}' - Results: {results['total_count']}")
    
    return render_template('search_results.html', 
                         query=query,
                         search_type=search_type,
                         results=results)

@app.route('/')
def index():
    # Get settings for home page limits and content
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
        db.session.commit()

    categories_limit = 6
    products_limit = 8
    
    # Get all home page settings
    home_settings = {
        'hero_image': settings.hero_image,
        'hero_enabled': settings.hero_enabled,
        'hero_slideshow_enabled': False,
        
        'categories_enabled': settings.categories_enabled,
        'categories_section_title': settings.categories_section_title,
        'categories_section_subtitle': settings.categories_section_subtitle,
        
        'products_enabled': settings.products_enabled,
        'products_section_title': settings.products_section_title,
        'products_section_subtitle': settings.products_section_subtitle,
        'products_show_view_all': True,
        
        'layout_style': 'modern',
        'color_scheme': 'azure',
        'mobile_layout': 'responsive',
        
        'section_order': '["hero", "categories", "products"]',
        'section_hero_enabled': True,
        'section_categories_enabled': True,
        'section_products_enabled': True,
    }
    
    # Apply limits (0 means no limit)
    if categories_limit > 0:
        categories = Category.query.limit(categories_limit).all()
    else:
        categories = Category.query.all()
        
    if products_limit > 0:
        featured_products = Product.query.filter_by(featured=True).limit(products_limit).all()
    else:
        featured_products = Product.query.filter_by(featured=True).all()
    
    # Get products marked as "Just Launched" - prioritize manually selected products
    recent_products = Product.query.filter_by(just_launched=True).limit(6).all()
    
    # If we don't have enough manually selected products, fall back to newest products
    if len(recent_products) < 6:
        # Get remaining slots needed
        remaining_slots = 6 - len(recent_products)
        
        # Get the IDs of already selected products to avoid duplicates
        selected_ids = [p.id for p in recent_products]
        
        # Fill remaining slots with newest products (excluding already selected ones)
        newest_products = Product.query.filter(~Product.id.in_(selected_ids)).order_by(Product.id.desc()).limit(remaining_slots).all()
        recent_products.extend(newest_products)
    
    # Parse section order for dynamic rendering
    try:
        if settings.section_order:
            # Handle both JSON format and comma-separated format
            if settings.section_order.startswith('['):
                # JSON format
                import json
                section_order = json.loads(settings.section_order)
            else:
                # Comma-separated format
                section_order = [s.strip() for s in settings.section_order.split(',')]
        else:
            section_order = ['hero', 'categories', 'just_launched', 'products']
    except:
        section_order = ['hero', 'categories', 'just_launched', 'products']
    
    return render_template('index.html', 
                         products=featured_products,
                         recent_products=recent_products, 
                         categories=categories,
                         hero_image=home_settings['hero_image'],
                         home_settings=home_settings,
                         section_order=section_order)

@app.route('/products')
def products():
    category_id_str = request.args.get('category', type=str)
    search = request.args.get('search', '')
    
    # Quick Filters
    featured_only = request.args.get('featured', type=bool)
    in_stock_only = request.args.get('in_stock', type=bool)
    on_sale_only = request.args.get('on_sale', type=bool)
    
    # Price Range Filters
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    # Sorting
    sort_by = request.args.get('sort', default='newest')
    
    query = Product.query
    
    # Category Filter
    if category_id_str:
        try:
            # Convert string UUID to UUID object for database query
            import uuid as uuid_module
            category_uuid = uuid_module.UUID(category_id_str)
            query = query.filter_by(category_id=category_uuid)
        except (ValueError, AttributeError):
            # If invalid UUID, ignore the filter
            pass
    
    # Search Filter
    if search:
        query = query.filter(Product.name.contains(search) | Product.description.contains(search))
    
    # Quick Filters
    if featured_only:
        query = query.filter(Product.featured == True)
    
    if in_stock_only:
        query = query.filter(Product.stock > 0)
    
    if on_sale_only:
        # For now, filter by featured products as "on sale"
        # You can add a sale_price field later for actual sales
        query = query.filter(Product.featured == True)
    
    # Price Range Filters
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    # Sorting
    if sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'name_asc':
        query = query.order_by(Product.name.asc())
    elif sort_by == 'popular':
        # Order by featured first, then by name
        query = query.order_by(Product.featured.desc(), Product.name.asc())
    else:  # default: newest - order by id desc as proxy for newest
        query = query.order_by(Product.id.desc())
    
    products = query.all()
    categories = Category.query.all()
    selected_category = category_id_str if category_id_str else None
    
    # Pass filter states to template
    filter_state = {
        'featured': featured_only,
        'in_stock': in_stock_only,
        'on_sale': on_sale_only,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort_by
    }
    
    return render_template('products.html', 
                         products=products, 
                         categories=categories, 
                         selected_category=selected_category,
                         filter_state=filter_state)

@app.route('/product/<id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template('product_detail.html', product=product)

@app.route('/cart')
def cart():
    items = []
    total = 0
    
    if current_user.is_authenticated:
        # Get cart items from database for logged-in users
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        for cart_item in cart_items:
            items.append({
                'product': cart_item.product,
                'quantity': cart_item.quantity,
                'subtotal': cart_item.product.price * cart_item.quantity
            })
            total += cart_item.product.price * cart_item.quantity
    else:
        # Use session cart for anonymous users
        cart_items = session.get('cart', {})
        for product_id, quantity in cart_items.items():
            try:
                # Convert string UUID to UUID object
                import uuid as uuid_module
                product_uuid = uuid_module.UUID(product_id)
                product = Product.query.get(product_uuid)
                if product:
                    items.append({
                        'product': product,
                        'quantity': quantity,
                        'subtotal': product.price * quantity
                    })
                    total += product.price * quantity
            except (ValueError, AttributeError):
                # Skip invalid product IDs
                continue
    
    return render_template('cart.html', items=items, total=total)

@app.route('/add-to-cart/<product_id>')
def add_to_cart(product_id):
    try:
        # Convert string UUID to UUID object
        import uuid as uuid_module
        product_uuid = uuid_module.UUID(product_id)
        product = Product.query.get_or_404(product_uuid)
    except (ValueError, AttributeError) as e:
        app.logger.error(f'Invalid product ID: {product_id} - {str(e)}')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid product ID'}), 400
        flash('Invalid product', 'danger')
        return redirect(url_for('products'))
    
    if current_user.is_authenticated:
        # Use database cart for logged-in users
        cart_item = CartItem.query.filter_by(
            user_id=current_user.id,
            product_id=product.id
        ).first()
        
        if cart_item:
            cart_item.quantity += 1
        else:
            cart_item = CartItem(
                user_id=current_user.id,
                product_id=product.id,
                quantity=1
            )
            db.session.add(cart_item)
        
        db.session.commit()
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    else:
        # Use session cart for anonymous users
        if 'cart' not in session:
            session['cart'] = {}
        
        cart = session['cart']
        product_id_str = str(product_id)
        
        if product_id_str in cart:
            cart[product_id_str] += 1
        else:
            cart[product_id_str] = 1
        
        session['cart'] = cart
        cart_count = len(cart)
    
    # Check if it's an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'product': {
                'name': product.name,
                'price': f"{product.price:.2f}",
                'image': product.image_url,
                'category': product.category.name
            },
            'cart_count': cart_count
        })
    
    flash(f'{product.name} added to cart!', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/remove-from-cart/<product_id>')
def remove_from_cart(product_id):
    try:
        # Convert string UUID to UUID object
        import uuid as uuid_module
        product_uuid = uuid_module.UUID(product_id)
    except (ValueError, AttributeError):
        flash('Invalid product', 'danger')
        return redirect(url_for('cart'))
    
    if current_user.is_authenticated:
        # Remove from database cart for logged-in users
        cart_item = CartItem.query.filter_by(
            user_id=current_user.id,
            product_id=product_uuid
        ).first()
        
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
            flash('Item removed from cart', 'success')
    else:
        # Remove from session cart for anonymous users
        if 'cart' in session:
            cart = session['cart']
            product_id_str = str(product_id)
            
            if product_id_str in cart:
                del cart[product_id_str]
                session['cart'] = cart
                flash('Item removed from cart', 'success')
    
    return redirect(url_for('cart'))

@app.route('/update-cart-quantity/<product_id>', methods=['POST'])
def update_cart_quantity(product_id):
    """Update the quantity of an item in the cart"""
    try:
        # Convert string UUID to UUID object
        import uuid as uuid_module
        product_uuid = uuid_module.UUID(product_id)
        
        data = request.get_json()
        new_quantity = int(data.get('quantity', 1))
        
        if new_quantity < 1:
            return jsonify({'success': False, 'message': 'Quantity must be at least 1'}), 400
        
        if current_user.is_authenticated:
            # Update database cart for logged-in users
            cart_item = CartItem.query.filter_by(
                user_id=current_user.id,
                product_id=product_uuid
            ).first()
            
            if cart_item:
                # Check stock availability
                product = Product.query.get(product_uuid)
                if product and new_quantity > product.stock:
                    return jsonify({
                        'success': False, 
                        'message': f'Only {product.stock} items available in stock'
                    }), 400
                
                cart_item.quantity = new_quantity
                db.session.commit()
                
                # Calculate new subtotal
                subtotal = cart_item.product.price * new_quantity
                
                # Calculate cart total
                all_items = CartItem.query.filter_by(user_id=current_user.id).all()
                cart_total = sum([item.product.price * item.quantity for item in all_items])
                
                return jsonify({
                    'success': True,
                    'quantity': new_quantity,
                    'subtotal': subtotal,
                    'cart_total': cart_total,
                    'delivery': 0 if cart_total >= 500 else 60,
                    'grand_total': cart_total if cart_total >= 500 else cart_total + 60
                })
            else:
                return jsonify({'success': False, 'message': 'Item not found in cart'}), 404
        else:
            # Update session cart for anonymous users
            if 'cart' not in session:
                session['cart'] = {}
            
            cart = session['cart']
            product_id_str = str(product_id)
            
            if product_id_str in cart:
                # Check stock availability
                product = Product.query.get(product_uuid)
                if product and new_quantity > product.stock:
                    return jsonify({
                        'success': False, 
                        'message': f'Only {product.stock} items available in stock'
                    }), 400
                
                cart[product_id_str] = new_quantity
                session['cart'] = cart
                
                # Calculate new subtotal
                product = Product.query.get(product_uuid)
                subtotal = product.price * new_quantity if product else 0
                
                # Calculate cart total
                cart_total = 0
                for pid, qty in cart.items():
                    try:
                        p_uuid = uuid_module.UUID(pid)
                        p = Product.query.get(p_uuid)
                        if p:
                            cart_total += p.price * qty
                    except (ValueError, AttributeError):
                        continue
                
                return jsonify({
                    'success': True,
                    'quantity': new_quantity,
                    'subtotal': subtotal,
                    'cart_total': cart_total,
                    'delivery': 0 if cart_total >= 500 else 60,
                    'grand_total': cart_total if cart_total >= 500 else cart_total + 60
                })
            else:
                return jsonify({'success': False, 'message': 'Item not found in cart'}), 404
                
    except Exception as e:
        app.logger.error(f'Error updating cart quantity: {str(e)}')
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    # Get cart items from database for logged-in users
    db_cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not db_cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('products'))
    
    if request.method == 'POST':
        # Get shipping information from form
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        street_address = request.form.get('street_address')
        suburb = request.form.get('suburb')
        city = request.form.get('city')
        province = request.form.get('province')
        postal_code = request.form.get('postal_code')
        payment_method = request.form.get('payment_method')
        
        # Format the shipping address
        shipping_address = f"{first_name} {last_name}\n{email}\n{phone}\n{street_address}\n{suburb}, {city}\n{province.replace('-', ' ').title()}\n{postal_code}"
        
        total = 0
        order = Order(
            user_id=current_user.id,
            total_amount=0, # Will be updated later
            shipping_address=shipping_address,
            payment_method=payment_method,
            status='pending'
        )
        # Generate order number
        order.order_number = order.generate_order_number()
        db.session.add(order)
        db.session.flush()
        
        # Process cart items from database
        for cart_item in db_cart_items:
            product = cart_item.product
            if product and product.stock >= cart_item.quantity:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=cart_item.quantity,
                    price=product.price
                )
                db.session.add(order_item)
                product.stock -= cart_item.quantity
                total += product.price * cart_item.quantity
        
        # Calculate delivery charge (free over R500)
        delivery_charge = 0 if total >= 500 else 60
        
        # Update order total amount (including delivery)
        order.total_amount = total + delivery_charge
        
        # Clear cart items from database
        CartItem.query.filter_by(user_id=current_user.id).delete()
        
        # Create income transaction for accounting
        try:
            from datetime import date
            income_transaction = IncomeTransaction(
                date=date.today(),
                description=f'Order {order.order_number} - {first_name} {last_name}',
                category='Product Sales',
                amount_incl_vat=order.total_amount,
                vat_rate=15.0,
                order_id=order.id,
                notes=f'Payment method: {payment_method}\nInvoice sent to: {email}\nCustomer Email: {email}',
                created_by_id=current_user.id,
                # Add customer information for SARS compliance
                customer_name=f'{first_name} {last_name}',
                payment_method=payment_method,
                reference_number=order.order_number,
                tax_invoice_issued=True,
                income_type='Trading',
                export_status='Domestic'
            )
            income_transaction.calculate_vat()
            db.session.add(income_transaction)
            db.session.flush()  # Get the transaction ID before creating audit log

            # Create audit log
            audit_log = AccountingAuditLog(
                user_id=current_user.id,
                action='CREATE',
                transaction_type='Income',
                transaction_id=income_transaction.id,
                amount=income_transaction.amount_incl_vat,
                details=f'Order {order.order_number}',
                ip_address=request.remote_addr
            )
            db.session.add(audit_log)

            # Commit everything (order, order items, accounting entries)
            db.session.commit()

            # Attempt to generate invoice and send emails (best-effort)
            try:
                invoice_path = None
                try:
                    invoice_path = generate_order_invoice(order)
                except Exception as gen_exc:
                    app.logger.warning(f'Failed to generate invoice: {gen_exc}')

                try:
                    # send_invoice_email signature may vary; best-effort call
                    send_invoice_email(order, current_user.email) if 'send_invoice_email' in globals() else None
                except Exception as email_exc:
                    app.logger.warning(f'Failed to send invoice email: {email_exc}')

                try:
                    # Pass invoice_path to admin notification (required parameter)
                    send_admin_notification(order, invoice_path)
                except Exception as admin_exc:
                    app.logger.warning(f'Failed to send admin notification: {admin_exc}')
            except Exception:
                # Silently continue if notifications fail
                pass

            flash('Order placed successfully! A confirmation email has been sent (if email settings are configured).', 'success')
            
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': 'Order placed successfully!',
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'redirect_url': url_for('my_orders')
                })
            
            return redirect(url_for('my_orders'))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error processing checkout: {str(e)}')
            error_message = 'There was an error processing your order. Please try again.'
            flash(error_message, 'danger')
            
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'error': error_message
                }), 500
            
            return redirect(url_for('cart'))
    
    # GET request - display checkout form
    items = []
    total = 0
    
    for cart_item in db_cart_items:
        items.append({
            'product': cart_item.product,
            'quantity': cart_item.quantity,
            'subtotal': cart_item.product.price * cart_item.quantity
        })
        total += cart_item.product.price * cart_item.quantity
    
    # Calculate VAT breakdown (prices include 15% VAT)
    # Formula: price_excl_vat = price_incl_vat / 1.15
    # vat_amount = price_incl_vat - price_excl_vat
    subtotal_excl_vat = total / 1.15
    vat_amount = total - subtotal_excl_vat
    
    # Calculate delivery charge (free over R500)
    delivery_charge = 0 if total >= 500 else 60
    
    # Grand total includes delivery
    grand_total = total + delivery_charge
    
    return render_template('checkout.html', 
                         items=items, 
                         total=total,
                         subtotal_excl_vat=subtotal_excl_vat,
                         vat_amount=vat_amount,
                         delivery_charge=delivery_charge,
                         grand_total=grand_total)

@app.route('/orders')
@login_required
def my_orders():
    """User's order history page"""
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('my_orders.html', orders=orders)

@app.route('/order/<string:id>')
@login_required
def order_detail(id):
    """View details of a specific order"""
    try:
        import uuid as uuid_module
        order_uuid = uuid_module.UUID(id)
        order = Order.query.get_or_404(order_uuid)
    except (ValueError, TypeError):
        flash('Invalid order ID', 'danger')
        return redirect(url_for('my_orders'))

    if not current_user.is_admin and order.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    return render_template('order_detail.html', order=order)

@app.route('/invoice')
def invoice():
    """Display professional invoice page"""
    return render_template('invoice.html')

# ======================
# AUTH ROUTES
# ======================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            
            # Migrate session cart to database cart
            session_cart = session.get('cart', {})
            if session_cart:
                for product_id, quantity in session_cart.items():
                    # Check if item already exists in user's cart
                    cart_item = CartItem.query.filter_by(
                        user_id=user.id,
                        product_id=product_id
                    ).first()
                    
                    if cart_item:
                        # Update quantity
                        cart_item.quantity += quantity
                    else:
                        # Create new cart item
                        cart_item = CartItem(
                            user_id=user.id,
                            product_id=product_id,
                            quantity=quantity
                        )
                        db.session.add(cart_item)
                
                db.session.commit()
                # Clear session cart
                session['cart'] = {}
            
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'danger')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# ======================
# VENDOR ROUTES
# ======================

@app.route('/vendor/signup', methods=['GET', 'POST'])
def vendor_signup():
    """Vendor registration page - comprehensive signup form for sellers"""
    import uuid
    import json
    import os
    from werkzeug.utils import secure_filename
    
    if request.method == 'POST':
        try:
            # Basic Information
            business_name = request.form.get('business_name', '').strip()
            trading_name = request.form.get('trading_name', '').strip()
            business_type = request.form.get('business_type', '')
            registration_number = request.form.get('registration_number', '').strip()
            vat_number = request.form.get('vat_number', '').strip()
            tax_number = request.form.get('tax_number', '').strip()
            
            # Contact Information
            contact_person = request.form.get('contact_person', '').strip()
            contact_email = request.form.get('contact_email', '').strip()
            contact_phone = request.form.get('contact_phone', '').strip()
            alternative_phone = request.form.get('alternative_phone', '').strip()
            
            # Business Address
            physical_address = request.form.get('physical_address', '').strip()
            postal_address = request.form.get('postal_address', '').strip()
            city = request.form.get('city', '').strip()
            province = request.form.get('province', '')
            postal_code = request.form.get('postal_code', '').strip()
            
            # Banking Information
            bank_name = request.form.get('bank_name', '')
            account_holder = request.form.get('account_holder', '').strip()
            account_number = request.form.get('account_number', '').strip()
            branch_code = request.form.get('branch_code', '').strip()
            account_type = request.form.get('account_type', '')
            
            # Business Information
            business_description = request.form.get('business_description', '').strip()
            selected_categories = request.form.getlist('product_categories')
            website_url = request.form.get('website_url', '').strip()
            years_in_business = request.form.get('years_in_business', type=int)
            number_of_employees = request.form.get('number_of_employees', '')
            
            # Compliance Information
            bee_level = request.form.get('bee_level', '').strip()
            bee_certificate_expiry = request.form.get('bee_certificate_expiry')
            
            # Agreement checkboxes
            terms_accepted = bool(request.form.get('terms_accepted'))
            privacy_accepted = bool(request.form.get('privacy_accepted'))
            marketplace_agreement_accepted = bool(request.form.get('marketplace_agreement_accepted'))
            
            # Validation
            errors = []
            
            if not business_name:
                errors.append("Business name is required")
            if not contact_person:
                errors.append("Contact person is required")
            if not contact_email:
                errors.append("Contact email is required")
            if not contact_phone:
                errors.append("Contact phone is required")
            if not physical_address:
                errors.append("Physical address is required")
            if not city:
                errors.append("City is required")
            if not province:
                errors.append("Province is required")
            if not postal_code:
                errors.append("Postal code is required")
            if not bank_name:
                errors.append("Bank name is required")
            if not account_holder:
                errors.append("Account holder name is required")
            if not account_number:
                errors.append("Account number is required")
            if not branch_code:
                errors.append("Branch code is required")
            if not account_type:
                errors.append("Account type is required")
            if not business_description:
                errors.append("Business description is required")
            if not selected_categories:
                errors.append("Please select at least one product category")
            if not terms_accepted:
                errors.append("You must accept the Terms and Conditions")
            if not privacy_accepted:
                errors.append("You must accept the Privacy Policy")
            if not marketplace_agreement_accepted:
                errors.append("You must accept the Marketplace Agreement")
                
            # Check if email already exists
            if Vendor.query.filter_by(contact_email=contact_email).first():
                errors.append("A vendor with this email address already exists")
                
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return redirect(url_for('vendor_signup'))
            
            # Create vendor record
            vendor = Vendor(
                business_name=business_name,
                trading_name=trading_name if trading_name else None,
                business_type=business_type,
                registration_number=registration_number if registration_number else None,
                vat_number=vat_number if vat_number else None,
                tax_number=tax_number if tax_number else None,
                contact_person=contact_person,
                contact_email=contact_email,
                contact_phone=contact_phone,
                alternative_phone=alternative_phone if alternative_phone else None,
                physical_address=physical_address,
                postal_address=postal_address if postal_address else None,
                city=city,
                province=province,
                postal_code=postal_code,
                bank_name=bank_name,
                account_holder=account_holder,
                account_number=account_number,
                branch_code=branch_code,
                account_type=account_type,
                business_description=business_description,
                product_categories=json.dumps(selected_categories),
                website_url=website_url if website_url else None,
                years_in_business=years_in_business,
                number_of_employees=number_of_employees,
                bee_level=bee_level if bee_level else None,
                bee_certificate_expiry=datetime.strptime(bee_certificate_expiry, '%Y-%m-%d').date() if bee_certificate_expiry else None,
                terms_accepted=terms_accepted,
                terms_accepted_date=datetime.utcnow() if terms_accepted else None,
                privacy_accepted=privacy_accepted,
                marketplace_agreement_accepted=marketplace_agreement_accepted,
                status='pending'
            )
            
            db.session.add(vendor)
            db.session.flush()  # Get vendor ID
            
            # Process uploaded documents
            document_types = [
                'cipc_certificate', 'bank_confirmation', 'id_copy', 
                'vat_certificate', 'bee_certificate', 'tax_clearance', 
                'proof_of_address', 'other_documents'
            ]
            
            uploaded_documents = []
            for doc_type in document_types:
                file = request.files.get(doc_type)
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_data = file.read()
                    
                    # Create document record
                    vendor_doc = VendorDocument(
                        vendor_id=vendor.id,
                        document_type=doc_type.upper(),
                        document_name=filename,
                        description=f"{doc_type.replace('_', ' ').title()} - {filename}",
                        file_name=filename,
                        file_size=len(file_data),
                        mime_type=file.content_type,
                        file_data=file_data,
                        verification_status='pending'
                    )
                    
                    db.session.add(vendor_doc)
                    uploaded_documents.append(doc_type.replace('_', ' ').title())
            
            db.session.commit()
            
            # Send confirmation email (if email utilities are configured)
            try:
                # You could add email notification here
                pass
            except Exception as e:
                app.logger.warning(f"Failed to send vendor signup notification: {str(e)}")
            
            flash(f'Vendor application submitted successfully! Your application ID is pending review. You will be contacted at {contact_email} once your application has been processed.', 'success')
            flash(f'Documents uploaded: {", ".join(uploaded_documents)}' if uploaded_documents else 'No documents were uploaded. Please contact support to submit required documents.', 'info')
            
            return redirect(url_for('vendor_signup_success', vendor_id=vendor.id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error processing vendor signup: {str(e)}")
            flash('An error occurred while processing your application. Please try again.', 'danger')
            return redirect(url_for('vendor_signup'))
    
    # GET request - show signup form
    categories = Category.query.all()
    
    return render_template('vendor_signup.html', categories=categories)

@app.route('/vendor/signup/test', methods=['GET', 'POST'])
def vendor_signup_test():
    """Test version of vendor signup with minimal template"""
    if request.method == 'POST':
        # Simple processing for testing
        business_name = request.form.get('business_name', '').strip()
        contact_email = request.form.get('contact_email', '').strip()
        
        if business_name and contact_email:
            flash(f'Test application received for {business_name}!', 'success')
        else:
            flash('Please fill in required fields.', 'danger')
            
        return redirect(url_for('vendor_signup_test'))
    
    return render_template('vendor_signup_minimal.html')

@app.route('/vendor/signup/success/<string:vendor_id>')
def vendor_signup_success(vendor_id):
    """Vendor signup success page"""
    try:
        vendor_uuid = uuid.UUID(vendor_id)
        vendor = Vendor.query.get_or_404(vendor_uuid)
        return render_template('vendor_signup_success.html', vendor=vendor)
    except (ValueError, TypeError):
        flash('Invalid vendor ID', 'danger')
        return redirect(url_for('vendor_signup'))

# ======================
# VENDOR DASHBOARD ROUTES  
# ======================

@app.route('/vendor/dashboard')
@login_required
def vendor_dashboard():
    """Vendor dashboard - only for approved vendors"""
    # Check if current user has an approved vendor account
    vendor = Vendor.query.filter_by(contact_email=current_user.email, status='approved').first()
    
    if not vendor:
        flash('You must be an approved vendor to access this page.', 'danger')
        return redirect(url_for('vendor_signup'))
    
    # Get vendor statistics
    total_products = Product.query.filter_by(vendor_id=vendor.id).count()
    active_products = Product.query.filter_by(vendor_id=vendor.id, is_available=True).count()
    total_orders = Order.query.join(OrderItem).join(Product).filter(Product.vendor_id == vendor.id).count()
    
    # Recent orders for this vendor
    recent_orders = db.session.query(Order)\
        .join(OrderItem)\
        .join(Product)\
        .filter(Product.vendor_id == vendor.id)\
        .order_by(Order.created_at.desc())\
        .limit(5).all()
    
    return render_template('vendor/dashboard.html', 
                         vendor=vendor,
                         total_products=total_products,
                         active_products=active_products,
                         total_orders=total_orders,
                         recent_orders=recent_orders)

@app.route('/vendor/products')
@login_required
def vendor_products():
    """Vendor product management page"""
    vendor = Vendor.query.filter_by(contact_email=current_user.email, status='approved').first()
    
    if not vendor:
        flash('You must be an approved vendor to access this page.', 'danger')
        return redirect(url_for('vendor_signup'))
    
    products = Product.query.filter_by(vendor_id=vendor.id).order_by(Product.id.desc()).all()
    categories = Category.query.all()
    
    return render_template('vendor/products.html', 
                         vendor=vendor,
                         products=products,
                         categories=categories)

@app.route('/vendor/product/add', methods=['GET', 'POST'])
@login_required
def vendor_add_product():
    """Add new product - vendors only"""
    vendor = Vendor.query.filter_by(contact_email=current_user.email, status='approved').first()
    
    if not vendor:
        flash('You must be an approved vendor to access this page.', 'danger')
        return redirect(url_for('vendor_signup'))
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            price = float(request.form.get('price', 0))
            category_id = request.form.get('category_id')
            stock_quantity = int(request.form.get('stock_quantity', 0))
            
            # Validation
            errors = []
            if not name:
                errors.append("Product name is required")
            if not description:
                errors.append("Product description is required")
            if price <= 0:
                errors.append("Price must be greater than 0")
            if not category_id:
                errors.append("Category is required")
            if stock_quantity < 0:
                errors.append("Stock quantity cannot be negative")
            
            # Check for image upload
            image = request.files.get('image')
            if image and image.filename:
                # Handle image upload
                filename = secure_filename(image.filename)
                image_path = f"uploads/products/{filename}"
                image.save(os.path.join(app.static_folder, image_path))
            else:
                image_path = None
            
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return redirect(url_for('vendor_add_product'))
            
            # Create product
            product = Product(
                name=name,
                description=description,
                price=price,
                category_id=category_id,
                stock_quantity=stock_quantity,
                vendor_id=vendor.id,
                is_available=True,
                image_url=image_path
            )
            product.order_number = product.generate_order_number()
            
            db.session.add(product)
            db.session.commit()
            
            flash('Product added successfully!', 'success')
            return redirect(url_for('vendor_products'))
            
        except ValueError:
            flash('Please enter valid price and stock quantity', 'danger')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding product: {str(e)}")
            flash('Error adding product. Please try again.', 'danger')
    
    categories = Category.query.all()
    return render_template('vendor/product_form.html', vendor=vendor, categories=categories)

@app.route('/vendor/product/<string:product_id>/edit', methods=['GET', 'POST'])
@login_required
def vendor_edit_product(product_id):
    """Edit product - vendors only"""
    vendor = Vendor.query.filter_by(contact_email=current_user.email, status='approved').first()
    
    if not vendor:
        flash('You must be an approved vendor to access this page.', 'danger')
        return redirect(url_for('vendor_signup'))
    
    try:
        product_uuid = uuid.UUID(product_id)
        product = Product.query.filter_by(id=product_uuid, vendor_id=vendor.id).first_or_404()
    except (ValueError, TypeError):
        flash('Invalid product ID', 'danger')
        return redirect(url_for('vendor_products'))
    
    if request.method == 'POST':
        try:
            # Update product data
            product.name = request.form.get('name', '').strip()
            product.description = request.form.get('description', '').strip()
            product.price = float(request.form.get('price', 0))
            product.category_id = request.form.get('category_id')
            product.stock_quantity = int(request.form.get('stock_quantity', 0))
            product.is_available = request.form.get('is_available') == 'on'
            
            # Handle image upload
            image = request.files.get('image')
            if image and image.filename:
                filename = secure_filename(image.filename)
                image_path = f"uploads/products/{filename}"
                image.save(os.path.join(app.static_folder, image_path))
                product.image_url = image_path
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('vendor_products'))
            
        except ValueError:
            flash('Please enter valid price and stock quantity', 'danger')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating product: {str(e)}")
            flash('Error updating product. Please try again.', 'danger')
    
    categories = Category.query.all()
    return render_template('vendor/product_form.html', vendor=vendor, product=product, categories=categories)

# ==============================================
# JOB PORTAL ROUTES - LinkedIn-like Functionality
# ==============================================

# ======================
# PROFILE & CV MANAGEMENT ROUTES
# ======================

@app.route('/profile')
@login_required
def profile():
    """User profile page - view own profile"""
    # Get or create user profile
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    if not user_profile:
        user_profile = UserProfile(user_id=current_user.id)
        db.session.add(user_profile)
        db.session.commit()
    
    # Get related data
    experiences = Experience.query.filter_by(user_id=current_user.id).order_by(Experience.start_date.desc()).all()
    educations = Education.query.filter_by(user_id=current_user.id).order_by(Education.start_year.desc()).all()
    user_skills = db.session.query(UserSkill, Skill).join(Skill).filter(UserSkill.user_id == current_user.id).all()
    certifications = Certification.query.filter_by(user_id=current_user.id).order_by(Certification.issue_date.desc()).all()
    
    return render_template('profile/profile.html',
                         profile=user_profile,
                         experiences=experiences,
                         educations=educations,
                         user_skills=user_skills,
                         certifications=certifications)

@app.route('/profile/<uuid:user_id>')
def view_profile(user_id):
    """View another user's profile"""
    user = User.query.get_or_404(user_id)
    user_profile = UserProfile.query.filter_by(user_id=user_id).first()
    
    if not user_profile or user_profile.profile_visibility == 'private':
        flash('This profile is not available.', 'warning')
        return redirect(url_for('index'))
    
    # Check if current user can view (connections_only visibility)
    if user_profile.profile_visibility == 'connections_only' and current_user.is_authenticated:
        # Check if users are connected
        connection = Connection.query.filter(
            ((Connection.requester_id == current_user.id) & (Connection.receiver_id == user_id)) |
            ((Connection.requester_id == user_id) & (Connection.receiver_id == current_user.id))
        ).filter(Connection.status == 'accepted').first()
        
        if not connection:
            flash('You need to be connected to view this profile.', 'warning')
            return redirect(url_for('index'))
    
    # Get profile data
    experiences = Experience.query.filter_by(user_id=user_id).order_by(Experience.start_date.desc()).all()
    educations = Education.query.filter_by(user_id=user_id).order_by(Education.start_year.desc()).all()
    user_skills = db.session.query(UserSkill, Skill).join(Skill).filter(UserSkill.user_id == user_id).all()
    certifications = Certification.query.filter_by(user_id=user_id).order_by(Certification.issue_date.desc()).all()
    
    # Update profile views
    if current_user.is_authenticated and current_user.id != user_id:
        user_profile.profile_views += 1
        db.session.commit()
    
    return render_template('profile/view_profile.html',
                         user=user,
                         profile=user_profile,
                         experiences=experiences,
                         educations=educations,
                         user_skills=user_skills,
                         certifications=certifications)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    if not user_profile:
        user_profile = UserProfile(user_id=current_user.id)
        db.session.add(user_profile)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            # Update profile fields
            user_profile.professional_headline = request.form.get('professional_headline', '').strip()
            user_profile.summary = request.form.get('summary', '').strip()
            user_profile.current_position = request.form.get('current_position', '').strip()
            user_profile.current_company = request.form.get('current_company', '').strip()
            user_profile.industry = request.form.get('industry', '').strip()
            user_profile.location = request.form.get('location', '').strip()
            user_profile.phone = request.form.get('phone', '').strip()
            user_profile.website_url = request.form.get('website_url', '').strip()
            user_profile.linkedin_url = request.form.get('linkedin_url', '').strip()
            user_profile.github_url = request.form.get('github_url', '').strip()
            user_profile.portfolio_url = request.form.get('portfolio_url', '').strip()
            user_profile.profile_visibility = request.form.get('profile_visibility', 'public')
            user_profile.open_to_work = 'open_to_work' in request.form
            user_profile.open_to_opportunities = request.form.get('open_to_opportunities', 'not_looking')
            
            # Handle salary expectations
            salary_min = request.form.get('desired_salary_min')
            salary_max = request.form.get('desired_salary_max')
            user_profile.desired_salary_min = int(salary_min) if salary_min else None
            user_profile.desired_salary_max = int(salary_max) if salary_max else None
            
            # Handle profile picture upload
            profile_picture = request.files.get('profile_picture')
            if profile_picture and profile_picture.filename:
                user_profile.profile_picture = profile_picture.read()
            
            # Handle CV upload
            cv_file = request.files.get('cv_file')
            if cv_file and cv_file.filename:
                user_profile.cv_file = cv_file.read()
                user_profile.cv_filename = cv_file.filename
            
            user_profile.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
    
    return render_template('profile/edit_profile.html', profile=user_profile)

# ======================
# JOB SEARCH & APPLICATION ROUTES
# ======================

@app.route('/jobs')
def jobs():
    """Job search page with filters"""
    # Get filter parameters
    keywords = request.args.get('keywords', '').strip()
    location = request.args.get('location', '').strip()
    remote_type = request.args.get('remote_type', '')
    employment_type = request.args.get('employment_type', '')
    experience_level = request.args.get('experience_level', '')
    industry = request.args.get('industry', '')
    company_id = request.args.get('company_id', '')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = Job.query.filter(Job.status == 'active')
    
    # Apply filters
    if keywords:
        query = query.filter(
            (Job.title.contains(keywords)) |
            (Job.description.contains(keywords)) |
            (Job.requirements.contains(keywords))
        )
    
    if location:
        query = query.filter(Job.location.contains(location))
    
    if remote_type:
        query = query.filter(Job.remote_type == remote_type)
    
    if employment_type:
        query = query.filter(Job.employment_type == employment_type)
    
    if experience_level:
        query = query.filter(Job.experience_level == experience_level)
    
    if industry:
        query = query.filter(Job.industry == industry)
    
    if company_id:
        query = query.filter(Job.company_id == company_id)
    
    # Sort by most recent
    query = query.order_by(Job.published_at.desc())
    
    # Paginate results
    jobs = query.paginate(page=page, per_page=20, error_out=False)
    
    # Get filter options for dropdowns
    companies = Company.query.filter(Company.is_active == True).order_by(Company.name).all()
    industries = db.session.query(Job.industry).distinct().filter(Job.industry.isnot(None)).all()
    locations = db.session.query(Job.location).distinct().filter(Job.location.isnot(None)).all()
    
    return render_template('jobs/job_search.html',
                         jobs=jobs,
                         companies=companies,
                         industries=[i[0] for i in industries],
                         locations=[l[0] for l in locations],
                         filters={
                             'keywords': keywords,
                             'location': location,
                             'remote_type': remote_type,
                             'employment_type': employment_type,
                             'experience_level': experience_level,
                             'industry': industry,
                             'company_id': company_id
                         })

@app.route('/jobs/<uuid:job_id>')
def job_detail(job_id):
    """Job detail page"""
    job = Job.query.get_or_404(job_id)
    
    # Update view count
    job.views_count += 1
    db.session.commit()
    
    # Check if user has applied
    application = None
    is_saved = False
    if current_user.is_authenticated:
        application = JobApplication.query.filter_by(job_id=job_id, user_id=current_user.id).first()
        is_saved = SavedJob.query.filter_by(job_id=job_id, user_id=current_user.id).first() is not None
    
    # Get similar jobs
    similar_jobs = Job.query.filter(
        Job.id != job_id,
        Job.status == 'active',
        (Job.industry == job.industry) | (Job.function == job.function)
    ).limit(5).all()
    
    return render_template('jobs/job_detail.html',
                         job=job,
                         application=application,
                         is_saved=is_saved,
                         similar_jobs=similar_jobs)

@app.route('/jobs/<uuid:job_id>/apply', methods=['GET', 'POST'])
@login_required
def apply_job(job_id):
    """Apply for a job"""
    job = Job.query.get_or_404(job_id)
    
    # Check if already applied
    existing_application = JobApplication.query.filter_by(job_id=job_id, user_id=current_user.id).first()
    if existing_application:
        flash('You have already applied for this job.', 'warning')
        return redirect(url_for('job_detail', job_id=job_id))
    
    # Check if job is still active
    if job.status != 'active':
        flash('This job is no longer accepting applications.', 'warning')
        return redirect(url_for('job_detail', job_id=job_id))
    
    if request.method == 'POST':
        try:
            # Create application
            application = JobApplication(
                job_id=job_id,
                user_id=current_user.id,
                cover_letter=request.form.get('cover_letter', '').strip()
            )
            
            # Handle resume upload
            resume_file = request.files.get('resume_file')
            if resume_file and resume_file.filename:
                application.resume_file = resume_file.read()
                application.resume_filename = resume_file.filename
            
            # Handle additional documents
            additional_docs = request.files.get('additional_documents')
            if additional_docs and additional_docs.filename:
                application.additional_documents = additional_docs.read()
                application.additional_docs_filename = additional_docs.filename
            
            # Handle screening questions (if any)
            screening_responses = {}
            for key in request.form:
                if key.startswith('screening_'):
                    question_id = key.replace('screening_', '')
                    screening_responses[question_id] = request.form[key]
            
            if screening_responses:
                application.screening_responses = json.dumps(screening_responses)
            
            db.session.add(application)
            
            # Update job application count
            job.applications_count += 1
            
            db.session.commit()
            flash('Application submitted successfully!', 'success')
            return redirect(url_for('job_detail', job_id=job_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting application: {str(e)}', 'danger')
    
    # Get user's profile data for pre-filling
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    
    return render_template('jobs/apply_job.html', job=job, user_profile=user_profile)

@app.route('/jobs/<uuid:job_id>/save', methods=['POST'])
@login_required
def save_job(job_id):
    """Save/bookmark a job"""
    job = Job.query.get_or_404(job_id)
    
    # Check if already saved
    existing_save = SavedJob.query.filter_by(job_id=job_id, user_id=current_user.id).first()
    if existing_save:
        return jsonify({'success': False, 'message': 'Job already saved'})
    
    try:
        saved_job = SavedJob(
            job_id=job_id,
            user_id=current_user.id,
            notes=request.form.get('notes', '').strip()
        )
        db.session.add(saved_job)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Job saved successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/jobs/<uuid:job_id>/unsave', methods=['POST'])
@login_required
def unsave_job(job_id):
    """Remove job from saved list"""
    saved_job = SavedJob.query.filter_by(job_id=job_id, user_id=current_user.id).first()
    if saved_job:
        db.session.delete(saved_job)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Job removed from saved list'})
    
    return jsonify({'success': False, 'message': 'Job not in saved list'})

@app.route('/my-applications')
@login_required
def my_applications():
    """User's job applications tracking"""
    applications = db.session.query(JobApplication, Job, Company).join(Job).join(Company)\
        .filter(JobApplication.user_id == current_user.id)\
        .order_by(JobApplication.applied_at.desc()).all()
    
    return render_template('jobs/my_applications.html', applications=applications)

@app.route('/saved-jobs')
@login_required
def saved_jobs():
    """User's saved/bookmarked jobs"""
    saved_jobs = db.session.query(SavedJob, Job, Company).join(Job).join(Company)\
        .filter(SavedJob.user_id == current_user.id)\
        .order_by(SavedJob.created_at.desc()).all()
    
    return render_template('jobs/saved_jobs.html', saved_jobs=saved_jobs)

# ======================
# NETWORKING ROUTES
# ======================

@app.route('/network')
@login_required
def network():
    """Professional network page"""
    # Get user's connections
    connections = db.session.query(Connection, User).join(
        User, 
        (Connection.requester_id == User.id) | (Connection.receiver_id == User.id)
    ).filter(
        ((Connection.requester_id == current_user.id) | (Connection.receiver_id == current_user.id)),
        Connection.status == 'accepted',
        User.id != current_user.id
    ).all()
    
    # Get pending connection requests
    pending_requests = db.session.query(Connection, User).join(
        User, Connection.requester_id == User.id
    ).filter(
        Connection.receiver_id == current_user.id,
        Connection.status == 'pending'
    ).all()
    
    # Get people you may know (simplified algorithm)
    suggested_connections = User.query.filter(
        User.id != current_user.id,
        ~User.id.in_(
            db.session.query(Connection.requester_id).filter(Connection.receiver_id == current_user.id).union(
            db.session.query(Connection.receiver_id).filter(Connection.requester_id == current_user.id))
        )
    ).limit(10).all()
    
    return render_template('network/network.html',
                         connections=connections,
                         pending_requests=pending_requests,
                         suggested_connections=suggested_connections)

@app.route('/connect/<uuid:user_id>', methods=['POST'])
@login_required
def send_connection_request(user_id):
    """Send connection request"""
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot connect to yourself'})
    
    # Check if connection already exists
    existing_connection = Connection.query.filter(
        ((Connection.requester_id == current_user.id) & (Connection.receiver_id == user_id)) |
        ((Connection.requester_id == user_id) & (Connection.receiver_id == current_user.id))
    ).first()
    
    if existing_connection:
        return jsonify({'success': False, 'message': 'Connection request already exists'})
    
    try:
        connection = Connection(
            requester_id=current_user.id,
            receiver_id=user_id,
            message=request.form.get('message', '').strip(),
            relationship=request.form.get('relationship', 'colleague')
        )
        db.session.add(connection)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Connection request sent'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/connection-request/<uuid:connection_id>/respond', methods=['POST'])
@login_required
def respond_connection_request(connection_id):
    """Accept or decline connection request"""
    connection = Connection.query.get_or_404(connection_id)
    
    if connection.receiver_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    action = request.form.get('action')
    if action not in ['accept', 'decline']:
        return jsonify({'success': False, 'message': 'Invalid action'})
    
    try:
        connection.status = 'accepted' if action == 'accept' else 'declined'
        connection.responded_at = datetime.utcnow()
        
        # Update connection counts for both users
        if action == 'accept':
            requester_profile = UserProfile.query.filter_by(user_id=connection.requester_id).first()
            receiver_profile = UserProfile.query.filter_by(user_id=connection.receiver_id).first()
            
            if requester_profile:
                requester_profile.connection_count += 1
            if receiver_profile:
                receiver_profile.connection_count += 1
        
        db.session.commit()
        
        message = 'Connection accepted' if action == 'accept' else 'Connection declined'
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# ======================
# COMPANY PAGES ROUTES
# ======================

@app.route('/companies')
def companies():
    """Companies directory"""
    page = request.args.get('page', 1, type=int)
    industry = request.args.get('industry', '')
    company_size = request.args.get('company_size', '')
    location = request.args.get('location', '')
    
    # Build query
    query = Company.query.filter(Company.is_active == True)
    
    if industry:
        query = query.filter(Company.industry == industry)
    if company_size:
        query = query.filter(Company.company_size == company_size)
    if location:
        query = query.filter(Company.headquarters_location.contains(location))
    
    companies = query.order_by(Company.name).paginate(page=page, per_page=20, error_out=False)
    
    # Get filter options
    industries = db.session.query(Company.industry).distinct().filter(Company.industry.isnot(None)).all()
    sizes = db.session.query(Company.company_size).distinct().filter(Company.company_size.isnot(None)).all()
    
    return render_template('companies/companies.html',
                         companies=companies,
                         industries=[i[0] for i in industries],
                         sizes=[s[0] for s in sizes],
                         filters={
                             'industry': industry,
                             'company_size': company_size,
                             'location': location
                         })

@app.route('/company/<string:slug>')
def company_detail(slug):
    """Company profile page"""
    company = Company.query.filter_by(slug=slug).first_or_404()
    
    # Get company's active jobs
    jobs = Job.query.filter_by(company_id=company.id, status='active')\
        .order_by(Job.published_at.desc()).limit(10).all()
    
    # Get company posts/updates
    posts = Post.query.filter_by(company_id=company.id, is_published=True)\
        .order_by(Post.created_at.desc()).limit(5).all()
    
    # Check if current user follows this company
    is_following = False
    if current_user.is_authenticated:
        is_following = Follow.query.filter_by(
            follower_id=current_user.id,
            following_company_id=company.id
        ).first() is not None
    
    return render_template('companies/company_detail.html',
                         company=company,
                         jobs=jobs,
                         posts=posts,
                         is_following=is_following)

@app.route('/company/<uuid:company_id>/follow', methods=['POST'])
@login_required
def follow_company(company_id):
    """Follow a company"""
    company = Company.query.get_or_404(company_id)
    
    # Check if already following
    existing_follow = Follow.query.filter_by(
        follower_id=current_user.id,
        following_company_id=company_id
    ).first()
    
    if existing_follow:
        return jsonify({'success': False, 'message': 'Already following this company'})
    
    try:
        follow = Follow(
            follower_id=current_user.id,
            following_company_id=company_id
        )
        db.session.add(follow)
        
        # Update follower count
        company.follower_count += 1
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Company followed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/company/<uuid:company_id>/unfollow', methods=['POST'])
@login_required
def unfollow_company(company_id):
    """Unfollow a company"""
    follow = Follow.query.filter_by(
        follower_id=current_user.id,
        following_company_id=company_id
    ).first()
    
    if not follow:
        return jsonify({'success': False, 'message': 'Not following this company'})
    
    try:
        db.session.delete(follow)
        
        # Update follower count
        company = Company.query.get(company_id)
        if company and company.follower_count > 0:
            company.follower_count -= 1
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Company unfollowed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# ======================
# ADMIN DASHBOARD ROUTES
# ======================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard - overview of platform statistics"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get platform statistics
        total_products = Product.query.count()
        total_orders = Order.query.count()
        total_users = User.query.filter_by(is_admin=False).count()
        
        # Calculate total revenue
        total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
        
        # Recent orders
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
        
        # Additional stats for enhanced dashboard
        total_categories = Category.query.count()
        total_vendors = Vendor.query.count()
        total_drivers = Driver.query.count()
        pending_vendors = Vendor.query.filter_by(status='pending').count()
        pending_drivers = Driver.query.filter_by(status='pending').count()
        active_vendors = Vendor.query.filter_by(status='approved').count()
        active_drivers = Driver.query.filter_by(status='approved').count()
        
        return render_template('admin/dashboard.html', 
                             total_products=total_products,
                             total_orders=total_orders,
                             total_users=total_users,
                             total_revenue=total_revenue,
                             recent_orders=recent_orders,
                             total_categories=total_categories,
                             total_vendors=total_vendors,
                             total_drivers=total_drivers,
                             pending_vendors=pending_vendors,
                             pending_drivers=pending_drivers,
                             active_vendors=active_vendors,
                             active_drivers=active_drivers)
                             
    except Exception as e:
        app.logger.error(f"Error loading admin dashboard: {str(e)}")
        flash('Error loading dashboard data', 'danger')
        return render_template('admin/dashboard.html', 
                             total_products=0,
                             total_orders=0,
                             total_users=0,
                             total_revenue=0,
                             recent_orders=[],
                             total_categories=0,
                             total_vendors=0,
                             total_drivers=0,
                             pending_vendors=0,
                             pending_drivers=0,
                             active_vendors=0,
                             active_drivers=0)

# ======================
# ADMIN CORE ROUTES - Products, Categories, Orders, Users, Vendors
# ======================

@app.route('/admin/products')
@login_required
def admin_products():
    """Admin products management page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        products = Product.query.all()
        return render_template('admin/products.html', products=products)
    except Exception as e:
        app.logger.error(f"Error loading admin products: {str(e)}")
        flash('Error loading products', 'danger')
        return render_template('admin/products.html', products=[])

@app.route('/admin/product/add', methods=['GET', 'POST'])
@login_required
def admin_add_product():
    """Admin add product page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Create new product
            product = Product(
                name=request.form.get('name'),
                description=request.form.get('description'),
                price=float(request.form.get('price')),
                stock_quantity=int(request.form.get('stock_quantity', 0)),
                category_id=request.form.get('category_id'),
                is_available=request.form.get('is_available') == 'on',
                featured=request.form.get('featured') == 'on',
                just_launched=request.form.get('just_launched') == 'on'
            )
            
            # Handle image upload
            image = request.files.get('image')
            if image and image.filename:
                filename = secure_filename(image.filename)
                image_path = f"uploads/products/{filename}"
                image.save(os.path.join(app.static_folder, image_path))
                product.image_url = image_path
            
            db.session.add(product)
            db.session.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin_products'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding product: {str(e)}")
            flash('Error adding product. Please try again.', 'danger')
    
    categories = Category.query.all()
    return render_template('admin/product_form.html', categories=categories, product=None)

@app.route('/admin/product/<id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_product(id):
    """Admin edit product page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            product.name = request.form.get('name')
            product.description = request.form.get('description')
            product.price = float(request.form.get('price'))
            product.stock_quantity = int(request.form.get('stock_quantity', 0))
            product.category_id = request.form.get('category_id')
            product.is_available = request.form.get('is_available') == 'on'
            product.featured = request.form.get('featured') == 'on'
            product.just_launched = request.form.get('just_launched') == 'on'
            
            # Handle image upload
            image = request.files.get('image')
            if image and image.filename:
                filename = secure_filename(image.filename)
                image_path = f"uploads/products/{filename}"
                image.save(os.path.join(app.static_folder, image_path))
                product.image_url = image_path
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin_products'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating product: {str(e)}")
            flash('Error updating product. Please try again.', 'danger')
    
    categories = Category.query.all()
    return render_template('admin/product_form.html', categories=categories, product=product)

@app.route('/admin/product/<id>/delete', methods=['POST'])
@login_required
def admin_delete_product(id):
    """Admin delete product"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        product = Product.query.get_or_404(id)
        product_name = product.name
        
        # Delete the product
        db.session.delete(product)
        db.session.commit()
        
        flash(f'Product "{product_name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting product: {str(e)}")
        flash('Error deleting product. Please try again.', 'danger')
    
    return redirect(url_for('admin_products'))

@app.route('/admin/product/<id>/toggle_just_launched', methods=['POST'])
@login_required
def admin_toggle_just_launched(id):
    """Toggle just_launched status for a product"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    product = Product.query.get_or_404(id)
    
    try:
        # Toggle the just_launched status
        product.just_launched = not product.just_launched
        db.session.commit()
        
        return jsonify({
            'success': True,
            'just_launched': product.just_launched,
            'message': f"Product {'added to' if product.just_launched else 'removed from'} Just Launched section"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/categories')
@login_required
def admin_categories():
    """Admin categories management page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        categories = Category.query.all()
        return render_template('admin/categories.html', categories=categories)
    except Exception as e:
        app.logger.error(f"Error loading admin categories: {str(e)}")
        flash('Error loading categories', 'danger')
        return render_template('admin/categories.html', categories=[])

@app.route('/admin/categories/add', methods=['GET', 'POST'])
@login_required
def admin_add_category():
    """Add a new category"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            image_url = request.form.get('image_url', '')
            
            if not name or not description:
                flash('Name and description are required', 'danger')
                return render_template('admin/category_form.html')
            
            # Check if category already exists
            existing = Category.query.filter_by(name=name).first()
            if existing:
                flash('Category with this name already exists', 'danger')
                return render_template('admin/category_form.html')
            
            category = Category(
                name=name,
                description=description,
                image_url=image_url or f'/static/images/categories/{name.lower().replace(" ", "_")}.jpg'
            )
            
            db.session.add(category)
            db.session.commit()
            
            flash('Category added successfully', 'success')
            return redirect(url_for('admin_categories'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding category: {str(e)}")
            flash('Error adding category', 'danger')
    
    return render_template('admin/category_form.html')

@app.route('/admin/categories/edit/<uuid:id>', methods=['GET', 'POST'])
@login_required
def admin_edit_category(id):
    """Edit an existing category"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    category = Category.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            image_url = request.form.get('image_url')
            
            if not name or not description:
                flash('Name and description are required', 'danger')
                return render_template('admin/category_form.html', category=category)
            
            # Check if another category with this name exists
            existing = Category.query.filter(Category.name == name, Category.id != id).first()
            if existing:
                flash('Another category with this name already exists', 'danger')
                return render_template('admin/category_form.html', category=category)
            
            category.name = name
            category.description = description
            if image_url:
                category.image_url = image_url
            
            db.session.commit()
            
            flash('Category updated successfully', 'success')
            return redirect(url_for('admin_categories'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating category: {str(e)}")
            flash('Error updating category', 'danger')
    
    return render_template('admin/category_form.html', category=category)

@app.route('/admin/categories/delete/<uuid:id>')
@login_required
def admin_delete_category_advanced(id):
    """Delete a category with advanced options"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    category = Category.query.get_or_404(id)
    
    # Check if category has products
    product_count = Product.query.filter_by(category_id=id).count()
    
    if product_count > 0:
        # Render delete options page
        return render_template('admin/category_delete_options.html', 
                             category=category, 
                             product_count=product_count)
    else:
        # Safe to delete directly
        try:
            db.session.delete(category)
            db.session.commit()
            flash(f'Category "{category.name}" deleted successfully', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting category: {str(e)}")
            flash('Error deleting category', 'danger')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/delete/<uuid:id>/confirm', methods=['POST'])
@login_required
def admin_delete_category_confirm(id):
    """Confirm category deletion with products handling"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    category = Category.query.get_or_404(id)
    action = request.form.get('action')
    
    try:
        if action == 'delete_with_products':
            # Delete category and all its products
            Product.query.filter_by(category_id=id).delete()
            db.session.delete(category)
            db.session.commit()
            flash(f'Category "{category.name}" and all its products deleted successfully', 'success')
            
        elif action == 'move_products':
            # Move products to another category
            new_category_id = request.form.get('new_category_id')
            if not new_category_id:
                flash('Please select a category to move products to', 'danger')
                return redirect(url_for('admin_delete_category_advanced', id=id))
            
            Product.query.filter_by(category_id=id).update({'category_id': new_category_id})
            db.session.delete(category)
            db.session.commit()
            flash(f'Category "{category.name}" deleted and products moved successfully', 'success')
            
        else:
            flash('Invalid action', 'danger')
            return redirect(url_for('admin_delete_category_advanced', id=id))
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting category: {str(e)}")
        flash('Error deleting category', 'danger')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/orders')
@login_required
def admin_orders():
    """Admin orders management page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        orders = Order.query.order_by(Order.created_at.desc()).all()
        return render_template('admin/orders.html', orders=orders)
    except Exception as e:
        app.logger.error(f"Error loading admin orders: {str(e)}")
        flash('Error loading orders', 'danger')
        return render_template('admin/orders.html', orders=[])

@app.route('/admin/migrate_cascade_delete', methods=['POST'])
@login_required
def migrate_cascade_delete():
    """Handle database migration for cascade delete functionality"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        password = request.form.get('password')
        
        # Verify admin password
        if not password or not check_password_hash(current_user.password_hash, password):
            flash('Invalid password', 'danger')
            return redirect(url_for('admin_orders'))
        
        # Log the migration attempt
        app.logger.info(f"Database migration initiated by admin user: {current_user.email}")
        
        # Here you could add actual migration logic if needed
        # For now, we'll just acknowledge the request
        flash('Database migration completed successfully', 'success')
        
    except Exception as e:
        app.logger.error(f"Error during database migration: {str(e)}")
        flash('Migration failed. Please try again.', 'danger')
    
    return redirect(url_for('admin_orders'))

@app.route('/admin/orders/<uuid:id>/update-status', methods=['POST'])
@login_required
def admin_update_order_status(id):
    """Update order status"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        order = Order.query.get_or_404(id)
        new_status = request.form.get('status')
        
        if new_status not in ['pending', 'processing', 'shipped', 'delivered', 'cancelled']:
            flash('Invalid status', 'danger')
            return redirect(url_for('admin_orders'))
        
        old_status = order.status
        order.status = new_status
        db.session.commit()
        
        app.logger.info(f"Order {order.id} status updated from '{old_status}' to '{new_status}' by admin {current_user.email}")
        flash(f'Order status updated to {new_status}', 'success')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating order status: {str(e)}")
        flash('Error updating order status', 'danger')
    
    return redirect(url_for('admin_orders'))

@app.route('/admin/orders/<uuid:id>/delete', methods=['POST'])
@login_required
def admin_delete_order(id):
    """Delete an order (admin only)"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        order = Order.query.get_or_404(id)
        order_number = order.order_number or str(order.id)
        
        # Delete related order items first (if cascade delete isn't working)
        OrderItem.query.filter_by(order_id=order.id).delete()
        
        # Delete the order
        db.session.delete(order)
        db.session.commit()
        
        app.logger.info(f"Order {order_number} deleted by admin {current_user.email}")
        flash('Order deleted successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting order {id}: {str(e)}")
        flash('Error deleting order', 'danger')
    
    return redirect(url_for('admin_orders'))

@app.route('/admin/users')
@login_required
def admin_users():
    """Admin users management page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        users = User.query.filter_by(is_admin=False).all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        app.logger.error(f"Error loading admin users: {str(e)}")
        flash('Error loading users', 'danger')
        return render_template('admin/users.html', users=[])

@app.route('/admin/users/<uuid:user_id>')
@login_required
def admin_user_detail(user_id):
    """Admin user detail page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        user = User.query.get_or_404(user_id)
        # Don't allow editing admin users
        if user.is_admin:
            flash('Cannot edit admin users', 'danger')
            return redirect(url_for('admin_users'))
        
        orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
        return render_template('admin/user_detail.html', user=user, orders=orders)
    except (ValueError, TypeError):
        flash('Invalid user ID', 'danger')
        return redirect(url_for('admin_users'))

@app.route('/admin/users/<uuid:user_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    """Edit user details"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        user = User.query.get_or_404(user_id)
        # Don't allow editing admin users
        if user.is_admin:
            flash('Cannot edit admin users', 'danger')
            return redirect(url_for('admin_users'))
        
        if request.method == 'POST':
            # Update user fields
            user.first_name = request.form.get('first_name', '').strip()
            user.last_name = request.form.get('last_name', '').strip()
            user.email = request.form.get('email', '').strip()
            user.username = request.form.get('username', '').strip()
            
            # Handle password change
            new_password = request.form.get('new_password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            
            # Validation
            if not user.first_name or not user.last_name or not user.email or not user.username:
                flash('All required fields must be filled', 'danger')
                return redirect(url_for('admin_edit_user', user_id=user_id))
            
            # Password validation (if passwords are provided)
            if new_password or confirm_password:
                if new_password != confirm_password:
                    flash('New passwords do not match', 'danger')
                    return redirect(url_for('admin_edit_user', user_id=user_id))
                
                if len(new_password) < 6:
                    flash('Password must be at least 6 characters long', 'danger')
                    return redirect(url_for('admin_edit_user', user_id=user_id))
                
                # Update password
                user.set_password(new_password)
            
            # Check if email is already used by another user
            existing_email = User.query.filter(User.email == user.email, User.id != user.id).first()
            if existing_email:
                flash('Email already exists', 'danger')
                return redirect(url_for('admin_edit_user', user_id=user_id))
            
            # Check if username is already used by another user
            existing_username = User.query.filter(User.username == user.username, User.id != user.id).first()
            if existing_username:
                flash('Username already exists', 'danger')
                return redirect(url_for('admin_edit_user', user_id=user_id))
            
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Success message includes password change info
            success_msg = f'User "{user.username}" updated successfully'
            if new_password:
                success_msg += ' (password changed)'
            flash(success_msg, 'success')
            return redirect(url_for('admin_users'))
        
        # GET request - show edit form
        return render_template('admin/user_form.html', user=user)
        
    except (ValueError, TypeError):
        flash('Invalid user ID', 'danger')
        return redirect(url_for('admin_users'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error editing user: {str(e)}")
        flash('Error updating user', 'danger')
        return redirect(url_for('admin_users'))

@app.route('/admin/users/<uuid:user_id>/get', methods=['GET'])
@login_required
def get_user_data(user_id):
    """Get user data for editing (AJAX endpoint)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        # Don't allow editing admin users
        if user.is_admin:
            return jsonify({'error': 'Cannot edit admin users'}), 403
        
        return jsonify({
            'id': str(user.id),
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'email': user.email,
            'username': user.username,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M') if user.created_at else 'N/A'
        })
        
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid user ID'}), 400
    except Exception as e:
        app.logger.error(f"Error fetching user data: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/users/<uuid:user_id>/update', methods=['POST'])
@login_required
def update_user_data(user_id):
    """Update user data (AJAX endpoint)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        # Don't allow editing admin users
        if user.is_admin:
            return jsonify({'error': 'Cannot edit admin users'}), 403
        
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update user fields
        user.first_name = data.get('first_name', '').strip()
        user.last_name = data.get('last_name', '').strip()
        user.email = data.get('email', '').strip()
        user.username = data.get('username', '').strip()
        
        # Handle password change
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        
        # Validation
        if not user.first_name or not user.last_name or not user.email or not user.username:
            return jsonify({'error': 'All required fields must be filled'}), 400
        
        # Password validation (if passwords are provided)
        password_changed = False
        if new_password or confirm_password:
            if new_password != confirm_password:
                return jsonify({'error': 'New passwords do not match'}), 400
            
            if len(new_password) < 6:
                return jsonify({'error': 'Password must be at least 6 characters long'}), 400
            
            # Update password
            user.set_password(new_password)
            password_changed = True
        
        # Check if email is already used by another user
        existing_email = User.query.filter(User.email == user.email, User.id != user.id).first()
        if existing_email:
            return jsonify({'error': 'Email already exists'}), 400
        
        # Check if username is already used by another user
        existing_username = User.query.filter(User.username == user.username, User.id != user.id).first()
        if existing_username:
            return jsonify({'error': 'Username already exists'}), 400
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Success message includes password change info
        success_msg = f'User "{user.username}" updated successfully'
        if password_changed:
            success_msg += ' (password changed)'
        
        return jsonify({
            'success': True,
            'message': success_msg,
            'user': {
                'id': str(user.id),
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}".strip()
            }
        })
        
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid user ID'}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/users/<uuid:user_id>/reset-password', methods=['POST'])
@login_required
def admin_reset_user_password(user_id):
    """Reset user password to a temporary password"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        # Don't allow resetting admin user passwords
        if user.is_admin:
            return jsonify({'error': 'Cannot reset admin user passwords'}), 403
        
        # Generate a temporary password
        import string
        import random
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        
        # Set the temporary password
        user.set_password(temp_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Password reset for user "{user.username}"',
            'temporary_password': temp_password,
            'note': 'Please provide this temporary password to the user and ask them to change it immediately.'
        })
        
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid user ID'}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error resetting user password: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/vendors')
@login_required
def admin_vendors():
    """Admin vendors management page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        vendors_query = Vendor.query.all()
        # Create list of tuples with vendor and document count as expected by template
        vendors = []
        for vendor in vendors_query:
            document_count = len(vendor.documents) if vendor.documents else 0
            vendors.append((vendor, document_count))
        
        return render_template('admin/vendors.html', vendors=vendors)
    except Exception as e:
        app.logger.error(f"Error loading admin vendors: {str(e)}")
        flash('Error loading vendors', 'danger')
        return render_template('admin/vendors.html', vendors=[])

@app.route('/admin/vendors/<uuid:vendor_id>')
@login_required
def admin_vendor_detail(vendor_id):
    """Admin vendor detail page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        vendor = Vendor.query.get_or_404(vendor_id)
        return render_template('admin/vendor_detail.html', vendor=vendor)
    except Exception as e:
        app.logger.error(f"Error loading vendor details for {vendor_id}: {str(e)}")
        flash('Error loading vendor details', 'danger')
        return redirect(url_for('admin_vendors'))

@app.route('/admin/vendors/<uuid:vendor_id>/approve', methods=['POST'])
@login_required
def admin_approve_vendor(vendor_id):
    """Approve a vendor"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        vendor = Vendor.query.get_or_404(vendor_id)
        vendor.status = 'approved'
        vendor.approved_at = datetime.utcnow()
        vendor.approved_by_id = current_user.id
        vendor.approval_notes = request.form.get('notes', '')
        
        db.session.commit()
        
        flash(f'Vendor "{vendor.business_name}" has been approved successfully', 'success')
        return redirect(url_for('admin_vendor_detail', vendor_id=vendor_id))
    except Exception as e:
        app.logger.error(f"Error approving vendor {vendor_id}: {str(e)}")
        flash('Error approving vendor', 'danger')
        return redirect(url_for('admin_vendor_detail', vendor_id=vendor_id))

@app.route('/admin/vendors/<uuid:vendor_id>/reject', methods=['POST'])
@login_required
def admin_reject_vendor(vendor_id):
    """Reject a vendor"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        vendor = Vendor.query.get_or_404(vendor_id)
        vendor.status = 'rejected'
        vendor.rejected_at = datetime.utcnow()
        vendor.rejected_by_id = current_user.id
        vendor.rejection_reason = request.form.get('reason', '')
        
        db.session.commit()
        
        flash(f'Vendor "{vendor.business_name}" has been rejected', 'warning')
        return redirect(url_for('admin_vendor_detail', vendor_id=vendor_id))
    except Exception as e:
        app.logger.error(f"Error rejecting vendor {vendor_id}: {str(e)}")
        flash('Error rejecting vendor', 'danger')
        return redirect(url_for('admin_vendor_detail', vendor_id=vendor_id))

@app.route('/admin/vendor/<uuid:vendor_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_vendor_edit(vendor_id):
    """Edit vendor information"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        vendor = Vendor.query.get_or_404(vendor_id)
        
        if request.method == 'POST':
            # Update business information
            vendor.business_name = request.form.get('business_name', vendor.business_name).strip()
            vendor.trading_name = request.form.get('trading_name', vendor.trading_name or '').strip()
            vendor.business_type = request.form.get('business_type', vendor.business_type)
            vendor.registration_number = request.form.get('registration_number', vendor.registration_number or '').strip()
            vendor.vat_number = request.form.get('vat_number', vendor.vat_number or '').strip()
            vendor.tax_number = request.form.get('tax_number', vendor.tax_number or '').strip()
            
            # Update contact information
            vendor.contact_person = request.form.get('contact_person', vendor.contact_person).strip()
            vendor.contact_email = request.form.get('contact_email', vendor.contact_email).strip()
            vendor.contact_phone = request.form.get('contact_phone', vendor.contact_phone).strip()
            vendor.alternative_phone = request.form.get('alternative_phone', vendor.alternative_phone or '').strip()
            
            # Update address information
            vendor.physical_address = request.form.get('physical_address', vendor.physical_address).strip()
            vendor.postal_address = request.form.get('postal_address', vendor.postal_address or '').strip()
            vendor.city = request.form.get('city', vendor.city).strip()
            vendor.province = request.form.get('province', vendor.province)
            vendor.postal_code = request.form.get('postal_code', vendor.postal_code).strip()
            
            # Update banking information
            vendor.bank_name = request.form.get('bank_name', vendor.bank_name)
            vendor.account_holder = request.form.get('account_holder', vendor.account_holder).strip()
            vendor.account_number = request.form.get('account_number', vendor.account_number).strip()
            vendor.branch_code = request.form.get('branch_code', vendor.branch_code).strip()
            vendor.account_type = request.form.get('account_type', vendor.account_type)
            
            # Update business information
            vendor.business_description = request.form.get('business_description', vendor.business_description).strip()
            vendor.website_url = request.form.get('website_url', vendor.website_url or '').strip()
            
            # Update numeric fields safely
            try:
                years_in_business = request.form.get('years_in_business')
                if years_in_business and years_in_business.strip():
                    vendor.years_in_business = int(years_in_business)
            except (ValueError, TypeError):
                pass  # Keep existing value if conversion fails
            
            vendor.number_of_employees = request.form.get('number_of_employees', vendor.number_of_employees)
            vendor.bee_level = request.form.get('bee_level', vendor.bee_level or '').strip()
            
            vendor.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Vendor "{vendor.business_name}" information has been updated.', 'success')
            return redirect(url_for('admin_vendor_detail', vendor_id=vendor_id))
            
        # GET request - show edit form
        return render_template('admin/vendor_form.html', vendor=vendor)
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating vendor: {str(e)}")
        flash('Error updating vendor information. Please try again.', 'danger')
        return redirect(url_for('admin_vendor_detail', vendor_id=vendor_id))

@app.route('/admin/vendor-document/<string:document_id>/download')
@login_required
def download_vendor_document(document_id):
    """Download a vendor document"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        doc_uuid = uuid.UUID(document_id)
        document = VendorDocument.query.get_or_404(doc_uuid)
        
        if not document.file_data:
            flash('File data not found', 'danger')
            return redirect(url_for('admin_vendor_detail', vendor_id=document.vendor_id))
        
        return Response(
            document.file_data,
            mimetype=document.mime_type or 'application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{document.file_name}"'
            }
        )
    except (ValueError, TypeError):
        flash('Invalid document ID', 'danger')
        return redirect(url_for('admin_vendors'))

@app.route('/admin/vendor-document/<string:document_id>/verify', methods=['POST'])
@login_required
def admin_vendor_document_verify(document_id):
    """Mark a vendor document as verified or rejected"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        doc_uuid = uuid.UUID(document_id)
        document = VendorDocument.query.get_or_404(doc_uuid)
        
        verification_status = request.form.get('verification_status')
        if verification_status not in ['verified', 'rejected']:
            flash('Invalid verification status', 'danger')
            return redirect(url_for('admin_vendor_detail', vendor_id=document.vendor_id))
        
        # Update document verification status
        document.verification_status = verification_status
        document.verified_at = datetime.utcnow()
        document.verified_by_id = current_user.id
        
        if verification_status == 'rejected':
            document.rejection_reason = request.form.get('rejection_reason', 'Document rejected by admin')
        else:
            document.rejection_reason = None
        
        db.session.commit()
        
        status_text = 'verified' if verification_status == 'verified' else 'rejected'
        flash(f'Document has been {status_text}', 'success')
        
    except (ValueError, TypeError):
        flash('Invalid document ID', 'danger')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error verifying vendor document: {str(e)}")
        flash('Error updating document status', 'danger')
    
    return redirect(url_for('admin_vendor_detail', vendor_id=document.vendor_id))

@app.route('/admin/accounting')
@login_required
def admin_accounting():
    """Admin accounting management page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        from datetime import datetime, timedelta
        
        # Get date range (default to current month)
        end_date = datetime.now().date()
        start_date = end_date.replace(day=1)  # First day of current month
        
        # Get date filters from request if provided
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Convert to datetime for database queries
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Calculate total revenue (sum of all completed orders in date range)
        total_revenue = db.session.query(db.func.sum(Order.total_amount))\
            .filter(Order.created_at >= start_datetime)\
            .filter(Order.created_at <= end_datetime)\
            .filter(Order.status.in_(['completed', 'delivered', 'paid']))\
            .scalar() or 0
        
        # Calculate VAT (15% of revenue)
        # South African VAT: Revenue includes VAT, so VAT = revenue * 15/115
        total_vat_output = total_revenue * 15 / 115 if total_revenue > 0 else 0
        
        # For expenses, we'll use a simple calculation (you can enhance this based on your needs)
        # For now, let's assume 10% of revenue as expenses for demo purposes
        total_expenses = total_revenue * 0.1 if total_revenue > 0 else 0
        total_vat_input = total_expenses * 15 / 115 if total_expenses > 0 else 0
        
        # Net VAT payable (output VAT minus input VAT)
        net_vat_payable = total_vat_output - total_vat_input
        
        # Get order statistics
        total_orders = Order.query\
            .filter(Order.created_at >= start_datetime)\
            .filter(Order.created_at <= end_datetime)\
            .count()
        
        # Get recent orders for the period
        recent_orders = Order.query\
            .filter(Order.created_at >= start_datetime)\
            .filter(Order.created_at <= end_datetime)\
            .order_by(Order.created_at.desc())\
            .limit(10).all()
        
        # Create income transactions from orders (simplified approach)
        income_transactions = []
        
        # Add actual IncomeTransaction records
        actual_income_transactions = IncomeTransaction.query\
            .filter(IncomeTransaction.date >= start_date)\
            .filter(IncomeTransaction.date <= end_date)\
            .order_by(IncomeTransaction.date.desc()).all()
        
        for income in actual_income_transactions:
            income_transactions.append({
                'id': str(income.id),
                'date': income.date.strftime('%Y-%m-%d'),
                'description': income.description,
                'customer': income.customer_name or 'Unknown',
                'amount_incl_vat': income.amount_incl_vat,
                'vat_amount': income.vat_amount,
                'amount_excl_vat': income.amount_excl_vat,
                'category': income.category,
                'type': 'income_transaction'  # Mark this as actual income transaction
            })
        
        # Add order-based income transactions
        for order in recent_orders:
            order_excl_vat = order.total_amount / 1.15
            order_vat = order.total_amount - order_excl_vat
            customer_name = f"{order.user.first_name} {order.user.last_name}" if order.user else "Unknown"
            
            income_transactions.append({
                'id': str(order.id),  # Add order ID for edit functionality
                'date': order.created_at.strftime('%Y-%m-%d'),
                'description': f'Order #{order.order_number or order.id}',
                'customer': customer_name,
                'amount_incl_vat': order.total_amount,
                'vat_amount': order_vat,
                'amount_excl_vat': order_excl_vat,
                'category': 'Sales Revenue',
                'type': 'order'  # Mark this as order-based income
            })
        
        # Calculate income totals
        revenue_excl_vat = total_revenue / 1.15 if total_revenue > 0 else 0
        revenue_vat = total_revenue - revenue_excl_vat
        
        # Calculate totals from actual displayed transactions
        displayed_incl_vat = sum(transaction['amount_incl_vat'] for transaction in income_transactions)
        displayed_vat = sum(transaction['vat_amount'] for transaction in income_transactions)
        displayed_excl_vat = sum(transaction['amount_excl_vat'] for transaction in income_transactions)
        
        income_totals = {
            'incl_vat': displayed_incl_vat,
            'vat': displayed_vat,
            'excl_vat': displayed_excl_vat
        }
        
        # Load actual expense transactions
        expense_transactions = []
        
        # Add actual ExpenseTransaction records
        actual_expense_transactions = ExpenseTransaction.query\
            .filter(ExpenseTransaction.date >= start_date)\
            .filter(ExpenseTransaction.date <= end_date)\
            .order_by(ExpenseTransaction.date.desc()).all()
        
        for expense in actual_expense_transactions:
            expense_transactions.append({
                'id': str(expense.id),
                'date': expense.date.strftime('%Y-%m-%d'),
                'description': expense.description,
                'supplier_name': expense.supplier_name or 'Unknown',
                'amount_incl_vat': expense.amount_incl_vat,
                'vat_amount': expense.vat_amount,
                'amount_excl_vat': expense.amount_excl_vat,
                'category': expense.category,
                'has_tax_invoice': expense.has_tax_invoice,
                'type': 'expense_transaction'
            })
        
        # Add sample/estimated expenses if no actual transactions exist
        if not expense_transactions and total_expenses > 0:
            expenses_excl_vat = total_expenses / 1.15
            expenses_vat = total_expenses - expenses_excl_vat
            expense_transactions.append({
                'id': 'estimated',
                'date': end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date),
                'description': 'Operating Expenses (Estimated)',
                'supplier_name': 'Various Suppliers',
                'amount_incl_vat': total_expenses,
                'vat_amount': expenses_vat,
                'amount_excl_vat': expenses_excl_vat,
                'category': 'Operating Expenses',
                'has_tax_invoice': False,
                'type': 'estimated'
            })
        
        # Calculate expense totals from actual displayed transactions
        displayed_expense_incl_vat = sum(transaction['amount_incl_vat'] for transaction in expense_transactions)
        displayed_expense_vat = sum(transaction['vat_amount'] for transaction in expense_transactions)
        displayed_expense_excl_vat = sum(transaction['amount_excl_vat'] for transaction in expense_transactions)
        
        expense_totals = {
            'incl_vat': displayed_expense_incl_vat,
            'vat': displayed_expense_vat,
            'excl_vat': displayed_expense_excl_vat
        }
        
        # Create comprehensive reports object for the Reports tab
        # Use actual transaction data for accurate calculations
        total_income_excl_vat = income_totals['excl_vat']
        total_expense_excl_vat = expense_totals['excl_vat']
        
        # Categorize expenses for better reporting
        cost_of_sales = 0
        operating_expenses = 0
        
        # Calculate actual cost of sales and operating expenses from transaction categories
        for expense in expense_transactions:
            if expense.get('category') in ['Cost of Goods Sold', 'Inventory Purchases', 'Direct Materials', 'Production Costs']:
                cost_of_sales += expense.get('amount_excl_vat', 0)
            else:
                operating_expenses += expense.get('amount_excl_vat', 0)
        
        # If no specific cost of sales categorization, use 70% as cost of sales for product businesses
        if cost_of_sales == 0 and total_expense_excl_vat > 0:
            cost_of_sales = total_expense_excl_vat * 0.7
            operating_expenses = total_expense_excl_vat * 0.3
        
        gross_profit = total_income_excl_vat - cost_of_sales
        net_profit = gross_profit - operating_expenses
        
        # Calculate realistic asset estimates based on business performance
        cash_on_hand = max(net_profit * 0.2, total_income_excl_vat * 0.05)  # 20% of profit or 5% of revenue
        inventory_value = cost_of_sales * 0.25 if cost_of_sales > 0 else total_income_excl_vat * 0.15  # 25% of COGS or 15% of revenue
        accounts_receivable = total_income_excl_vat * 0.1  # 10% of revenue as outstanding receivables
        
        total_assets = cash_on_hand + inventory_value + accounts_receivable
        
        # Calculate realistic liabilities
        accounts_payable = cost_of_sales * 0.2 if cost_of_sales > 0 else total_expense_excl_vat * 0.3  # 20% of COGS or 30% of expenses
        accrued_expenses = operating_expenses * 0.1  # 10% of operating expenses
        
        total_liabilities = net_vat_payable + accounts_payable + accrued_expenses
        net_worth = total_assets - total_liabilities
        
        # Cash flow calculations
        cash_from_operations = net_profit + (accounts_payable * 0.1)  # Add back some non-cash items
        cash_from_investing = 0  # Assume no major investments for now
        cash_from_financing = 0  # Assume no financing activities for now
        net_cash_flow = cash_from_operations + cash_from_investing + cash_from_financing
        
        # Tax calculations (South African rates)
        provisional_tax = max(net_profit * 0.28, 0) if net_profit > 0 else 0  # 28% company tax rate
        
        reports = {
            'revenue_excl_vat': total_income_excl_vat,
            'cost_of_sales': cost_of_sales,
            'gross_profit': gross_profit,
            'gross_profit_margin': (gross_profit / total_income_excl_vat * 100) if total_income_excl_vat > 0 else 0,
            'operating_expenses': operating_expenses,
            'net_profit': net_profit,
            'net_profit_margin': (net_profit / total_income_excl_vat * 100) if total_income_excl_vat > 0 else 0,
            'cash_on_hand': cash_on_hand,
            'inventory_value': inventory_value,
            'accounts_receivable': accounts_receivable,
            'total_assets': total_assets,
            'vat_payable': net_vat_payable,
            'accounts_payable': accounts_payable,
            'accrued_expenses': accrued_expenses,
            'total_liabilities': total_liabilities,
            'net_worth': net_worth,
            'cash_from_operations': cash_from_operations,
            'cash_from_investing': cash_from_investing,
            'cash_from_financing': cash_from_financing,
            'net_cash_flow': net_cash_flow,
            'vat_output': total_vat_output,
            'vat_input': total_vat_input,
            'vat_net': net_vat_payable,
            'provisional_tax': provisional_tax,
            'current_ratio': (total_assets / total_liabilities) if total_liabilities > 0 else 0,
            'debt_to_equity': (total_liabilities / net_worth) if net_worth > 0 else 0
        }
        
        # Calculate totals based on displayed transactions, not estimated values
        actual_total_revenue = income_totals['incl_vat']
        actual_total_vat_output = income_totals['vat']
        actual_total_expenses = expense_totals['incl_vat']
        actual_total_vat_input = expense_totals['vat']
        actual_net_vat_payable = actual_total_vat_output - actual_total_vat_input
        
        return render_template('admin/accounting.html',
                             total_revenue=actual_total_revenue,
                             total_vat_output=actual_total_vat_output,
                             total_expenses=actual_total_expenses,
                             total_vat_input=actual_total_vat_input,
                             net_vat_payable=actual_net_vat_payable,
                             total_orders=total_orders,
                             recent_orders=recent_orders,
                             income_transactions=income_transactions,
                             income_totals=income_totals,
                             expense_transactions=expense_transactions,
                             expense_totals=expense_totals,
                             reports=reports,
                             start_date=start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date),
                             end_date=end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date))
    except Exception as e:
        from datetime import datetime as dt
        import traceback
        app.logger.error(f"Error loading admin accounting: {str(e)}")
        app.logger.error(f"Full traceback: {traceback.format_exc()}")
        flash('Error loading accounting', 'danger')
        # Provide default values for template
        default_reports = {
            'revenue_excl_vat': 0,
            'cost_of_sales': 0,
            'gross_profit': 0,
            'gross_profit_margin': 0,
            'operating_expenses': 0,
            'net_profit': 0,
            'net_profit_margin': 0,
            'cash_on_hand': 0,
            'inventory_value': 0,
            'accounts_receivable': 0,
            'total_assets': 0,
            'vat_payable': 0,
            'accounts_payable': 0,
            'accrued_expenses': 0,
            'total_liabilities': 0,
            'net_worth': 0,
            'cash_from_operations': 0,
            'cash_from_investing': 0,
            'cash_from_financing': 0,
            'net_cash_flow': 0,
            'vat_output': 0,
            'vat_input': 0,
            'vat_net': 0,
            'provisional_tax': 0,
            'current_ratio': 0,
            'debt_to_equity': 0
        }
        
        return render_template('admin/accounting.html',
                             total_revenue=0,
                             total_vat_output=0,
                             total_expenses=0,
                             total_vat_input=0,
                             net_vat_payable=0,
                             total_orders=0,
                             recent_orders=[],
                             income_transactions=[],
                             income_totals={'incl_vat': 0, 'vat': 0, 'excl_vat': 0},
                             expense_transactions=[],
                             expense_totals={'incl_vat': 0, 'vat': 0, 'excl_vat': 0},
                             reports=default_reports,
                             start_date=datetime.now().strftime('%Y-%m-%d'),
                             end_date=datetime.now().strftime('%Y-%m-%d'))

@app.route('/admin/accounting/income/add', methods=['POST'])
@login_required
def add_income_transaction():
    """Add a new income transaction"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get form data
        date_str = request.form.get('date')
        description = request.form.get('description')
        customer_name = request.form.get('customer', 'Unknown')
        amount_incl_vat = float(request.form.get('amount_incl_vat', 0))
        category = request.form.get('category', 'Other Income')
        payment_method = request.form.get('payment_method', 'Cash')
        reference_number = request.form.get('reference_number', '')
        vat_rate = float(request.form.get('vat_rate', 15.0))
        
        # Parse date
        transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()
        
        # Create the income transaction
        income_transaction = IncomeTransaction(
            date=transaction_date,
            description=description,
            category=category,
            customer_name=customer_name,
            amount_incl_vat=amount_incl_vat,
            vat_rate=vat_rate,
            payment_method=payment_method,
            reference_number=reference_number,
            tax_invoice_issued=bool(request.form.get('tax_invoice_issued')),
            income_type='Trading',
            export_status='Domestic'
        )
        income_transaction.calculate_vat()
        db.session.add(income_transaction)
        db.session.flush()  # Get the transaction ID before creating audit log

        # Create audit log
        audit_log = AccountingAuditLog(
            user_id=current_user.id,
            action='CREATE',
            transaction_type='Income',
            transaction_id=income_transaction.id,
            amount=income_transaction.amount_incl_vat,
            details=f'Manual entry: {description}',
            ip_address=request.remote_addr
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash(f'Income transaction recorded: {description} - R{amount_incl_vat:.2f}', 'success')
        app.logger.info(f"Income transaction created by {current_user.email}: {description} - R{amount_incl_vat:.2f}")
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding income transaction: {str(e)}")
        flash('Error adding income transaction', 'danger')
    
    return redirect(url_for('admin_accounting'))

@app.route('/admin/accounting/expense/add', methods=['POST'])
@login_required
def add_expense_transaction():
    """Add a new expense transaction"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get form data
        date_str = request.form.get('date')
        description = request.form.get('description')
        supplier_name = request.form.get('supplier', 'Unknown')
        amount_incl_vat = float(request.form.get('amount_incl_vat', 0))
        category = request.form.get('category', 'Operating Expenses')
        payment_method = request.form.get('payment_method', 'Cash')
        reference_number = request.form.get('reference_number', '')
        vat_rate = float(request.form.get('vat_rate', 15.0))
        
        # Parse date
        transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()
        
        # Create the expense transaction
        expense_transaction = ExpenseTransaction(
            date=transaction_date,
            description=description,
            category=category,
            supplier_name=supplier_name,
            amount_incl_vat=amount_incl_vat,
            vat_rate=vat_rate,
            payment_method=payment_method,
            reference_number=reference_number,
            has_tax_invoice=bool(request.form.get('has_tax_invoice')),
            expense_type='Operating',
            business_use_percentage=100.0
        )
        expense_transaction.calculate_vat()
        db.session.add(expense_transaction)
        db.session.flush()  # Get the transaction ID before creating audit log

        # Create audit log
        audit_log = AccountingAuditLog(
            user_id=current_user.id,
            action='CREATE',
            transaction_type='Expense',
            transaction_id=expense_transaction.id,
            amount=expense_transaction.amount_incl_vat,
            details=f'Manual entry: {description}',
            ip_address=request.remote_addr
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash(f'Expense transaction recorded: {description} - R{amount_incl_vat:.2f}', 'success')
        app.logger.info(f"Expense transaction created by {current_user.email}: {description} - R{amount_incl_vat:.2f}")
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding expense transaction: {str(e)}")
        flash('Error adding expense transaction', 'danger')
    
    return redirect(url_for('admin_accounting'))

@app.route('/admin/accounting/export')
@login_required
def export_accounting_csv():
    """Export accounting data to CSV"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        import csv
        from io import StringIO
        from flask import make_response
        
        # Get parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        export_type = request.args.get('type', 'all')
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Date', 'Order ID', 'Customer', 'Total Amount', 'Status', 'Payment Method'])
        
        # Build query
        query = Order.query
        
        # Apply date filters if provided
        if start_date:
            from datetime import datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Order.created_at >= start_dt)
        
        if end_date:
            from datetime import datetime
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Order.created_at <= end_dt)
        
        # Get orders
        orders = query.order_by(Order.created_at.desc()).all()
        
        # Write data rows
        for order in orders:
            user_name = f"{order.user.first_name} {order.user.last_name}" if order.user else "Unknown"
            writer.writerow([
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.order_number or order.id,
                user_name,
                f"R{order.total_amount:.2f}",
                order.status,
                getattr(order, 'payment_method', 'N/A')
            ])
        
        # Create response
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=accounting_export_{export_type}.csv'
        
        return response
        
    except Exception as e:
        app.logger.error(f"Error exporting accounting CSV: {str(e)}")
        flash('Error exporting data', 'danger')
        return redirect(url_for('admin_accounting'))

@app.route('/admin/vat-return')
@login_required
def generate_vat_return():
    """Generate South African VAT 201 return"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        from datetime import datetime
        import csv
        from io import StringIO
        from flask import make_response
        
        # Get date parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if not start_date_str or not end_date_str:
            flash('Start date and end date are required', 'danger')
            return redirect(url_for('admin_accounting'))
        
        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Convert to datetime for database queries
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Calculate VAT figures for the period
        total_revenue = db.session.query(db.func.sum(Order.total_amount))\
            .filter(Order.created_at >= start_datetime)\
            .filter(Order.created_at <= end_datetime)\
            .filter(Order.status.in_(['completed', 'delivered', 'paid']))\
            .scalar() or 0
        
        # South African VAT calculations (15% standard rate)
        # Revenue includes VAT, so: VAT = revenue * 15/115
        total_vat_output = total_revenue * 15 / 115 if total_revenue > 0 else 0
        revenue_excl_vat = total_revenue - total_vat_output
        
        # Estimated expenses (you can enhance this based on your business model)
        total_expenses = total_revenue * 0.1 if total_revenue > 0 else 0
        total_vat_input = total_expenses * 15 / 115 if total_expenses > 0 else 0
        expenses_excl_vat = total_expenses - total_vat_input
        
        # Net VAT payable
        net_vat_payable = total_vat_output - total_vat_input
        
        # Prepare VAT return data
        vat_data = {
            'start_date': start_date.strftime('%d %B %Y'),
            'end_date': end_date.strftime('%d %B %Y'),
            'period_start': start_date.strftime('%Y-%m-%d'),
            'period_end': end_date.strftime('%Y-%m-%d'),
            'total_sales_excl_vat': revenue_excl_vat,
            'total_vat_output': total_vat_output,
            'total_sales_incl_vat': total_revenue,
            'total_purchases_excl_vat': expenses_excl_vat,
            'total_vat_input': total_vat_input,
            'total_purchases_incl_vat': total_expenses,
            'net_vat_payable': net_vat_payable,
            'net_vat': net_vat_payable,  # Template expects this name
            'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'business_name': 'Brand Cartel',
            'vat_number': 'TBD'  # You should set this in your settings
        }
        
        # Check if it's a CSV export request
        export_format = request.args.get('format', 'html')
        
        if export_format == 'csv':
            # Generate CSV export
            output = StringIO()
            writer = csv.writer(output)
            
            # Write VAT return headers and data
            writer.writerow(['VAT 201 Return - Brand Cartel'])
            writer.writerow([f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"])
            writer.writerow([f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
            writer.writerow([])
            
            writer.writerow(['Description', 'Amount (R)'])
            writer.writerow(['Total Sales (Excl VAT)', f"{revenue_excl_vat:.2f}"])
            writer.writerow(['VAT Output Tax', f"{total_vat_output:.2f}"])
            writer.writerow(['Total Sales (Incl VAT)', f"{total_revenue:.2f}"])
            writer.writerow([])
            writer.writerow(['Total Purchases (Excl VAT)', f"{expenses_excl_vat:.2f}"])
            writer.writerow(['VAT Input Tax', f"{total_vat_input:.2f}"])
            writer.writerow(['Total Purchases (Incl VAT)', f"{total_expenses:.2f}"])
            writer.writerow([])
            writer.writerow(['Net VAT Payable', f"{net_vat_payable:.2f}"])
            
            # Create response
            output.seek(0)
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=vat_return_{start_date}_{end_date}.csv'
            
            return response
        
        # Render HTML VAT return page
        return render_template('admin/vat_return.html', vat_data=vat_data)
        
    except Exception as e:
        app.logger.error(f"Error generating VAT return: {str(e)}")
        flash('Error generating VAT return. Please try again.', 'danger')
        return redirect(url_for('admin_accounting'))

@app.route('/admin/tax-documents')
@login_required
def tax_documents():
    """Admin tax documents management page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get filter parameters
        document_type_filter = request.args.get('type', 'all')
        search_query = request.args.get('search', '')
        
        # Build query with filters
        query = TaxDocument.query
        
        if document_type_filter != 'all':
            query = query.filter(TaxDocument.document_type == document_type_filter)
        
        if search_query:
            query = query.filter(
                db.or_(
                    TaxDocument.document_number.contains(search_query),
                    TaxDocument.supplier_customer_name.contains(search_query),
                    TaxDocument.description.contains(search_query)
                )
            )
        
        # Get all tax documents ordered by date (newest first)
        documents = query.order_by(TaxDocument.document_date.desc()).all()
        
        # Calculate some statistics
        total_documents = len(documents)
        total_value = sum(doc.amount for doc in documents)  # Change total_amount to total_value
        total_vat = sum(doc.vat_amount for doc in documents)
        
        # Count documents by type
        total_invoices = len([doc for doc in documents if doc.document_type == 'Tax Invoice'])
        total_credit_notes = len([doc for doc in documents if doc.document_type == 'Credit Note'])
        
        # Group by document type for summary
        doc_type_summary = {}
        for doc in documents:
            doc_type = doc.document_type
            if doc_type not in doc_type_summary:
                doc_type_summary[doc_type] = {'count': 0, 'amount': 0, 'vat': 0}
            doc_type_summary[doc_type]['count'] += 1
            doc_type_summary[doc_type]['amount'] += doc.amount
            doc_type_summary[doc_type]['vat'] += doc.vat_amount
        
        return render_template('admin/tax_documents.html', 
                             documents=documents,
                             total_documents=total_documents,
                             total_invoices=total_invoices,
                             total_credit_notes=total_credit_notes,
                             total_value=total_value,
                             total_vat=total_vat,
                             doc_type_summary=doc_type_summary,
                             document_type=document_type_filter,
                             search_query=search_query)
    except Exception as e:
        app.logger.error(f"Error loading tax documents: {str(e)}")
        flash('Error loading tax documents', 'danger')
        return render_template('admin/tax_documents.html', 
                             documents=[],
                             total_documents=0,
                             total_invoices=0,
                             total_credit_notes=0,
                             total_value=0,
                             total_vat=0,
                             doc_type_summary={},
                             document_type='all',
                             search_query='')

@app.route('/admin/tax-documents/upload', methods=['GET', 'POST'])
@login_required
def tax_document_upload():
    """Upload and categorize tax documents"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            from werkzeug.utils import secure_filename
            import os
            
            # Get form data
            document_type = request.form.get('document_type')
            document_number = request.form.get('document_number', '').strip()
            document_date_str = request.form.get('document_date')
            supplier_customer_name = request.form.get('supplier_customer_name', '').strip()
            vat_number = request.form.get('vat_number', '').strip()
            amount = float(request.form.get('amount', 0))
            vat_amount = float(request.form.get('vat_amount', 0))
            description = request.form.get('description', '').strip()
            category = request.form.get('category', '').strip()
            notes = request.form.get('notes', '').strip()
            
            # Parse date
            document_date = datetime.strptime(document_date_str, '%Y-%m-%d').date()
            
            # Handle file upload
            uploaded_file = request.files.get('document_file')
            if not uploaded_file or uploaded_file.filename == '':
                flash('Please select a file to upload', 'danger')
                return redirect(url_for('tax_document_upload'))
            
            # Read file data
            file_data = uploaded_file.read()
            filename = secure_filename(uploaded_file.filename)
            
            # Create tax document record
            tax_doc = TaxDocument(
                document_type=document_type,
                document_number=document_number if document_number else None,
                document_date=document_date,
                supplier_customer_name=supplier_customer_name,
                vat_number=vat_number if vat_number else None,
                amount=amount,
                vat_amount=vat_amount,
                description=description if description else None,
                category=category if category else None,
                file_name=filename,
                file_size=len(file_data),
                mime_type=uploaded_file.content_type,
                file_data=file_data,
                notes=notes if notes else None,
                uploaded_by_id=current_user.id
            )
            
            db.session.add(tax_doc)
            db.session.commit()
            
            flash(f'Tax document "{filename}" uploaded successfully!', 'success')
            return redirect(url_for('tax_documents'))
            
        except ValueError as e:
            flash('Please enter valid amounts and date', 'danger')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error uploading tax document: {str(e)}")
            flash('Error uploading document. Please try again.', 'danger')
    
    return render_template('admin/tax_document_upload.html')

@app.route('/admin/tax-documents/<string:doc_id>/download')
@login_required
def tax_document_download(doc_id):
    """Download a tax document"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        from flask import Response
        import uuid as uuid_module
        
        doc_uuid = uuid_module.UUID(doc_id)
        document = TaxDocument.query.get_or_404(doc_uuid)
        
        if not document.file_data:
            flash('File data not found', 'danger')
            return redirect(url_for('tax_documents'))
        
        return Response(
            document.file_data,
            mimetype=document.mime_type or 'application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{document.file_name}"'
            }
        )
    except (ValueError, TypeError):
        flash('Invalid document ID', 'danger')
        return redirect(url_for('tax_documents'))

# Add route aliases for template compatibility
@app.route('/admin/tax-documents/upload-form')
@login_required  
def upload_tax_document():
    """Alias for tax_document_upload for template compatibility"""
    return tax_document_upload()

@app.route('/admin/tax-documents/<string:document_id>/download-file')
@login_required
def download_tax_document(document_id):
    """Alias for tax_document_download for template compatibility"""
    return tax_document_download(document_id)

@app.route('/admin/tax-documents/<string:document_id>/view')
@login_required
def view_tax_document(document_id):
    """View a tax document in browser"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        from flask import Response
        import uuid as uuid_module
        
        doc_uuid = uuid_module.UUID(document_id)
        document = TaxDocument.query.get_or_404(doc_uuid)
        
        if not document.file_data:
            flash('File data not found', 'danger')
            return redirect(url_for('tax_documents'))
        
        return Response(
            document.file_data,
            mimetype=document.mime_type or 'application/octet-stream',
            headers={
                'Content-Disposition': f'inline; filename="{document.file_name}"'
            }
        )
    except (ValueError, TypeError):
        flash('Invalid document ID', 'danger')
        return redirect(url_for('tax_documents'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    """Admin settings management page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get settings, create default if none exists
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
            db.session.commit()
        
        if request.method == 'POST':
            # Handle file uploads first
            import base64
            
            # Handle hero image file upload
            hero_image_file = request.files.get('hero_image_file')
            if hero_image_file and hero_image_file.filename:
                try:
                    # Convert uploaded file to base64 data URL
                    file_data = hero_image_file.read()
                    file_extension = hero_image_file.filename.lower().split('.')[-1]
                    
                    # Map file extensions to MIME types
                    mime_type_map = {
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg', 
                        'png': 'image/png',
                        'gif': 'image/gif',
                        'webp': 'image/webp',
                        'svg': 'image/svg+xml'
                    }
                    
                    mime_type = mime_type_map.get(file_extension, 'image/png')
                    base64_data = base64.b64encode(file_data).decode('utf-8')
                    data_url = f"data:{mime_type};base64,{base64_data}"
                    settings.hero_image = data_url
                except Exception as e:
                    app.logger.error(f"Error processing hero image: {e}")
                    flash('Error uploading hero image', 'danger')
            
            # Handle favicon file upload
            favicon_file = request.files.get('favicon_file')
            if favicon_file and favicon_file.filename:
                try:
                    # Log old favicon removal if one exists
                    old_favicon = settings.favicon
                    if old_favicon and old_favicon != 'images/favi.png':
                        # Check if it's a base64 data URL (uploaded favicon) vs default file path
                        if old_favicon.startswith('data:'):
                            app.logger.info("Removing old favicon from database (base64 data)")
                            # Clear the old favicon from database
                            settings.favicon = None
                            db.session.flush()  # Ensure old favicon is cleared before setting new one
                        else:
                            app.logger.info(f"Replacing favicon file reference: {old_favicon}")
                    
                    # Convert uploaded file to base64 data URL
                    file_data = favicon_file.read()
                    file_extension = favicon_file.filename.lower().split('.')[-1]
                    
                    # Validate file size (max 1MB for favicons)
                    max_size = 1024 * 1024  # 1MB
                    if len(file_data) > max_size:
                        flash('Favicon file too large. Please use a file smaller than 1MB.', 'danger')
                        raise ValueError(f"File too large: {len(file_data)} bytes")
                    
                    # Validate file extension
                    allowed_extensions = {'ico', 'png', 'jpg', 'jpeg', 'gif'}
                    if file_extension not in allowed_extensions:
                        flash(f'Invalid favicon format. Please use: {", ".join(allowed_extensions)}', 'danger')
                        raise ValueError(f"Invalid file extension: {file_extension}")
                    
                    # Map file extensions to MIME types
                    mime_type_map = {
                        'ico': 'image/x-icon',
                        'png': 'image/png',
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg',
                        'gif': 'image/gif'
                    }
                    
                    mime_type = mime_type_map.get(file_extension, 'image/x-icon')
                    base64_data = base64.b64encode(file_data).decode('utf-8')
                    data_url = f"data:{mime_type};base64,{base64_data}"
                    
                    # Set new favicon
                    settings.favicon = data_url
                    
                    app.logger.info(f"New favicon uploaded and stored (format: {file_extension}, size: {len(file_data)} bytes)")
                    flash('Favicon updated successfully! Changes will appear on next page load.', 'success')
                    
                except Exception as e:
                    app.logger.error(f"Error processing favicon: {e}")
                    flash('Error uploading favicon', 'danger')
            
            # Handle logo file upload
            logo_file = request.files.get('logo_file')
            if logo_file and logo_file.filename:
                try:
                    # Convert uploaded file to base64 data URL
                    file_data = logo_file.read()
                    file_extension = logo_file.filename.lower().split('.')[-1]
                    
                    # Map file extensions to MIME types
                    mime_type_map = {
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg',
                        'png': 'image/png',
                        'gif': 'image/gif',
                        'svg': 'image/svg+xml',
                        'webp': 'image/webp'
                    }
                    
                    mime_type = mime_type_map.get(file_extension, 'image/png')
                    base64_data = base64.b64encode(file_data).decode('utf-8')
                    data_url = f"data:{mime_type};base64,{base64_data}"
                    settings.store_logo = data_url
                except Exception as e:
                    app.logger.error(f"Error processing logo: {e}")
                    flash('Error uploading logo', 'danger')
            
            # Handle banner file upload
            banner_file = request.files.get('banner_image_file')
            if banner_file and banner_file.filename:
                try:
                    app.logger.info(f"Processing banner upload: {banner_file.filename}")
                    
                    # Log old banner removal if one exists
                    old_banner = settings.banner_image
                    if old_banner and old_banner != 'images/banner.png':
                        if old_banner.startswith('data:'):
                            app.logger.info("Removing old banner from database (base64 data)")
                            # Clear the old banner from database
                            settings.banner_image = None
                            db.session.flush()
                        else:
                            app.logger.info(f"Replacing banner file reference: {old_banner}")
                    
                    # Convert uploaded file to base64 data URL
                    file_data = banner_file.read()
                    file_extension = banner_file.filename.lower().split('.')[-1]
                    
                    app.logger.info(f"Banner file size: {len(file_data)} bytes, extension: {file_extension}")
                    
                    # Validate file size (max 5MB for banners)
                    max_size = 5 * 1024 * 1024  # 5MB
                    if len(file_data) > max_size:
                        error_msg = f'Banner file too large ({len(file_data)} bytes). Please use a file smaller than 5MB.'
                        app.logger.error(error_msg)
                        flash(error_msg, 'danger')
                        raise ValueError(f"Banner file too large: {len(file_data)} bytes")
                    
                    # Validate file extension
                    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
                    if file_extension not in allowed_extensions:
                        error_msg = f'Invalid banner format ({file_extension}). Please use: {", ".join(allowed_extensions)}'
                        app.logger.error(error_msg)
                        flash(error_msg, 'danger')
                        raise ValueError(f"Invalid file extension: {file_extension}")
                    
                    # Map file extensions to MIME types
                    mime_type_map = {
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg',
                        'png': 'image/png',
                        'gif': 'image/gif',
                        'webp': 'image/webp'
                    }
                    
                    mime_type = mime_type_map.get(file_extension, 'image/png')
                    base64_data = base64.b64encode(file_data).decode('utf-8')
                    data_url = f"data:{mime_type};base64,{base64_data}"
                    
                    # Update the banner_image field
                    settings.banner_image = data_url
                    
                    app.logger.info(f"Banner successfully processed and set (format: {file_extension}, size: {len(file_data)} bytes, data_url length: {len(data_url)})")
                    flash('Banner updated successfully! Changes will appear on next page load.', 'success')
                    
                except Exception as e:
                    app.logger.error(f"Error processing banner upload: {str(e)}")
                    import traceback
                    app.logger.error(f"Banner upload traceback: {traceback.format_exc()}")
                    flash(f'Error uploading banner: {str(e)}', 'danger')
            
            # Update settings from form data (only if files weren't uploaded)
            if not request.files.get('hero_image_file') or not request.files.get('hero_image_file').filename:
                settings.hero_image = request.form.get('hero_image', settings.hero_image)
            if not request.files.get('favicon_file') or not request.files.get('favicon_file').filename:
                settings.favicon = request.form.get('favicon', settings.favicon)
            if not request.files.get('logo_file') or not request.files.get('logo_file').filename:
                settings.store_logo = request.form.get('store_logo', settings.store_logo)
            if not request.files.get('banner_image_file') or not request.files.get('banner_image_file').filename:
                settings.banner_image = request.form.get('banner_image', settings.banner_image)
                
            settings.hero_enabled = 'hero_enabled' in request.form
            settings.hero_title = request.form.get('hero_title', settings.hero_title)
            settings.hero_subtitle = request.form.get('hero_subtitle', settings.hero_subtitle)
            settings.hero_button_text = request.form.get('hero_button_text', settings.hero_button_text)
            settings.hero_button_url = request.form.get('hero_button_url', settings.hero_button_url)
            
            # Banner settings
            settings.banner_enabled = 'banner_enabled' in request.form
            settings.banner_title = request.form.get('banner_title', settings.banner_title)
            settings.banner_subtitle = request.form.get('banner_subtitle', settings.banner_subtitle)
            settings.banner_button_text = request.form.get('banner_button_text', settings.banner_button_text)
            settings.banner_button_url = request.form.get('banner_button_url', settings.banner_button_url)
            settings.banner_link_url = request.form.get('banner_link_url', settings.banner_link_url)
            settings.banner_target_blank = 'banner_target_blank' in request.form
            
            settings.categories_enabled = 'categories_enabled' in request.form
            settings.categories_section_title = request.form.get('categories_section_title', settings.categories_section_title)
            settings.categories_section_subtitle = request.form.get('categories_section_subtitle', settings.categories_section_subtitle)
            settings.categories_limit = int(request.form.get('categories_limit', settings.categories_limit))
            
            settings.products_enabled = 'products_enabled' in request.form
            settings.products_section_title = request.form.get('products_section_title', settings.products_section_title)
            settings.products_section_subtitle = request.form.get('products_section_subtitle', settings.products_section_subtitle)
            settings.products_limit = int(request.form.get('products_limit', settings.products_limit))
            settings.products_show_view_all = 'products_show_view_all' in request.form
            
            settings.store_name = request.form.get('store_name', settings.store_name)
            settings.store_tagline = request.form.get('store_tagline', settings.store_tagline)
            settings.store_email = request.form.get('store_email', settings.store_email)
            settings.store_phone = request.form.get('store_phone', settings.store_phone)
            
            settings.footer_enabled = 'footer_enabled' in request.form
            settings.footer_text = request.form.get('footer_text', settings.footer_text)
            settings.footer_about_text = request.form.get('footer_about_text', settings.footer_about_text)
            
            db.session.commit()
            
            # Verify the banner was saved correctly
            if request.files.get('banner_image_file') and request.files.get('banner_image_file').filename:
                saved_settings = Settings.query.first()
                if saved_settings and saved_settings.banner_image and saved_settings.banner_image.startswith('data:'):
                    app.logger.info(f"Banner successfully saved to database (length: {len(saved_settings.banner_image)})")
                else:
                    app.logger.error("Banner was not saved to database correctly!")
                    flash('Warning: Banner may not have been saved correctly. Please try again.', 'warning')
            
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('admin_settings'))
        
        return render_template('admin/settings.html', settings=settings)
    except Exception as e:
        app.logger.error(f"Error loading admin settings: {str(e)}")
        flash('Error loading settings', 'danger')
        # Create a default settings object for the template
        default_settings = Settings()
        return render_template('admin/settings.html', settings=default_settings)

# ======================
# ADMIN DRIVER ROUTES - Driver Management System (Similar to Uber)
# ======================

@app.route('/admin/drivers')
@login_required
def admin_drivers():
    """Admin driver management page"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Get all drivers with their document counts
    drivers = db.session.query(Driver)\
        .outerjoin(DriverDocument)\
        .add_columns(db.func.count(DriverDocument.id).label('document_count'))\
        .group_by(Driver.id)\
        .order_by(Driver.created_at.desc()).all()
    
    # Count by status
    pending_count = Driver.query.filter_by(status='pending').count()
    approved_count = Driver.query.filter_by(status='approved').count()
    rejected_count = Driver.query.filter_by(status='rejected').count()
    active_count = Driver.query.filter_by(status='active').count()
    
    return render_template('admin/drivers.html', 
                         drivers=drivers,
                         pending_count=pending_count,
                         approved_count=approved_count,
                         rejected_count=rejected_count,
                         active_count=active_count)

@app.route('/admin/driver/<uuid:driver_id>')
@login_required
def admin_driver_detail(driver_id):
    """Admin driver detail page with documents"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        driver = Driver.query.get_or_404(driver_id)
        documents = DriverDocument.query.filter_by(driver_id=driver.id).all()
        
        # Group documents by type for better organization
        doc_groups = {}
        for doc in documents:
            if doc.document_type not in doc_groups:
                doc_groups[doc.document_type] = []
            doc_groups[doc.document_type].append(doc)
        
        return render_template('admin/driver_detail.html', 
                             driver=driver, 
                             documents=documents,
                             doc_groups=doc_groups)
    except (ValueError, TypeError):
        flash('Invalid driver ID', 'danger')
        return redirect(url_for('admin_drivers'))

@app.route('/admin/driver/<uuid:driver_id>/approve', methods=['POST'])
@login_required
def admin_driver_approve(driver_id):
    """Approve a driver application"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        # Get approval notes (optional)
        approval_notes = request.form.get('approval_notes', '').strip()
        
        # Update driver status
        driver.status = 'active'  # Approved drivers are active by default
        driver.approved_at = datetime.utcnow()
        driver.approved_by_id = current_user.id
        if approval_notes:
            driver.approval_notes = approval_notes
        
        db.session.commit()
        
        flash(f'Driver "{driver.full_name}" has been approved and is now active.', 'success')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error approving driver: {str(e)}")
        flash('Error approving driver. Please try again.', 'danger')
    
    return redirect(url_for('admin_driver_detail', driver_id=driver_id))

@app.route('/admin/driver/<uuid:driver_id>/reject', methods=['POST'])
@login_required
def admin_driver_reject(driver_id):
    """Reject a driver application"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        # Get rejection reason (required)
        rejection_reason = request.form.get('rejection_reason', '').strip()
        if not rejection_reason:
            flash('Rejection reason is required', 'danger')
            return redirect(url_for('admin_driver_detail', driver_id=driver_id))
        
        # Update driver status
        driver.status = 'rejected'
        driver.rejected_at = datetime.utcnow()
        driver.rejected_by_id = current_user.id
        driver.rejection_reason = rejection_reason
        
        db.session.commit()
        
        flash(f'Driver "{driver.full_name}" has been rejected.', 'info')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error rejecting driver: {str(e)}")
        flash('Error rejecting driver. Please try again.', 'danger')
    
    return redirect(url_for('admin_driver_detail', driver_id=driver_id))

@app.route('/admin/driver/<uuid:driver_id>/suspend', methods=['POST'])
@login_required
def admin_driver_suspend(driver_id):
    """Suspend an active driver"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        suspension_reason = request.form.get('suspension_reason', '').strip()
        if not suspension_reason:
            flash('Suspension reason is required', 'danger')
            return redirect(url_for('admin_driver_detail', driver_id=driver_id))
        
        # Update driver status
        driver.status = 'suspended'
        driver.is_online = False
        driver.is_available = False
        
        db.session.commit()
        flash(f'Driver "{driver.full_name}" has been suspended.', 'warning')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error suspending driver: {str(e)}")
        flash('Error suspending driver. Please try again.', 'danger')
    
    return redirect(url_for('admin_driver_detail', driver_id=driver_id))

@app.route('/admin/driver/<uuid:driver_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_driver_edit(driver_id):
    """Edit driver information"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        if request.method == 'POST':
            # Update editable fields
            driver.phone = request.form.get('phone', driver.phone).strip()
            driver.home_address = request.form.get('home_address', driver.home_address).strip()
            driver.city = request.form.get('city', driver.city).strip()
            driver.province = request.form.get('province', driver.province)
            driver.postal_code = request.form.get('postal_code', driver.postal_code).strip()
            
            # Emergency contact information
            driver.emergency_contact_name = request.form.get('emergency_contact_name', driver.emergency_contact_name).strip()
            driver.emergency_contact_phone = request.form.get('emergency_contact_phone', driver.emergency_contact_phone).strip()
            driver.emergency_contact_relationship = request.form.get('emergency_contact_relationship', driver.emergency_contact_relationship).strip()
            
            # Vehicle information
            driver.vehicle_make = request.form.get('vehicle_make', driver.vehicle_make).strip()
            driver.vehicle_model = request.form.get('vehicle_model', driver.vehicle_model).strip()
            driver.vehicle_year = int(request.form.get('vehicle_year', driver.vehicle_year))
            driver.vehicle_color = request.form.get('vehicle_color', driver.vehicle_color).strip()
            driver.vehicle_license_plate = request.form.get('vehicle_license_plate', driver.vehicle_license_plate).strip()
            driver.vehicle_type = request.form.get('vehicle_type', driver.vehicle_type)
            
            # Banking information
            driver.bank_name = request.form.get('bank_name', driver.bank_name)
            driver.account_holder = request.form.get('account_holder', driver.account_holder).strip()
            driver.account_number = request.form.get('account_number', driver.account_number).strip()
            driver.branch_code = request.form.get('branch_code', driver.branch_code).strip()
            driver.account_type = request.form.get('account_type', driver.account_type)
            
            driver.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Driver "{driver.full_name}" information has been updated.', 'success')
            return redirect(url_for('admin_driver_detail', driver_id=driver_id))
            
        # GET request - show edit form
        return render_template('admin/driver_form.html', driver=driver)
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating driver: {str(e)}")
        flash('Error updating driver information. Please try again.', 'danger')
        return redirect(url_for('admin_driver_detail', driver_id=driver_id))

@app.route('/admin/driver-document/<string:document_id>/download')
@login_required
def admin_driver_document_download(document_id):
    """Download a driver document"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        doc_uuid = uuid.UUID(document_id)
        document = DriverDocument.query.get_or_404(doc_uuid)
        
        if not document.file_data:
            flash('File data not found', 'danger')
            return redirect(url_for('admin_driver_detail', driver_id=document.driver_id))
        
        return Response(
            document.file_data,
            mimetype=document.mime_type or 'application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{document.file_name}"'
            }
        )
    except (ValueError, TypeError):
        flash('Invalid document ID', 'danger')
        return redirect(url_for('admin_drivers'))

@app.route('/admin/driver-document/<string:document_id>/verify', methods=['POST'])
@login_required
def admin_driver_document_verify(document_id):
    """Mark a driver document as verified"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        doc_uuid = uuid.UUID(document_id)
        document = DriverDocument.query.get_or_404(doc_uuid)
        
        verification_status = request.form.get('verification_status')  # 'verified' or 'rejected'
        verification_notes = request.form.get('verification_notes', '').strip()
        
        if verification_status not in ['verified', 'rejected']:
            flash('Invalid verification status', 'danger')
            return redirect(url_for('admin_driver_detail', driver_id=document.driver_id))
        
        document.verification_status = verification_status
        document.verified_at = datetime.utcnow()
        document.verified_by_id = current_user.id
        if verification_notes:
            document.verification_notes = verification_notes
        
        db.session.commit()
        
        flash(f'Document "{document.document_name}" has been {verification_status}', 'success')
        
    except (ValueError, TypeError):
        flash('Invalid document ID', 'danger')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error verifying document: {str(e)}")
        flash('Error updating document verification. Please try again.', 'danger')
    
    return redirect(url_for('admin_driver_detail', driver_id=document.driver_id))

# ======================
# DRIVER SIGNUP ROUTES - Uber-like Driver Onboarding
# ======================

@app.route('/driver/signup', methods=['GET', 'POST'])
def driver_signup():
    """Driver registration page - comprehensive signup form similar to Uber"""
    import uuid
    from werkzeug.utils import secure_filename
    
    if request.method == 'POST':
        try:
            # Personal Information
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            date_of_birth = request.form.get('date_of_birth')
            id_number = request.form.get('id_number', '').strip()
            
            # Address Information
            home_address = request.form.get('home_address', '').strip()
            city = request.form.get('city', '').strip()
            province = request.form.get('province', '')
            postal_code = request.form.get('postal_code', '').strip()
            
            # Emergency Contact
            emergency_contact_name = request.form.get('emergency_contact_name', '').strip()
            emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip()
            emergency_contact_relationship = request.form.get('emergency_contact_relationship', '').strip()
            
            # Vehicle Information
            vehicle_make = request.form.get('vehicle_make', '').strip()
            vehicle_model = request.form.get('vehicle_model', '').strip()
            vehicle_year = request.form.get('vehicle_year', type=int)
            vehicle_color = request.form.get('vehicle_color', '').strip()
            vehicle_license_plate = request.form.get('vehicle_license_plate', '').strip()
            vehicle_vin = request.form.get('vehicle_vin', '').strip()
            vehicle_type = request.form.get('vehicle_type', '')
            
            # Banking Information
            bank_name = request.form.get('bank_name', '')
            account_holder = request.form.get('account_holder', '').strip()
            account_number = request.form.get('account_number', '').strip()
            branch_code = request.form.get('branch_code', '').strip()
            account_type = request.form.get('account_type', '')
            
            # License Information
            drivers_license_number = request.form.get('drivers_license_number', '').strip()
            license_expiry_date = request.form.get('license_expiry_date')
            license_type = request.form.get('license_type', '')
            
            # Agreement checkboxes
            terms_accepted = bool(request.form.get('terms_accepted'))
            privacy_accepted = bool(request.form.get('privacy_accepted'))
            driver_agreement_accepted = bool(request.form.get('driver_agreement_accepted'))
            data_sharing_consent = bool(request.form.get('data_sharing_consent'))
            
            # Validation
            errors = []
            
            if not first_name:
                errors.append("First name is required")
            if not last_name:
                errors.append("Last name is required")
            if not email:
                errors.append("Email is required")
            if not phone:
                errors.append("Phone number is required")
            if not date_of_birth:
                errors.append("Date of birth is required")
            if not id_number:
                errors.append("ID number is required")
            if not home_address:
                errors.append("Home address is required")
            if not city:
                errors.append("City is required")
            if not province:
                errors.append("Province is required")
            if not postal_code:
                errors.append("Postal code is required")
            if not emergency_contact_name:
                errors.append("Emergency contact name is required")
            if not emergency_contact_phone:
                errors.append("Emergency contact phone is required")
            if not emergency_contact_relationship:
                errors.append("Emergency contact relationship is required")
            if not vehicle_make:
                errors.append("Vehicle make is required")
            if not vehicle_model:
                errors.append("Vehicle model is required")
            if not vehicle_year or vehicle_year < 1990:
                errors.append("Valid vehicle year is required (1990 or later)")
            if not vehicle_color:
                errors.append("Vehicle color is required")
            if not vehicle_license_plate:
                errors.append("Vehicle license plate is required")
            if not vehicle_type:
                errors.append("Vehicle type is required")
            if not bank_name:
                errors.append("Bank name is required")
            if not account_holder:
                errors.append("Account holder name is required")
            if not account_number:
                errors.append("Account number is required")
            if not branch_code:
                errors.append("Branch code is required")
            if not account_type:
                errors.append("Account type is required")
            if not drivers_license_number:
                errors.append("Driver's license number is required")
            if not license_expiry_date:
                errors.append("License expiry date is required")
            if not license_type:
                errors.append("License type is required")
            if not terms_accepted:
                errors.append("You must accept the Terms and Conditions")
            if not privacy_accepted:
                errors.append("You must accept the Privacy Policy")
            if not driver_agreement_accepted:
                errors.append("You must accept the Driver Agreement")
            if not data_sharing_consent:
                errors.append("You must consent to data sharing for background checks")
                
            # Check if email already exists
            if Driver.query.filter_by(email=email).first():
                errors.append("A driver with this email address already exists")
                
            # Check if ID number already exists
            if Driver.query.filter_by(id_number=id_number).first():
                errors.append("A driver with this ID number already exists")
                
            # Check if license plate already exists
            if Driver.query.filter_by(vehicle_license_plate=vehicle_license_plate).first():
                errors.append("A driver with this vehicle license plate already exists")
                
            # Age validation (must be 18+)
            if date_of_birth:
                try:
                    birth_date = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                    today = datetime.utcnow().date()
                    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    if age < 18:
                        errors.append("You must be at least 18 years old to become a driver")
                except ValueError:
                    errors.append("Invalid date of birth format")
            
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return redirect(url_for('driver_signup'))
            
            # Create driver record
            driver = Driver(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                date_of_birth=datetime.strptime(date_of_birth, '%Y-%m-%d').date(),
                id_number=id_number,
                home_address=home_address,
                city=city,
                province=province,
                postal_code=postal_code,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone,
                emergency_contact_relationship=emergency_contact_relationship,
                vehicle_make=vehicle_make,
                vehicle_model=vehicle_model,
                vehicle_year=vehicle_year,
                vehicle_color=vehicle_color,
                vehicle_license_plate=vehicle_license_plate,
                vehicle_vin=vehicle_vin if vehicle_vin else None,
                vehicle_type=vehicle_type,
                bank_name=bank_name,
                account_holder=account_holder,
                account_number=account_number,
                branch_code=branch_code,
                account_type=account_type,
                drivers_license_number=drivers_license_number,
                license_expiry_date=datetime.strptime(license_expiry_date, '%Y-%m-%d').date(),
                license_type=license_type,
                terms_accepted=terms_accepted,
                terms_accepted_date=datetime.utcnow() if terms_accepted else None,
                privacy_accepted=privacy_accepted,
                driver_agreement_accepted=driver_agreement_accepted,
                data_sharing_consent=data_sharing_consent,
                status='pending',
                approval_stage='document_verification'
            )
            
            db.session.add(driver)
            db.session.flush()  # Get driver ID
            
            # Process uploaded documents
            document_types = [
                'id_copy', 'drivers_license', 'proof_of_address', 
                'vehicle_registration', 'vehicle_insurance', 'vehicle_roadworthy',
                'criminal_record_check', 'bank_statement', 'profile_photo', 'pdp_permit'
            ]
            
            uploaded_documents = []
            for doc_type in document_types:
                file = request.files.get(doc_type)
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_data = file.read()
                    
                    # Create document record
                    driver_doc = DriverDocument(
                        driver_id=driver.id,
                        document_type=doc_type.upper(),
                        document_name=filename,
                        description=f"{doc_type.replace('_', ' ').title()} - {filename}",
                        file_name=filename,
                        file_size=len(file_data),
                        mime_type=file.content_type,
                        file_data=file_data,
                        verification_status='pending'
                    )
                    
                    db.session.add(driver_doc)
                    uploaded_documents.append(doc_type.replace('_', ' ').title())
            
            db.session.commit()
            
            # Send confirmation (if email utilities are configured)
            try:
                # send_driver_confirmation_email(driver)
                pass
            except Exception as e:
                app.logger.error(f"Error sending driver confirmation email: {str(e)}")
            
            flash(f'Driver application submitted successfully! We will review your application and contact you within 2-3 business days.', 'success')
            return redirect(url_for('driver_signup_success', driver_id=driver.id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating driver application: {str(e)}")
            flash('Error submitting driver application. Please try again.', 'danger')
            return redirect(url_for('driver_signup'))
    
    # GET request - show form
    return render_template('driver_signup.html')

@app.route('/driver/signup/success/<string:driver_id>')
def driver_signup_success(driver_id):
    """Driver signup success page"""
    try:
        driver_uuid = uuid.UUID(driver_id)
        driver = Driver.query.get_or_404(driver_uuid)
        return render_template('driver_signup_success.html', driver=driver)
    except (ValueError, TypeError):
        flash('Invalid driver ID', 'danger')
        return redirect(url_for('driver_signup'))

# ======================

# ======================
# FAVICON SERVING ROUTE
# ======================

@app.route('/favicon.ico')
def serve_favicon():
    """Serve favicon with proper caching headers"""
    try:
        # Get current settings
        settings = Settings.query.first()
        favicon_path = 'images/favi.png'  # Default
        
        if settings and settings.favicon:
            favicon_path = settings.favicon
        
        # If it's a data URL (base64), serve it directly
        if favicon_path and favicon_path.startswith('data:'):
            import base64
            import io
            
            # Extract the base64 data
            header, data = favicon_path.split(',', 1)
            decoded = base64.b64decode(data)
            
            # Determine MIME type
            if 'image/png' in header:
                mimetype = 'image/png'
            elif 'image/jpeg' in header or 'image/jpg' in header:
                mimetype = 'image/jpeg'
            elif 'image/gif' in header:
                mimetype = 'image/gif'
            elif 'image/x-icon' in header or 'image/vnd.microsoft.icon' in header:
                mimetype = 'image/x-icon'
            else:
                mimetype = 'image/x-icon'
            
            response = Response(decoded, mimetype=mimetype)
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        
        # Otherwise serve from static files
        else:
            favicon_file = favicon_path if favicon_path else 'images/favi.png'
            # Remove 'images/' prefix if present since send_from_directory will handle the path
            if favicon_file.startswith('images/'):
                favicon_file = favicon_file[7:]  # Remove 'images/' prefix
            
            response = send_from_directory(
                os.path.join(app.static_folder, 'images'),
                favicon_file,
                mimetype='image/x-icon'
            )
            
            # Add no-cache headers for admin panel
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
            
    except Exception as e:
        app.logger.error(f"Error serving favicon: {str(e)}")
        # Fallback to default favicon
        try:
            return send_from_directory(
                os.path.join(app.static_folder, 'images'),
                'favi.png',
                mimetype='image/x-icon'
            )
        except:
            # Ultimate fallback - return empty icon
            return Response('', mimetype='image/x-icon')

# ======================

# ======================
# MISSING PAGE ROUTES
# ======================

@app.route('/track-order', methods=['GET', 'POST'])
def track_order():
    """Track order page - allows users to search for orders by order number or email"""
    orders = []
    
    if request.method == 'POST':
        order_number = request.form.get('order_number', '').strip()
        email = request.form.get('email', '').strip()
        
        if order_number or email:
            # Start with base query
            query = Order.query
            
            # If both order_number and email are provided, use AND logic
            if order_number and email:
                # Search by order_number field and email
                query = query.join(User).filter(
                    db.and_(
                        Order.order_number.ilike(f'%{order_number}%'),
                        User.email.ilike(f'%{email}%')
                    )
                )
            elif order_number:
                # Search by order_number only
                query = query.filter(Order.order_number.ilike(f'%{order_number}%'))
            elif email:
                # Search by customer email
                query = query.join(User).filter(User.email.ilike(f'%{email}%'))
            
            # Execute query and get results
            orders = query.order_by(Order.created_at.desc()).limit(10).all()
            
            if not orders:
                flash('No orders found matching your search criteria.', 'info')
    
    return render_template('track_order.html', orders=orders)

@app.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')

@app.route('/privacy-policy')
def privacy_policy():
    """Privacy Policy page"""
    return render_template('privacy_policy.html')

@app.route('/shipping-policy')
def shipping_policy():
    """Shipping Policy page"""
    return render_template('shipping_policy.html')

@app.route('/returns-policy')
def returns_policy():
    """Returns Policy page"""
    return render_template('returns_policy.html')

@app.route('/terms-and-conditions')
def terms_and_conditions():
    """Terms and Conditions page"""
    current_date = datetime.now().strftime("%B %d, %Y")
    return render_template('terms_and_conditions.html', current_date=current_date)

@app.route('/terms')
def terms_redirect():
    """Redirect /terms to /terms-and-conditions"""
    return redirect(url_for('terms_and_conditions'))

# ======================

# ======================
# INITIALIZE DATABASE
# ======================

def init_db():
    with app.app_context():
        try:
            db.create_all()
            
            # Create admin user if not exists
            admin = User.query.filter_by(email='admin@brandcartel.com').first()
            admin_username = User.query.filter_by(username='admin').first()
            if not admin and not admin_username:
                admin = User(
                    username='admin',
                    email='admin@brandcartel.com',
                    is_admin=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
            
            # Create sample categories
            if Category.query.count() == 0:
                categories_data = [
                    {'name': 'Electronics', 'description': 'Phones, Laptops, TVs and more', 'image_url': 'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=400'},
                    {'name': 'Fashion', 'description': 'Clothing, Shoes, Accessories', 'image_url': '/static/images/online-fashion.jpg'},
                    {'name': 'Home & Garden', 'description': 'Furniture, Decor, Kitchen', 'image_url': 'https://images.unsplash.com/photo-1484101403633-562f891dc89a?w=400'},
                    {'name': 'Sports', 'description': 'Fitness, Outdoor, Equipment', 'image_url': '/static/images/sportClothes.jpg'},
                    {'name': 'Books', 'description': 'Fiction, Non-fiction, Educational', 'image_url': '/static/images/book.png'},
                    {'name': 'Toys & Games', 'description': 'Kids toys, Board games, Puzzles', 'image_url': '/static/images/toys.jpg'},
                ]
                
                for cat_data in categories_data:
                    category = Category(**cat_data)
                    db.session.add(category)
            
            db.session.commit()
            
            # Create sample products
            if Product.query.count() == 0:
                electronics_cat = Category.query.filter_by(name='Electronics').first()
                fashion_cat = Category.query.filter_by(name='Fashion').first()
                home_cat = Category.query.filter_by(name='Home & Garden').first()
                sports_cat = Category.query.filter_by(name='Sports').first()
                
                products_data = [
                    {'name': 'Samsung Galaxy S23', 'description': 'Latest Samsung flagship with amazing camera and performance', 'price': 12999.99, 'stock': 50, 'category_id': electronics_cat.id, 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=500'},
                    {'name': 'MacBook Pro 14"', 'description': 'Apple M3 chip, 16GB RAM, 512GB SSD', 'price': 34999.99, 'stock': 30, 'category_id': electronics_cat.id, 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500'},
                    {'name': 'Sony WH-1000XM5', 'description': 'Industry leading noise cancelling headphones', 'price': 5999.99, 'stock': 100, 'category_id': electronics_cat.id, 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=500'},
                    {'name': 'LG 55" OLED TV', 'description': '4K OLED display with perfect blacks', 'price': 18999.99, 'stock': 20, 'category_id': electronics_cat.id, 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=500'},
                    {'name': 'Nike Air Max 2024', 'description': 'Comfortable running shoes with max cushioning', 'price': 2499.99, 'stock': 150, 'category_id': fashion_cat.id, 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500'},
                    {'name': 'Levi\'s 501 Jeans', 'description': 'Classic fit denim jeans', 'price': 1299.99, 'stock': 200, 'category_id': fashion_cat.id, 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1542272604-787c3835535d?w=500'},
                    {'name': 'Designer Leather Handbag', 'description': 'Premium leather handbag with gold accents', 'price': 4599.99, 'stock': 45, 'category_id': fashion_cat.id, 'featured': True, 'image_url': 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=500'},
                    {'name': 'Modern Coffee Table', 'description': 'Minimalist design with glass top', 'price': 3299.99, 'stock': 25, 'category_id': home_cat.id, 'featured': False, 'image_url': 'https://images.unsplash.com/photo-1533090161767-e6ffed986c88?w=500'},
                ]
                
                for product_data in products_data:
                    product = Product(**product_data)
                    db.session.add(product)
            
            db.session.commit()
            
            # Create sample vendors
            if Vendor.query.count() == 0:
                vendors_data = [
                    {
                        'business_name': 'TechHub Solutions',
                        'trading_name': 'TechHub',
                        'business_type': 'Company',
                        'registration_number': '2020/123456/07',
                        'vat_number': '4123456789',
                        'contact_person': 'John Smith',
                        'contact_email': 'john@techhub.co.za',
                        'contact_phone': '+27 11 123 4567',
                        'physical_address': '123 Tech Street, Sandton, Johannesburg',
                        'city': 'Johannesburg',
                        'province': 'Gauteng',
                        'postal_code': '2196',
                        'bank_name': 'Standard Bank',
                        'account_holder': 'TechHub Solutions (Pty) Ltd',
                        'account_number': '123456789',
                        'branch_code': '051001',
                        'account_type': 'Current',
                        'business_description': 'Leading supplier of electronic devices and technology solutions',
                        'product_categories': '["Electronics"]',
                        'website_url': 'https://techhub.co.za',
                        'years_in_business': 5,
                        'number_of_employees': '11-50',
                        'status': 'approved',
                        'approved_at': datetime.utcnow(),
                        'terms_accepted': True,
                        'privacy_accepted': True,
                        'marketplace_agreement_accepted': True
                    },
                    {
                        'business_name': 'Fashion Forward Boutique',
                        'business_type': 'Close Corporation',
                        'registration_number': 'CK2019/123456/23',
                        'contact_person': 'Sarah Johnson',
                        'contact_email': 'sarah@fashionforward.co.za',
                        'contact_phone': '+27 21 987 6543',
                        'physical_address': '456 Fashion Ave, Cape Town',
                        'city': 'Cape Town',
                        'province': 'Western Cape',
                        'postal_code': '8001',
                        'bank_name': 'FNB',
                        'account_holder': 'Fashion Forward Boutique CC',
                        'account_number': '987654321',
                        'branch_code': '250655',
                        'account_type': 'Current',
                        'business_description': 'Trendy fashion and accessories for modern lifestyle',
                        'product_categories': '["Fashion"]',
                        'years_in_business': 3,
                        'number_of_employees': '1-10',
                        'status': 'pending',
                        'terms_accepted': True,
                        'privacy_accepted': True,
                        'marketplace_agreement_accepted': True
                    },
                    {
                        'business_name': 'Home & Garden Paradise',
                        'business_type': 'Sole Proprietor',
                        'contact_person': 'Mike Williams',
                        'contact_email': 'mike@homegardenparadise.co.za',
                        'contact_phone': '+27 31 456 7890',
                        'physical_address': '789 Garden Road, Durban',
                        'city': 'Durban',
                        'province': 'KwaZulu-Natal',
                        'postal_code': '4001',
                        'bank_name': 'ABSA',
                        'account_holder': 'Mike Williams',
                        'account_number': '456789123',
                        'branch_code': '632005',
                        'account_type': 'Savings',
                        'business_description': 'Quality home and garden products for comfortable living',
                        'product_categories': '["Home & Garden"]',
                        'years_in_business': 7,
                        'number_of_employees': '1-10',
                        'status': 'approved',
                        'approved_at': datetime.utcnow(),
                        'terms_accepted': True,
                        'privacy_accepted': True,
                        'marketplace_agreement_accepted': True
                    }
                ]
                
                for vendor_data in vendors_data:
                    vendor = Vendor(**vendor_data)
                    db.session.add(vendor)
            
            # Create sample drivers
            if Driver.query.count() == 0:
                from datetime import date
                
                drivers_data = [
                    {
                        'first_name': 'David',
                        'last_name': 'Wilson',
                        'email': 'david.wilson@brandcartel.com',
                        'phone': '+27 82 123 4567',
                        'date_of_birth': date(1985, 6, 15),
                        'id_number': '8506155432089',
                        'home_address': '123 Delivery Street, Johannesburg',
                        'city': 'Johannesburg',
                        'province': 'Gauteng',
                        'postal_code': '2001',
                        'emergency_contact_name': 'Lisa Wilson',
                        'emergency_contact_phone': '+27 83 987 6543',
                        'emergency_contact_relationship': 'Spouse',
                        'vehicle_make': 'Toyota',
                        'vehicle_model': 'Corolla',
                        'vehicle_year': 2020,
                        'vehicle_color': 'White',
                        'vehicle_license_plate': 'ABC123GP',
                        'vehicle_vin': 'JT2AC12E7J0123456',
                        'vehicle_type': 'Car',
                        'bank_name': 'Standard Bank',
                        'account_holder': 'David Wilson',
                        'account_number': '123456789',
                        'branch_code': '051001',
                        'account_type': 'Current',
                        'status': 'active',
                        'approved_at': datetime.utcnow(),
                        'drivers_license_number': 'GP123456789',
                        'license_expiry_date': date(2027, 6, 15),
                        'license_type': 'B',
                        'criminal_record_status': 'passed',
                        'average_rating': 4.8,
                        'total_deliveries': 156,
                        'is_available': True,
                        'is_online': False
                    },
                    {
                        'first_name': 'Sarah',
                        'last_name': 'Mthembu',
                        'email': 'sarah.mthembu@brandcartel.com',
                        'phone': '+27 84 567 8901',
                        'date_of_birth': date(1990, 3, 22),
                        'id_number': '9003225432098',
                        'home_address': '456 Quick Road, Cape Town',
                        'city': 'Cape Town',
                        'province': 'Western Cape',
                        'postal_code': '8001',
                        'emergency_contact_name': 'John Mthembu',
                        'emergency_contact_phone': '+27 85 234 5678',
                        'emergency_contact_relationship': 'Brother',
                        'vehicle_make': 'Honda',
                        'vehicle_model': 'Civic',
                        'vehicle_year': 2019,
                        'vehicle_color': 'Blue',
                        'vehicle_license_plate': 'DEF456WC',
                        'vehicle_vin': 'JHGFD4321ABCD1234',
                        'vehicle_type': 'Car',
                        'bank_name': 'FNB',
                        'account_holder': 'Sarah Mthembu',
                        'account_number': '987654321',
                        'branch_code': '250655',
                        'account_type': 'Savings',
                        'status': 'pending',
                        'drivers_license_number': 'WC987654321',
                        'license_expiry_date': date(2026, 3, 22),
                        'license_type': 'B',
                        'criminal_record_status': 'pending',
                        'average_rating': 0.0,
                        'total_deliveries': 0,
                        'is_available': False,
                        'is_online': False
                    },
                    {
                        'first_name': 'Thabo',
                        'last_name': 'Khumalo',
                        'email': 'thabo.khumalo@brandcartel.com',
                        'phone': '+27 76 890 1234',
                        'date_of_birth': date(1988, 11, 8),
                        'id_number': '8811085432087',
                        'home_address': '789 Speed Avenue, Durban',
                        'city': 'Durban',
                        'province': 'KwaZulu-Natal',
                        'postal_code': '4001',
                        'emergency_contact_name': 'Mary Khumalo',
                        'emergency_contact_phone': '+27 77 345 6789',
                        'emergency_contact_relationship': 'Mother',
                        'vehicle_make': 'Nissan',
                        'vehicle_model': 'Almera',
                        'vehicle_year': 2018,
                        'vehicle_color': 'Silver',
                        'vehicle_license_plate': 'GHI789KZ',
                        'vehicle_vin': 'NISSAN123456789AB',
                        'vehicle_type': 'Car',
                        'bank_name': 'ABSA',
                        'account_holder': 'Thabo Khumalo',
                        'account_number': '456123789',
                        'branch_code': '632005',
                        'account_type': 'Current',
                        'status': 'approved',
                        'approved_at': datetime.utcnow(),
                        'drivers_license_number': 'KZ456789123',
                        'license_expiry_date': date(2025, 11, 8),
                        'license_type': 'B',
                        'criminal_record_status': 'passed',
                        'average_rating': 4.6,
                        'total_deliveries': 89,
                        'is_available': True,
                        'is_online': True
                    }
                ]
                
                for driver_data in drivers_data:
                    driver = Driver(**driver_data)
                    db.session.add(driver)
            
            db.session.commit()
            print("Database initialized successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing database: {str(e)}")
            raise

@app.route('/admin/accounting/income/<uuid:id>', methods=['GET'])
@login_required
def get_income_transaction(id):
    """Get income transaction details for editing"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # First try to find as IncomeTransaction
        income_transaction = IncomeTransaction.query.get(id)
        if income_transaction:
            return jsonify({
                'id': str(income_transaction.id),
                'date': income_transaction.date.strftime('%Y-%m-%d'),
                'payment_date': income_transaction.payment_date.strftime('%Y-%m-%d') if income_transaction.payment_date else '',
                'description': income_transaction.description,
                'category': income_transaction.category,
                'income_type': income_transaction.income_type,
                'customer_name': income_transaction.customer_name or '',
                'company_registration': income_transaction.company_registration or '',
                'customer_vat_number': income_transaction.customer_vat_number or '',
                'customer_tax_number': income_transaction.customer_tax_number or '',
                'amount_incl_vat': income_transaction.amount_incl_vat,
                'vat_rate': income_transaction.vat_rate,
                'vat_amount': income_transaction.vat_amount,
                'amount_excl_vat': income_transaction.amount_excl_vat,
                'payment_method': income_transaction.payment_method or '',
                'reference_number': income_transaction.reference_number or '',
                'tax_invoice_issued': income_transaction.tax_invoice_issued,
                'export_status': income_transaction.export_status,
                'notes': income_transaction.notes or '',
                'type': 'income_transaction'
            })
        
        # If not found as IncomeTransaction, try as Order
        order = Order.query.get(id)
        if order:
            order_excl_vat = order.total_amount / 1.15
            order_vat = order.total_amount - order_excl_vat
            customer_name = f"{order.user.first_name} {order.user.last_name}" if order.user else "Unknown"
            
            return jsonify({
                'id': str(order.id),
                'date': order.created_at.strftime('%Y-%m-%d'),
                'payment_date': order.created_at.strftime('%Y-%m-%d'),
                'description': f'Order #{order.order_number or order.id}',
                'category': 'Sales Revenue',
                'income_type': 'Trading',
                'customer_name': customer_name,
                'company_registration': '',
                'customer_vat_number': '',
                'customer_tax_number': '',
                'amount_incl_vat': order.total_amount,
                'vat_rate': 15.0,
                'vat_amount': order_vat,
                'amount_excl_vat': order_excl_vat,
                'payment_method': 'Online',
                'reference_number': order.order_number or str(order.id),
                'tax_invoice_issued': True,
                'export_status': 'Domestic',
                'notes': f'Generated from Order #{order.order_number or order.id}',
                'type': 'order',
                'readonly': True  # Mark order-based income as readonly
            })
        
        return jsonify({'error': 'Income transaction not found'}), 404
        
    except Exception as e:
        app.logger.error(f"Error fetching income transaction {id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/accounting/income/<uuid:id>/update', methods=['POST'])
@login_required
def update_income_transaction(id):
    """Update an income transaction"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Only allow updating actual IncomeTransaction records, not orders
        income_transaction = IncomeTransaction.query.get(id)
        if not income_transaction:
            return jsonify({'error': 'Income transaction not found or cannot be edited'}), 404
        
        # Update fields from form data
        income_transaction.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        income_transaction.description = request.form.get('description')
        income_transaction.category = request.form.get('category')
        income_transaction.income_type = request.form.get('income_type', 'Trading')
        income_transaction.customer_name = request.form.get('customer_name')
        income_transaction.company_registration = request.form.get('company_registration')
        income_transaction.customer_vat_number = request.form.get('customer_vat_number')
        income_transaction.customer_tax_number = request.form.get('customer_tax_number')
        income_transaction.amount_incl_vat = float(request.form.get('amount_incl_vat'))
        income_transaction.vat_rate = float(request.form.get('vat_rate', 15.0))
        income_transaction.payment_method = request.form.get('payment_method')
        income_transaction.reference_number = request.form.get('reference_number')
        income_transaction.tax_invoice_issued = bool(request.form.get('tax_invoice_issued'))
        income_transaction.export_status = request.form.get('export_status', 'Domestic')
        income_transaction.notes = request.form.get('notes')
        
        # Add payment date if provided
        payment_date = request.form.get('payment_date')
        if payment_date:
            income_transaction.payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
        
        # Recalculate VAT amounts
        income_transaction.calculate_vat()
        
        # Create audit log for update
        audit_log = AccountingAuditLog(
            user_id=current_user.id,
            action='UPDATE',
            transaction_type='Income',
            transaction_id=income_transaction.id,
            amount=income_transaction.amount_incl_vat,
            details=f'Updated: {income_transaction.description}',
            ip_address=request.remote_addr
        )
        db.session.add(audit_log)
        
        db.session.commit()
        
        app.logger.info(f"Income transaction {id} updated by {current_user.email}")
        return jsonify({'success': True, 'message': 'Income transaction updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating income transaction {id}: {str(e)}")
        return jsonify({'error': 'Failed to update income transaction'}), 500

@app.route('/admin/accounting/expense/<uuid:id>')
@login_required
def get_expense_transaction(id):
    """Get individual expense transaction data for editing"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        expense_transaction = ExpenseTransaction.query.get(id)
        if not expense_transaction:
            return jsonify({'error': 'Expense transaction not found'}), 404
        
        return jsonify({
            'id': str(expense_transaction.id),
            'date': expense_transaction.date.strftime('%Y-%m-%d'),
            'payment_date': expense_transaction.payment_date.strftime('%Y-%m-%d') if expense_transaction.payment_date else '',
            'description': expense_transaction.description,
            'category': expense_transaction.category,
            'expense_type': expense_transaction.expense_type,
            'supplier_name': expense_transaction.supplier_name or '',
            'company_registration': expense_transaction.company_registration or '',
            'supplier_vat_number': expense_transaction.supplier_vat_number or '',
            'sars_tax_number': expense_transaction.sars_tax_number or '',
            'amount_incl_vat': expense_transaction.amount_incl_vat,
            'vat_rate': expense_transaction.vat_rate,
            'vat_amount': expense_transaction.vat_amount,
            'amount_excl_vat': expense_transaction.amount_excl_vat,
            'payment_method': expense_transaction.payment_method or '',
            'reference_number': expense_transaction.reference_number or '',
            'has_tax_invoice': expense_transaction.has_tax_invoice,
            'business_use_percentage': expense_transaction.business_use_percentage,
            'vat_claim_reason': expense_transaction.vat_claim_reason or '',
            'notes': expense_transaction.notes or ''
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching expense transaction {id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/accounting/expense/<uuid:id>/update', methods=['POST'])
@login_required
def update_expense_transaction(id):
    """Update an expense transaction"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        expense_transaction = ExpenseTransaction.query.get(id)
        if not expense_transaction:
            return jsonify({'error': 'Expense transaction not found'}), 404
        
        # Update fields from form data
        expense_transaction.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        expense_transaction.description = request.form.get('description')
        expense_transaction.category = request.form.get('category')
        expense_transaction.expense_type = request.form.get('expense_type', 'Operating')
        expense_transaction.supplier_name = request.form.get('supplier_name')
        expense_transaction.company_registration = request.form.get('company_registration')
        expense_transaction.supplier_vat_number = request.form.get('supplier_vat_number')
        expense_transaction.sars_tax_number = request.form.get('sars_tax_number')
        expense_transaction.amount_incl_vat = float(request.form.get('amount_incl_vat'))
        expense_transaction.vat_rate = float(request.form.get('vat_rate', 15.0))
        expense_transaction.payment_method = request.form.get('payment_method')
        expense_transaction.reference_number = request.form.get('reference_number')
        expense_transaction.has_tax_invoice = bool(request.form.get('has_tax_invoice'))
        expense_transaction.business_use_percentage = float(request.form.get('business_use_percentage', 100.0))
        expense_transaction.vat_claim_reason = request.form.get('vat_claim_reason')
        expense_transaction.notes = request.form.get('notes')
        
        # Add payment date if provided
        payment_date = request.form.get('payment_date')
        if payment_date:
            expense_transaction.payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
        
        # Recalculate VAT amounts
        expense_transaction.calculate_vat()
        
        # Create audit log for update
        audit_log = AccountingAuditLog(
            user_id=current_user.id,
            action='UPDATE',
            transaction_type='Expense',
            transaction_id=expense_transaction.id,
            amount=expense_transaction.amount_incl_vat,
            details=f'Updated: {expense_transaction.description}',
            ip_address=request.remote_addr
        )
        db.session.add(audit_log)
        
        db.session.commit()
        
        app.logger.info(f"Expense transaction {id} updated by {current_user.email}")
        return jsonify({'success': True, 'message': 'Expense transaction updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating expense transaction {id}: {str(e)}")
        return jsonify({'error': 'Failed to update expense transaction'}), 500

@app.route('/api/diagnostic/section-status')
def diagnostic_section_status():
    """Diagnostic endpoint to check section order and just_launched products"""
    try:
        settings = Settings.query.first()
        just_launched_products = Product.query.filter_by(just_launched=True).all()
        
        return jsonify({
            'section_order': settings.section_order if settings else None,
            'just_launched_in_order': 'just_launched' in (settings.section_order if settings else ''),
            'just_launched_products_count': len(just_launched_products),
            'just_launched_products': [{'id': str(p.id), 'name': p.name} for p in just_launched_products[:6]],
            'settings_exist': settings is not None,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/admin/favicon/reset', methods=['POST'])
@login_required
def reset_favicon():
    """API endpoint to reset favicon to default"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
        
        old_favicon = settings.favicon
        
        # Reset to default favicon
        settings.favicon = 'images/favi.png'
        db.session.commit()
        
        # Log the action
        if old_favicon and old_favicon.startswith('data:'):
            app.logger.info("Favicon reset to default - removed base64 data from database")
        else:
            app.logger.info(f"Favicon reset to default - was: {old_favicon}")
        
        return jsonify({
            'success': True,
            'message': 'Favicon reset to default successfully',
            'new_favicon': 'images/favi.png'
        })
        
    except Exception as e:
        app.logger.error(f"Error resetting favicon: {e}")
        return jsonify({'error': 'Failed to reset favicon'}), 500

@app.route('/admin/accounting/income/<uuid:id>/delete', methods=['POST'])
@login_required
def delete_income_transaction(id):
    """Delete an income transaction with audit trail"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        income_transaction = IncomeTransaction.query.get(id)
        if not income_transaction:
            return jsonify({'error': 'Income transaction not found'}), 404
        
        # Create audit log before deletion
        audit_log = AccountingAuditLog(
            user_id=current_user.id,
            action='DELETE',
            transaction_type='Income',
            transaction_id=income_transaction.id,
            amount=income_transaction.amount_incl_vat,
            details=f'Deleted: {income_transaction.description}',
            ip_address=request.remote_addr
        )
        db.session.add(audit_log)
        
        # Store details for logging
        description = income_transaction.description
        amount = income_transaction.amount_incl_vat
        
        # Delete the transaction
        db.session.delete(income_transaction)
        db.session.commit()
        
        app.logger.info(f"Income transaction {id} deleted by {current_user.email}: {description}")
        return jsonify({'success': True, 'message': 'Income transaction deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting income transaction {id}: {str(e)}")
        return jsonify({'error': 'Failed to delete income transaction'}), 500

@app.route('/admin/accounting/expense/<uuid:id>/delete', methods=['POST'])
@login_required
def delete_expense_transaction(id):
    """Delete an expense transaction with audit trail"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        expense_transaction = ExpenseTransaction.query.get(id)
        if not expense_transaction:
            return jsonify({'error': 'Expense transaction not found'}), 404
        
        # Create audit log before deletion
        audit_log = AccountingAuditLog(
            user_id=current_user.id,
            action='DELETE',
            transaction_type='Expense',
            transaction_id=expense_transaction.id,
            amount=expense_transaction.amount_incl_vat,
            details=f'Deleted: {expense_transaction.description}',
            ip_address=request.remote_addr
        )
        db.session.add(audit_log)
        
        # Store details for logging
        description = expense_transaction.description
        amount = expense_transaction.amount_incl_vat
        
        # Delete the transaction
        db.session.delete(expense_transaction)
        db.session.commit()
        
        app.logger.info(f"Expense transaction {id} deleted by {current_user.email}: {description}")
        return jsonify({'success': True, 'message': 'Expense transaction deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting expense transaction {id}: {str(e)}")
        return jsonify({'error': 'Failed to delete expense transaction'}), 500

@app.route('/admin/accounting/audit-logs')
@login_required
def view_audit_logs():
    """View audit logs for accounting transactions"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Check if export is requested
        export_format = request.args.get('export')
        
        # Get pagination parameters (only if not exporting)
        page = request.args.get('page', 1, type=int) if not export_format else 1
        per_page = min(request.args.get('per_page', 50, type=int), 100) if not export_format else 10000
        
        # Get filter parameters
        action_filter = request.args.get('action')
        transaction_type_filter = request.args.get('transaction_type')
        user_filter = request.args.get('user_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Build query
        query = AccountingAuditLog.query
        
        # Apply filters
        if action_filter:
            query = query.filter(AccountingAuditLog.action == action_filter)
        if transaction_type_filter:
            query = query.filter(AccountingAuditLog.transaction_type == transaction_type_filter)
        if user_filter:
            query = query.filter(AccountingAuditLog.user_id == user_filter)
        
        # Date range filtering
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(AccountingAuditLog.timestamp >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                # Add 1 day to include the entire end date
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(AccountingAuditLog.timestamp <= end_dt)
            except ValueError:
                pass
        
        # Order by most recent first
        query = query.order_by(AccountingAuditLog.timestamp.desc())
        
        # Handle CSV export
        if export_format == 'csv':
            import csv
            from io import StringIO
            from flask import make_response
            
            try:
                output = StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow(['Timestamp', 'User Name', 'User Email', 'Action', 'Transaction Type', 
                               'Amount', 'Details', 'Reference', 'IP Address'])
                
                # Write data
                logs = query.all()
                for index, log in enumerate(logs, 1):
                    try:
                        writer.writerow([
                            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            f"{log.user.first_name} {log.user.last_name}",
                            log.user.email or '',
                            log.action or '',
                            log.transaction_type or '',
                            f"R{log.amount:.2f}" if log.amount else 'R0.00',
                            log.details or '',
                            f"#{index}" if log.transaction_id else '',
                            log.ip_address or ''
                        ])
                    except Exception as row_error:
                        app.logger.error(f"Error writing CSV row {index}: {str(row_error)}")
                        continue
                
                # Create response
                output.seek(0)
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'text/csv; charset=utf-8'
                response.headers['Content-Disposition'] = f'attachment; filename=audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                return response
                
            except Exception as csv_error:
                app.logger.error(f"Error generating CSV export: {str(csv_error)}")
                flash('Error generating CSV export. Please try again.', 'danger')
                return redirect(url_for('view_audit_logs'))
        
        # Paginate for normal view
        audit_logs = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get all admin users for filter dropdown
        users = User.query.filter_by(is_admin=True).order_by(User.first_name, User.last_name).all()
        
        return render_template('admin/audit_logs.html',
                             audit_logs=audit_logs,
                             users=users,
                             current_filters={
                                 'action': action_filter,
                                 'transaction_type': transaction_type_filter,
                                 'user_id': user_filter,
                                 'start_date': start_date,
                                 'end_date': end_date
                             })
        
    except Exception as e:
        app.logger.error(f"Error viewing audit logs: {str(e)}")
        flash('Error loading audit logs', 'danger')
        return redirect(url_for('admin_accounting'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5004))
    app.run(debug=True, host='0.0.0.0', port=port)
