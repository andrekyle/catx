#!/bin/bash

echo "🚀 Starting Brand Cartel Flask Server..."
echo "📂 Working directory: $(pwd)"
echo "🐍 Python version: $(python3 --version)"

cd /Users/michalsnell/Desktop/shopit-main

echo "✅ Database migration messages:"
python3 -c "from app import app; print('Flask app loaded successfully')" 2>&1

echo ""
echo "🌐 Starting server on port 5004..."
echo "📱 Access vendor signup at: http://localhost:5004/vendor/signup"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

python3 app.py
