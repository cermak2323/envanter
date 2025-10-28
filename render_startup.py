#!/usr/bin/env python3
"""
Render.com Startup - VENV Detection & Force Import
"""
import os
import sys
import site

# Force include site-packages from potential venv locations
venv_paths = [
    '/opt/render/project/src/.venv/lib/python3.11/site-packages',
    '/opt/render/project/src/venv/lib/python3.11/site-packages',
    '/opt/render/.venv/lib/python3.11/site-packages',
    '/usr/local/lib/python3.11/dist-packages',
]

for venv_path in venv_paths:
    if os.path.exists(venv_path):
        print(f"✅ Found venv: {venv_path}")
        sys.path.insert(0, venv_path)
        site.addsitedir(venv_path)
        break

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

print(f"\n📚 sys.path:")
for p in sys.path[:5]:
    print(f"  - {p}")

# Try imports
try:
    print("\n🔄 Importing Flask...")
    import flask
    print(f"✅ Flask {flask.__version__}")
    
    import psycopg2
    print("✅ PostgreSQL driver")
    
    import gunicorn
    print("✅ Gunicorn")
    
    print("\n✅ All dependencies available!")
    
    # Import app
    print("🔄 Importing application...")
    from app import app, socketio
    print("✅ Application loaded")
    
    # Run
    port = int(os.environ.get('PORT', 10000))
    print(f"\n🚀 Starting SocketIO on 0.0.0.0:{port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    
    # Last resort - try pip install
    print("\n🔄 Attempting pip install...")
    import subprocess
    
    packages = ['flask', 'psycopg2-binary', 'gunicorn', 'eventlet', 'flask-socketio']
    for pkg in packages:
        try:
            print(f"  📦 Installing {pkg}...")
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', pkg],
                                  capture_output=True, timeout=60)
            if result.returncode == 0:
                print(f"    ✅ {pkg} installed")
        except:
            print(f"    ❌ {pkg} failed")
    
    # Try again
    try:
        from app import app, socketio
        port = int(os.environ.get('PORT', 10000))
        socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
    except Exception as e2:
        print(f"❌ Fatal error: {e2}")
        sys.exit(1)