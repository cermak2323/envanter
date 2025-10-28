#!/usr/bin/env python3
"""
Render.com Startup - With Runtime Dependency Check
"""
import os
import sys
import subprocess

# Environment
os.environ.setdefault('RENDER', 'true')
os.environ.setdefault('FLASK_ENV', 'production')

# Create directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Verify Flask is available, install if not
try:
    import flask
except ImportError:
    print("⚠️ Flask not found, installing...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'], check=True)

# Now import app
from app import app, socketio

port = int(os.environ.get('PORT', 10000))

print(f"🚀 Starting app on 0.0.0.0:{port}")

# Run with SocketIO (production-ready)
socketio.run(
    app,
    host='0.0.0.0',
    port=port,
    debug=False,
    use_reloader=False,
    allow_unsafe_werkzeug=True
)



