#!/usr/bin/env python3
"""
Render.com Startup - Simple & Reliable
"""
import os
import sys

print("🚀 EnvanterQR RENDER.COM STARTUP")
print(f"🐍 Python: {sys.version}")
print(f"📁 Working dir: {os.getcwd()}")
print(f"🌐 PORT: {os.environ.get('PORT', '10000')}")

# Force production environment
os.environ['RENDER'] = 'true'
os.environ['FLASK_ENV'] = 'production'

# Create directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Check critical environment variables
required_vars = ['DATABASE_URL', 'SESSION_SECRET']
missing_vars = []
for var in required_vars:
    if not os.environ.get(var):
        missing_vars.append(var)

if missing_vars:
    print(f"❌ CRITICAL: Missing environment variables: {missing_vars}")
    print("   Please set these in Render Dashboard → Environment tab")
    sys.exit(1)

print("✅ Environment variables check passed")

try:
    print("🔄 Importing application...")
    from app import app, socketio
    print("✅ Application loaded successfully")
    
    # Run with proper Render configuration
    port = int(os.environ.get('PORT', 10000))
    print(f"\n🚀 Starting server on 0.0.0.0:{port}")
    
    # Use gunicorn-compatible run for production
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=port, 
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
        cors_allowed_origins="*"
    )
    
except Exception as e:
    print(f"❌ FATAL STARTUP ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)