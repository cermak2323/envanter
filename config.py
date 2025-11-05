"""
Optional local configuration for EnvanterQR.

This file is intended to mirror the settings you sent from your other system.
Drop this file into the project root on the server (or keep it in your repo for local/dev use).
Production secrets should still be provided via environment variables (Render env vars).
"""
import os
import pathlib

# Performance Optimizations
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_timeout': 20,
    'max_overflow': 10,
    'echo': False  # Production'da False olmalı
}

# Response compression
COMPRESS_MIMETYPES = [
    'text/html', 'text/css', 'text/xml', 'application/json',
    'application/javascript', 'text/javascript'
]
COMPRESS_LEVEL = 6
COMPRESS_MIN_SIZE = 500

# Base URL ayarı (production için gerçek domain adresini kullan)
BASE_URL = os.environ.get('BASE_URL', 'https://cermakservis.onrender.com')

# Proje kök dizini
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Database selection logic (this mirrors your other system's approach)
# Use RENDER_INTERNAL_DATABASE_URL when running on Render, otherwise DATABASE_URL or SUPABASE_DATABASE_URL
RENDER_INTERNAL_DATABASE_URL = os.environ.get('RENDER_INTERNAL_DATABASE_URL')
SUPABASE_DATABASE_URL = os.environ.get('SUPABASE_DATABASE_URL')
DATABASE_URL = os.environ.get('DATABASE_URL')

# File upload paths
if os.environ.get('RENDER'):
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    DOCUMENTS_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'documents')
    PHOTOS_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'photos')
    QR_CODES_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'qr_codes')
    QR_CODE_FOLDER = os.path.join(BASE_DIR, 'static', 'qrcodes')
else:
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    DOCUMENTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'documents')
    PHOTOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'photos')
    QR_CODES_FOLDER = os.path.join(UPLOAD_FOLDER, 'qr_codes')
    QR_CODE_FOLDER = os.path.join('static', 'qrcodes')

# Optionally create folders when running locally
if not os.environ.get('RENDER'):
    for folder in [UPLOAD_FOLDER, DOCUMENTS_FOLDER, PHOTOS_FOLDER, QR_CODES_FOLDER, QR_CODE_FOLDER]:
        try:
            pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
