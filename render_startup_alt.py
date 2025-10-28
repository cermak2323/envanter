#!/usr/bin/env python3
"""
Render.com Startup Script - Launches Gunicorn with render_wsgi
"""
import os
import sys
import subprocess

# Environment
os.environ.setdefault('RENDER', 'true')
os.environ.setdefault('FLASK_ENV', 'production')

port = os.environ.get('PORT', '10000')

# Build Gunicorn command
cmd = [
    sys.executable, '-m', 'gunicorn',
    '--worker-class', 'eventlet',
    '-w', '1',
    '--bind', f'0.0.0.0:{port}',
    '--timeout', '30',
    '--access-logfile', '-',
    '--error-logfile', '-',
    'render_wsgi:app'
]

print(f"🚀 Starting Gunicorn: {' '.join(cmd)}")

# Execute Gunicorn (replaces this process)
os.execvp(cmd[0], cmd)


