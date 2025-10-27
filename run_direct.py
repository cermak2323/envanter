#!/usr/bin/env python3
"""
Ultra-simple startup script for Render.com
"""
import os
import sys

# Set environment
os.environ.setdefault('FLASK_ENV', 'production')
port = int(os.environ.get('PORT', 10000))

print(f"🚀 Starting EnvanterQR on port {port}")
print(f"🐍 Python: {sys.version}")

# Import and run Flask app directly
try:
    from app import app
    print("✅ App imported successfully")
    app.run(host='0.0.0.0', port=port, debug=False)
except Exception as e:
    print(f"❌ Failed to start: {e}")
    sys.exit(1)