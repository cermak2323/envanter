#!/usr/bin/env python3
"""
Ultra-simple startup script for Render.com - Direct Flask Run
"""
import os
import sys

# Force production environment
os.environ['RENDER'] = 'true'
os.environ['FLASK_ENV'] = 'production'

# Get port
port = int(os.environ.get('PORT', 10000))

print(f"🚀 EnvanterQR Direct Flask Startup")
print(f"🐍 Python: {sys.version}")
print(f"🌐 Port: {port}")
print(f"� Working directory: {os.getcwd()}")

# Create required directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Test imports
try:
    import flask
    print(f"✅ Flask: {flask.__version__}")
except ImportError as e:
    print(f"❌ Flask import failed: {e}")
    sys.exit(1)

try:
    import psycopg2
    print("✅ PostgreSQL driver available")
except ImportError as e:
    print(f"❌ PostgreSQL driver failed: {e}")
    sys.exit(1)

# Import and run app
try:
    print("🔄 Importing application...")
    from app import app, socketio
    print("✅ Application imported successfully")
    
    print(f"🚀 Starting SocketIO server on 0.0.0.0:{port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
    
except Exception as e:
    print(f"❌ Failed to start application: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)