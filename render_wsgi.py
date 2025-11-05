"""
WSGI Application Wrapper for Render.com
This module is loaded by Gunicorn as: gunicorn render_wsgi:app
"""
import os
import sys

# Ensure imports work
sys.path.insert(0, os.getcwd())

# Environment setup
os.environ.setdefault('RENDER', 'true')
os.environ.setdefault('FLASK_ENV', 'production')

# Create directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Import and expose app
from app import app

# For Gunicorn WSGI
__all__ = ['app']
