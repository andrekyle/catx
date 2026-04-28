#!/usr/bin/env python3
"""
Database migration and initialization script for Nile PostgreSQL database
This script ensures all tables exist and creates sample data if needed.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Category, Product, Order, OrderItem, CartItem, Settings, Vendor, VendorDocument, Driver, DriverDocument
from datetime import datetime
import uuid

def init_nile_database():
    """Initialize the Nile database with tables and sample data"""
    
    with app.app_context():
        try:
            print("🔄 Connecting to Nile database...")
            
            # Test database connection
            db.engine.connect()
            print("✅ Successfully connected to Nile database")
            
            # Create all tables
            print("🔄 Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Check if we need to create sample data
            if User.query.count() == 0:
                print("🔄 No users found, creating sample data...")
                create_sample_data()
            else:
                print("✅ Sample data already exists")
                
            print("🎉 Database initialization completed successfully!")
            
        except Exception as e:
            print(f"❌ Database initialization failed: {str(e)}")
            raise

def create_sample_data():
    """Create sample data for the application"""
    
    # Create admin user
    admin = User(
        username='admin',
        email='admin@brandcartel.com',
        is_admin=True
    )
    admin.set_password('admin123')
    db.session.add(admin)
    
    # Create regular user
    user = User(
        username='John Doe',
        email='john@example.com',
        is_admin=False
    )
    user.set_password('password123')
    db.session.add(user)
    
    # Create categories
    categories = [
        {'name': 'Electronics', 'description': 'Electronic gadgets and devices'},
        {'name': 'Clothing', 'description': 'Fashion and apparel'},
        {'name': 'Home & Garden', 'description': 'Home improvement and garden supplies'},
        {'name': 'Sports', 'description': 'Sports equipment and accessories'},
        {'name': 'Toys', 'description': 'Toys and games for all ages'}
    ]
    
    category_objects = []
    for cat_data in categories:
        category = Category(**cat_data)
        db.session.add(category)
        category_objects.append(category)
    
    # Flush to get category IDs
    db.session.flush()
    
    # Create products
    products = [
        {'name': 'Smartphone', 'description': 'Latest smartphone model', 'price': 599.99, 'stock': 10, 'category_id': category_objects[0].id, 'featured': True},
        {'name': 'Laptop', 'description': 'High-performance laptop', 'price': 1299.99, 'stock': 5, 'category_id': category_objects[0].id, 'featured': True},
        {'name': 'T-Shirt', 'description': 'Cotton t-shirt', 'price': 29.99, 'stock': 50, 'category_id': category_objects[1].id, 'featured': False},
        {'name': 'Jeans', 'description': 'Classic blue jeans', 'price': 79.99, 'stock': 30, 'category_id': category_objects[1].id, 'featured': True},
        {'name': 'Garden Tools Set', 'description': 'Complete garden tools set', 'price': 149.99, 'stock': 15, 'category_id': category_objects[2].id, 'featured': False},
        {'name': 'Basketball', 'description': 'Professional basketball', 'price': 49.99, 'stock': 25, 'category_id': category_objects[3].id, 'featured': True},
        {'name': 'Board Game', 'description': 'Family board game', 'price': 39.99, 'stock': 20, 'category_id': category_objects[4].id, 'featured': False}
    ]
    
    for product_data in products:
        product = Product(**product_data)
        product.order_number = product.generate_order_number()
        db.session.add(product)
    
    # Create settings
    settings = Settings(
        store_name='Brand Cartel',
        store_tagline='Your one-stop shop for everything',
        store_email='contact@brandcartel.com',
        store_phone='+1 (555) 123-4567'
    )
    db.session.add(settings)
    
    # Commit all changes
    db.session.commit()
    print("✅ Sample data created successfully")

if __name__ == '__main__':
    init_nile_database()
