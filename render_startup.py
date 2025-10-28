#!/usr/bin/env python3
"""
Render.com Startup - Simple & Reliable with Dependency Check
"""
import os
import sys
import subprocess

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

# Check if Flask is available, if not install requirements
try:
    import flask
    print(f"✅ Flask {flask.__version__} available")
except ImportError:
    print("❌ Flask not found, installing requirements...")
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], check=True, capture_output=True, text=True, timeout=300)
        print("✅ Requirements installed successfully")
        
        # Test import again
        import flask
        print(f"✅ Flask {flask.__version__} now available")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during installation: {e}")
        sys.exit(1)

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