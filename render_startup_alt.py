#!/usr/bin/env python3
"""
Gunicorn WSGI app for Render.com
"""
import os
import sys

# Add current dir to path
sys.path.insert(0, os.getcwd())

# Setup environment
os.environ['RENDER'] = 'true'
os.environ['FLASK_ENV'] = 'production'

# Create directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('reports', exist_ok=True)

print(f"Python: {sys.version}")
print(f"CWD: {os.getcwd()}")
print(f"sys.path: {sys.path[:3]}")

# Import and configure app
try:
    from app import app, socketio
    print("✅ App imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    raise

# For Gunicorn
if __name__ != "__main__":
    # This runs when Gunicorn imports the module
    print("✅ Gunicorn WSGI app loaded")
else:
    # Direct execution
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)