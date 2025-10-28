#!/usr/bin/env python3
"""
Gunicorn WSGI app for Render.com
"""
import os
import sys

# Setup environment
os.environ['RENDER'] = 'true'
os.environ['FLASK_ENV'] = 'production'

# Create directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Import and configure app
from app import app, socketio

# For Gunicorn
if __name__ != "__main__":
    # This runs when Gunicorn imports the module
    print("✅ Gunicorn WSGI app loaded")
else:
    # Direct execution
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)