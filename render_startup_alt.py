#!/usr/bin/env python3
"""
Render.com Startup - Direct SocketIO
No Gunicorn dependency
"""
import os
import sys

# Environment
os.environ.setdefault('RENDER', 'true')
os.environ.setdefault('FLASK_ENV', 'production')

# Create directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Import app
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



