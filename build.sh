#!/bin/bash

# Vercel build script for Brand Cartel Flask app
echo "🔨 Starting Vercel build process..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p static/uploads/products
mkdir -p static/uploads/tax_documents
mkdir -p static/invoices

# Set permissions
echo "🔐 Setting permissions..."
chmod 755 static/uploads/products
chmod 755 static/uploads/tax_documents
chmod 755 static/invoices

echo "✅ Build process completed successfully!"