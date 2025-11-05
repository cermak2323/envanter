from flask import Flask, render_template, request, jsonify, send_file, session, redirect
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from functools import wraps, lru_cache
import time
from collections import defaultdict
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import sqlite3
import pandas as pd
import qrcode
from io import BytesIO
import base64
import os
import uuid
from datetime import datetime, timedelta
import zipfile
import re
import hashlib
import secrets
import random
import string
from dotenv import load_dotenv

# Environment-aware imports
try:
    if os.environ.get('RENDER'):  # Sadece production'da B2 import et
        from b2_storage import get_b2_service
        print("☁️ B2 Storage module imported (PRODUCTION)")
    else:
        print("🏠 B2 Storage skipped (LOCAL DEVELOPMENT)")
        get_b2_service = None
except ImportError:
    print("⚠️ B2 Storage module not available")
    get_b2_service = None

import logging
import threading
import json

# Load environment variables
load_dotenv()

# SQLAlchemy ve Models - Veritabanı ORM
from models import db, PartCode, QRCode, CountSession, ScannedQR, User, CountPassword
from db_config import DevelopmentConfig, ProductionConfig

# Logging Configuration
from logging.handlers import RotatingFileHandler
import os

# Log klasörü oluştur
os.makedirs('logs', exist_ok=True)

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('logs/app.log', maxBytes=10*1024*1024, backupCount=5),  # 10MB, 5 backup
        RotatingFileHandler('logs/security.log', maxBytes=5*1024*1024, backupCount=3),  # Security events
        logging.StreamHandler()
    ]
)

# Security logger
security_logger = logging.getLogger('security')
security_handler = RotatingFileHandler('logs/security.log', maxBytes=5*1024*1024, backupCount=3)
security_handler.setFormatter(logging.Formatter('%(asctime)s - SECURITY - %(levelname)s - %(message)s'))
security_logger.addHandler(security_handler)
security_logger.setLevel(logging.WARNING)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Ortama göre dual-mode sistem seç
IS_PRODUCTION = bool(os.environ.get('RENDER'))
IS_LOCAL = not IS_PRODUCTION

print(f"\n🔧 DUAL-MODE SİSTEM")
print(f"📍 Production (Render): {IS_PRODUCTION}")
print(f"🏠 Local (Development): {IS_LOCAL}")

if IS_PRODUCTION:
    # PRODUCTION: PostgreSQL + B2 Storage (KALICI)
    print("☁️ Production Mode: PostgreSQL + B2 Storage (KALICI)")
    USE_B2_STORAGE = True
    USE_POSTGRESQL = True

    # db_config.py kullan
    app.config.from_object(ProductionConfig)

    # Environment variable kontrolü
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("⚠️  WARNING: DATABASE_URL not found in environment!")
        print("🔧 Please set DATABASE_URL in Render Dashboard")
        print("📖 See RENDER_ENV_SETUP.md for instructions")

else:
    # LOCAL Mode - B2'yi enable edebiliriz environment variable ile
    FORCE_B2_LOCAL = os.environ.get('FORCE_B2_LOCAL', 'false').lower() == 'true'

    if FORCE_B2_LOCAL:
        print("🏠 Local Mode: SQLite + B2 Storage (DENEME) - FORCED B2")
        USE_B2_STORAGE = True
    else:
        print("🏠 Local Mode: SQLite + Local Storage (GEÇİCİ)")
        USE_B2_STORAGE = False

    USE_POSTGRESQL = False

    # db_config.py kullan
    app.config.from_object(DevelopmentConfig)

# Database setup

print(f"💾 Database: {'PostgreSQL' if USE_POSTGRESQL else 'SQLite'}")
print(f"📁 Storage: {'B2 Cloud' if USE_B2_STORAGE else 'Local Files'}")
print(f"🔄 Data: {'KALICI' if IS_PRODUCTION else 'GEÇİCİ'}")

# B2 durumu bilgisi
if USE_B2_STORAGE:
    print("\n" + "="*60)
    print("☁️  B2 CLOUD STORAGE ENABLED")
    print("="*60)
    print("📌 QR kodları B2'ye kaydedilecek (KALICI)")
    print("📌 Yeni QR'lar oluşturulduğunda otomatik yüklenir")
    print("📌 Download işlemlerinde B2'den indirilir")
    print("📌 Setup: B2_INTEGRATION_GUIDE.md dosyasını okuyun")
    print("="*60)
else:
    print("\n" + "="*60)
    print("💾 LOCAL STORAGE MODE")
    print("="*60)
    print("📌 QR kodları lokal depolama'ya kaydedilecek (GEÇİCİ)")
    print("📌 B2 enable etmek için: FORCE_B2_LOCAL=true")
    print("📌 Setup: B2_INTEGRATION_GUIDE.md dosyasını okuyun")
    print("="*60)

print()

# SQLAlchemy'yi app'e bağla
db.init_app(app)

# Static dosya sıkıştırma için
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 yıl cache

# SocketIO - Render.com compatible configuration
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1000000  # Changed from 1e6 to integer value
)

# ======================
# MOBIL PERFORMANS OPTIMIZASYONLARI
# ======================

@app.before_request
def mobile_optimizations():
    """Mobil cihazlar için performans optimizasyonları"""
    # Mobil user agent kontrolü
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(device in user_agent for device in [
        'mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone'
    ])

    # Mobil ise cache header'ları optimize et
    if is_mobile:
        pass  # Removed invalid assignment to request.is_mobile

@app.after_request
def add_performance_headers(response):
    """Performans için header'lar ekle"""
    # Static dosyalar için cache
    if request.endpoint == 'static':
        response.cache_control.max_age = 31536000  # 1 yıl
        response.cache_control.public = True

    # Diğer dosyalar için
    else:
        response.cache_control.no_cache = True
        response.cache_control.must_revalidate = True

    # Sıkıştırma header'ı
    if response.status_code == 200 and response.content_length and response.content_length > 1024:
        response.headers['Vary'] = 'Accept-Encoding'

    return response

# ======================
# PERFORMANS CACHE SISTEMI
# ======================

# Bellek tabanlı cache (production'da Redis kullanılmalı)
cache_store = {}
cache_lock = threading.Lock()
CACHE_TTL = 300  # 5 dakika cache süresi

def cache_get(key):
    """Cache'den veri al"""
    with cache_lock:
        if key in cache_store:
            data, timestamp = cache_store[key]
            if time.time() - timestamp < CACHE_TTL:
                return data
            else:
                del cache_store[key]
    return None

def cache_set(key, value):
    """Cache'e veri kaydet"""
    with cache_lock:
        cache_store[key] = (value, time.time())

def cache_delete(key):
    """Cache'den veri sil"""
    with cache_lock:
        if key in cache_store:
            del cache_store[key]

def cache_clear():
    """Tüm cache'i temizle"""
    with cache_lock:
        cache_store.clear()

# Cache temizleme thread'i
def cache_cleanup():
    """Eski cache verilerini temizle"""
    while True:
        time.sleep(60)  # Her dakika kontrol et
        current_time = time.time()
        with cache_lock:
            expired_keys = [
                key for key, (_, timestamp) in cache_store.items()
                if current_time - timestamp > CACHE_TTL
            ]
            for key in expired_keys:
                del cache_store[key]

# Cache temizleme thread'ini başlat
cleanup_thread = threading.Thread(target=cache_cleanup, daemon=True)
cleanup_thread.start()

# Rate limiting için IP tabanlı takip
login_attempts = defaultdict(list)

def add_security_headers(response):
    """Güvenlik header'larını ekle"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.socket.io https://unpkg.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; img-src 'self' data:;"
    return response

@app.after_request
def security_headers(response):
    return add_security_headers(response)

def rate_limit_login(f):
    """Login denemelerini sınırla"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', '127.0.0.1'))
        current_time = time.time()

        # Son 15 dakikadaki denemeleri filtrele
        login_attempts[client_ip] = [t for t in login_attempts[client_ip] if current_time - t < 900]

        # 15 dakikada 5'ten fazla deneme varsa engelle
        if len(login_attempts[client_ip]) >= 5:
            return jsonify({'error': 'Çok fazla login denemesi. 15 dakika bekleyin.'}), 429

        # Denemeyi kaydet
        login_attempts[client_ip].append(current_time)

        return f(*args, **kwargs)
    return decorated_function

# ----------------------
# Configuration / Performance options
# ----------------------

# SQLAlchemy style engine options (used if you adapt parts of the app to SQLAlchemy)
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_timeout': 20,
    'max_overflow': 10,
    'echo': False
}

# Response compression defaults (used if you integrate Flask-Compress)
COMPRESS_MIMETYPES = [
    'text/html', 'text/css', 'text/xml', 'application/json',
    'application/javascript', 'text/javascript'
]
COMPRESS_LEVEL = 6
COMPRESS_MIN_SIZE = 500

# Base URL for the app (production override via env)
BASE_URL = os.environ.get('BASE_URL', 'https://cermakservis.onrender.com')

# Project root
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Database connection selection
# Prefer internal Render DB when running on Render (set RENDER env var),
# then SUPABASE_DATABASE_URL, then DATABASE_URL, then fallback to local sqlite.
_raw_db_url = None
if os.environ.get('RENDER'):
    _raw_db_url = os.environ.get('RENDER_INTERNAL_DATABASE_URL') or os.environ.get('DATABASE_URL')
if not _raw_db_url:
    _raw_db_url = os.environ.get('SUPABASE_DATABASE_URL') or os.environ.get('DATABASE_URL')

# Normalize postgres scheme to explicit SQLAlchemy+psycopg driver when possible
_db_url = None
if _raw_db_url and (_raw_db_url.startswith('postgres://') or _raw_db_url.startswith('postgresql://')):
    if not _raw_db_url.startswith('postgresql+psycopg://'):
        if _raw_db_url.startswith('postgres://'):
            _db_url = _raw_db_url.replace('postgres://', 'postgresql+psycopg://', 1)
        else:
            _db_url = _raw_db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    else:
        _db_url = _raw_db_url
else:
    _db_url = _raw_db_url


# DUAL-MODE DATABASE CONFIGURATION
if USE_POSTGRESQL:
    # PRODUCTION: PostgreSQL (KALICI)
    DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('RENDER_INTERNAL_DATABASE_URL') or \
        "postgresql://cermak_envanter_user:N22HyFcRf3bvgMzkK1J5yNYgrXEfIgNC@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter?sslmode=require"
    print(f"☁️ Production PostgreSQL: {DATABASE_URL[:50]}...")
else:
    # LOCAL: SQLite (GEÇİCİ)
    DATABASE_URL = app.config['SQLALCHEMY_DATABASE_URI']
    print(f"🏠 Local SQLite: {DATABASE_URL}")

print(f"💾 Active Database URL: {DATABASE_URL[:100]}...")

# Connection Pool (PostgreSQL için)
db_pool = None

# Skip old config loading for dual-mode system

def validate_dsn(dsn):
    """Validate the DSN string and ensure the port is an integer."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(dsn)
        if parsed.port is None or not isinstance(parsed.port, int):
            raise ValueError(f"Invalid port in DSN: {parsed.port}")
        return True
    except Exception as e:
        logging.error(f"DSN validation failed: {e}")
        return False

def init_db_pool():
    """Initialize database connection pool (PostgreSQL only)"""
    global db_pool

    if not USE_POSTGRESQL:
        print("🏠 Local SQLite mode - No connection pool needed")
        return

    # PRODUCTION: PostgreSQL connection pool
    try:
        # Debug: show which DSN we will use (mask password)
        try:
            _masked = DATABASE_URL
            if _masked and '//' in _masked:
                parts = _masked.split('//', 1)
                creds_and_host = parts[1]
                if '@' in creds_and_host:
                    cred, rest = creds_and_host.split('@', 1)
                    if ':' in cred:
                        user, pwd = cred.split(':', 1)
                        cred = f"{user}:<hidden>"
                    _masked = parts[0] + '//' + cred + '@' + rest
        except Exception:
            _masked = '<unavailable>'
        print(f"☁️ Initializing PostgreSQL pool: {_masked}")

        # Validate DSN before proceeding
        if not validate_dsn(DATABASE_URL):
            raise ValueError("Invalid DATABASE_URL. Check the DSN format and port.")

        # Production PostgreSQL pool ayarları
        db_pool = SimpleConnectionPool(
            minconn=2,  # Minimum bağlantı sayısı
            maxconn=15, # Maximum bağlantı sayısı
            dsn=DATABASE_URL
        )
        print("✅ PostgreSQL connection pool initialized successfully")
        print("📊 Pool settings: minconn=2, maxconn=15")
    except Exception as e:
        import traceback
        print(f"❌ Failed to initialize PostgreSQL pool: {e}")
        traceback.print_exc()
        raise

# Initialize connection pool
init_db_pool()
REPORTS_DIR = 'reports'

def generate_strong_password():
    """Güçlü parola oluştur (8 karakter: büyük harf, küçük harf, rakam, özel karakter)"""
    characters = string.ascii_uppercase + string.ascii_lowercase + string.digits + "!@#$%^&*"
    # En az 1 büyük harf, 1 küçük harf, 1 rakam, 1 özel karakter olacak şekilde
    password = [
        random.choice(string.ascii_uppercase),  # Büyük harf
        random.choice(string.ascii_lowercase),  # Küçük harf
        random.choice(string.digits),           # Rakam
        random.choice("!@#$%^&*")              # Özel karakter
    ]
    # Kalan 4 karakteri rastgele seç
    for _ in range(4):
        password.append(random.choice(characters))

    # Karıştır
    random.shuffle(password)
    return ''.join(password)

def generate_count_password():
    """Sayım için parola oluştur (6 haneli sadece sayı) - Basit ve hızlı giriş için"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

# Admin sayım şifresi
ADMIN_COUNT_PASSWORD = "@R9t$L7e!xP2w"
print(f"DEBUG: ADMIN_COUNT_PASSWORD = '{ADMIN_COUNT_PASSWORD}'")  # DEBUG

os.makedirs(REPORTS_DIR, exist_ok=True)

def get_db_placeholder():
    """Database'e göre doğru placeholder döndür (%s for PostgreSQL, ? for SQLite)"""
    return '?' if not USE_POSTGRESQL else '%s'

def execute_query(cursor, query, params=None):
    """
    Execute SQL query with correct placeholder for current database.
    Automatically converts %s to ? for SQLite.
    """
    if not USE_POSTGRESQL:
        # SQLite: %s -> ? dönüştür
        query = query.replace('%s', '?')

    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    return cursor

def get_db():
    """Get database connection - dual mode (PostgreSQL pool vs SQLite direct)"""

    if USE_POSTGRESQL:
        # PRODUCTION: PostgreSQL from pool
        try:
            # Try to get a connection from the pool
            conn = db_pool.getconn()

            # Validate that the connection is open. psycopg2 connection has
            # a .closed attribute (0 means open). If it's closed, discard and get a new one.
            try:
                if getattr(conn, 'closed', 1):
                    # Return the closed connection (ask pool to close it) and get another
                    try:
                        db_pool.putconn(conn, close=True)
                    except Exception:
                        pass
                    conn = db_pool.getconn()

            except Exception:
                # If any validation check fails, attempt to use the connection anyway
                pass

            return conn
        except Exception as e:
            # Try to reinitialize pool once in case connections were dropped server-side
            try:
                logging.warning(f"PostgreSQL pool error, attempting to reinitialize pool: {e}")
                init_db_pool()
                conn = db_pool.getconn()
                return conn
            except Exception as e2:
                logging.error(f"Failed to get PostgreSQL connection after reinit: {e2}")
                raise
    else:
        # LOCAL: SQLite direct connection (GEÇİCİ)
        import sqlite3
        conn = sqlite3.connect(DATABASE_URL.replace('sqlite:///', ''))
        conn.row_factory = sqlite3.Row  # Dict-like access
        return conn

def close_db(conn):
    """Return connection to pool (PostgreSQL) or close (SQLite)"""

    if not conn:
        return

    if USE_POSTGRESQL:
        # PRODUCTION: Return to PostgreSQL pool
        try:
            # Check if connection is valid before returning to pool
            if hasattr(conn, 'closed'):
                if conn.closed == 0:  # Connection is open
                    try:
                        db_pool.putconn(conn)
                    except (TypeError, Exception) as e:
                        # Connection already exists in pool or other issue
                        try:
                            conn.close()
                        except:
                            pass
                else:  # Connection is closed
                    try:
                        db_pool.putconn(conn, close=True)
                    except (TypeError, Exception):
                        pass
            else:
                # Connection object doesn't have 'closed' attribute, try to return anyway
                try:
                    db_pool.putconn(conn)
                except (TypeError, Exception):
                    try:
                        conn.close()
                    except:
                        pass
        except Exception as e:
            logging.debug(f"Error returning PostgreSQL connection to pool: {e}")
            # Silently ignore pool errors to prevent cascading failures
    else:
        # LOCAL: Close SQLite connection
        try:
            if conn:
                conn.close()
        except Exception as e:
            logging.debug(f"Error closing SQLite connection: {e}")

def create_performance_indexes(cursor):
    """Performans için kritik indexleri oluştur"""
    indexes = [
        # QR Codes indexleri
        "CREATE INDEX IF NOT EXISTS idx_qr_codes_qr_id ON qr_codes(qr_id);",
        "CREATE INDEX IF NOT EXISTS idx_qr_codes_part_code ON qr_codes(part_code_id);",
        "CREATE INDEX IF NOT EXISTS idx_qr_codes_is_used ON qr_codes(is_used);",

        # Count Sessions indexleri
        "CREATE INDEX IF NOT EXISTS idx_count_sessions_is_active ON count_sessions(is_active);",
        "CREATE INDEX IF NOT EXISTS idx_count_sessions_created_by ON count_sessions(created_by);",
        "CREATE INDEX IF NOT EXISTS idx_count_sessions_created_at ON count_sessions(created_at);",

        # Scanned QR indexleri
        "CREATE INDEX IF NOT EXISTS idx_scanned_qr_session_id ON scanned_qr(session_id);",
        "CREATE INDEX IF NOT EXISTS idx_scanned_qr_qr_id ON scanned_qr(qr_id);",
        "CREATE INDEX IF NOT EXISTS idx_scanned_qr_scanned_by ON scanned_qr(scanned_by);",
        "CREATE INDEX IF NOT EXISTS idx_scanned_qr_scanned_at ON scanned_qr(scanned_at);",

        # Part Codes indexleri
        "CREATE INDEX IF NOT EXISTS idx_part_codes_part_code ON part_codes(part_code);",

        # Kullanıcı indexleri
        "CREATE INDEX IF NOT EXISTS idx_envanter_users_username ON envanter_users(username);",
        "CREATE INDEX IF NOT EXISTS idx_envanter_users_is_active ON envanter_users(is_active_user);",
    ]

    try:
        for index_sql in indexes:
            execute_query(cursor, index_sql)
        print("✅ Performance indexes created/verified")
    except Exception as e:
        print(f"⚠️ Warning: Could not create some indexes: {e}")

def init_db():
    """Initialize database tables using SQLAlchemy ORM

    Lokal: SQLite tables oluştur
    Production: PostgreSQL tables kontrol et
    """
    try:
        with app.app_context():
            if USE_POSTGRESQL:
                # PRODUCTION: PostgreSQL - SQLAlchemy ile
                print("\n" + "="*70)
                print("🔍 INITIALIZING POSTGRESQL TABLES")
                print("="*70)

                inspector = db.inspect(db.engine)
                existing_tables = inspector.get_table_names()
                print(f"Existing tables: {existing_tables}")

                required_tables = ['envanter_users', 'part_codes', 'qr_codes', 'count_sessions', 'count_passwords', 'scanned_qr']

                missing_tables = [t for t in required_tables if t not in existing_tables]

                if missing_tables:
                    print(f"☁️ Creating missing PostgreSQL tables: {', '.join(missing_tables)}")
                    db.create_all()
                    print("✅ PostgreSQL tables created successfully")
                else:
                    print("✅ All PostgreSQL tables already exist")

                # 🔧 DATABASE MIGRATION: Add finished_by column to count_sessions
                try:
                    conn = get_db()
                    cursor = conn.cursor()

                    # Check if finished_by column exists
                    execute_query(cursor, """
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='count_sessions' AND column_name='finished_by'
                    """)

                    if not cursor.fetchone():
                        print("🔧 Adding finished_by column to count_sessions table...")
                        execute_query(cursor, """
                            ALTER TABLE count_sessions 
                            ADD COLUMN finished_by INTEGER REFERENCES envanter_users(id)
                        """)
                        conn.commit()
                        print("✅ finished_by column added successfully")
                    else:
                        print("✅ finished_by column already exists")

                    close_db(conn)
                except Exception as e:
                    print(f"⚠️ Migration warning: {e}")

                # Verify scanned_qr table specifically (critical for duplicate detection)
                if 'scanned_qr' in existing_tables or 'scanned_qr' not in missing_tables:
                    print("✅ scanned_qr table verified - duplicate detection will work")
                else:
                    print("❌ WARNING: scanned_qr table not found - duplicate detection may fail!")
                    print("   Creating scanned_qr table manually...")
                    try:
                        # Create scanned_qr table manually if SQLAlchemy fails
                        conn = get_db()
                        cursor = conn.cursor()
                        execute_query(cursor, '''
                            CREATE TABLE IF NOT EXISTS scanned_qr (
                                id SERIAL PRIMARY KEY,
                                session_id VARCHAR(255) NOT NULL,
                                qr_id VARCHAR(255) NOT NULL,
                                part_code VARCHAR(255) NOT NULL,
                                scanned_by INTEGER,
                                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        ''')
                        conn.commit()
                        close_db(conn)
                        print("✅ scanned_qr table created successfully")
                    except Exception as e:
                        print(f"❌ Failed to create scanned_qr: {e}")

                # SQLAlchemy User model kullan
                admin_user = User.query.filter_by(username='admin').first()
                if not admin_user:
                    print("➕ Creating default PostgreSQL admin user...")
                    from werkzeug.security import generate_password_hash
                    admin_password = generate_password_hash("@R9t$L7e!xP2w")
                    admin = User(
                        username='admin',
                        full_name='Administrator',
                        password_hash=admin_password,
                        role='admin',
                        is_active_user=True
                    )
                    db.session.add(admin)
                    db.session.commit()
                    print("✅ PostgreSQL admin user created (admin/@R9t$L7e!xP2w)")
                else:
                    print("✅ PostgreSQL admin user already exists")

                print("="*70 + "\n")
                # LOCAL: SQLite - Raw SQL ile (basit tablo yapısı)
                print("🏠 Local SQLite mode - checking simple table structure")

                # SQLite bağlantısı al
                conn = get_db()
                cursor = conn.cursor()

                # SQLite schema'yı güncelle (full_name column ekle)
                try:
                    execute_query(cursor, "ALTER TABLE envanter_users ADD COLUMN full_name VARCHAR(255)")
                    print("✅ Added full_name column to SQLite")
                except sqlite3.OperationalError:
                    # Column zaten varsa veya başka hata
                    pass

                # Admin user var mı kontrol et (SQLite raw SQL)
                execute_query(cursor, "SELECT * FROM envanter_users WHERE username = 'admin'")
                admin_exists = cursor.fetchone()

                if not admin_exists:
                    print("➕ Creating default SQLite admin user...")
                    from werkzeug.security import generate_password_hash
                    admin_password_hash = generate_password_hash("admin123")
                    execute_query(cursor, '''
                        INSERT INTO envanter_users (username, password_hash, full_name, role, created_at, is_active)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', ('admin', admin_password_hash, 'Administrator', 'admin', datetime.now(), True))
                    conn.commit()
                    print("✅ SQLite admin user created (admin/admin123)")
                else:
                    print("✅ SQLite admin user already exists")

                close_db(conn)
                print("✅ SQLite database initialized successfully")

            return True

    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Giriş yapmanız gerekiyor'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Admin şifre kontrolü öncelikli
        if not session.get('admin_authenticated'):
            return redirect('/admin')

        if 'user_id' not in session:
            return jsonify({'error': 'Giriş yapmanız gerekiyor'}), 401
        conn = get_db()
        cursor = conn.cursor()
        placeholder = get_db_placeholder()
        execute_query(cursor, f'SELECT role FROM envanter_users WHERE id = {placeholder}', (session['user_id'],))
        user = cursor.fetchone()
        close_db(conn)
        if not user or user[0] != 'admin':
            return jsonify({'error': 'Bu işlem için yetkiniz yok'}), 403
        return f(*args, **kwargs)
    return decorated_function

def admin_count_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Giriş yapmanız gerekiyor'}), 401
        conn = get_db()
        cursor = conn.cursor()
        execute_query(cursor, 'SELECT role FROM envanter_users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        close_db(conn)
        if not user or user[0] != 'admin':
            return jsonify({'error': 'Bu işlem için yetkiniz yok'}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template('login.html')

    # ✅ SAYIM KONTROLÜ: Aktif sayım varsa kullanıcıları sayım sayfasına yönlendir
    conn = get_db()
    cursor = conn.cursor()
    placeholder = get_db_placeholder()

    try:
        execute_query(cursor, f'SELECT COUNT(*) FROM count_sessions WHERE is_active = {placeholder}', (True,))
        active_session_count = cursor.fetchone()[0]

        # Aktif sayım varsa sayım sayfasına yönlendir
        if active_session_count > 0:
            print(f"DEBUG: Aktif sayım bulundu ({active_session_count}), kullanıcı sayım sayfasına yönlendiriliyor")
            close_db(conn)
            return redirect('/count')

    except Exception as e:
        print(f"DEBUG: Sayım kontrolü hatası: {e}")
    finally:
        close_db(conn)

    # Aktif sayım yoksa normal ana sayfayı göster
    return render_template('index.html')

@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    """Cache'li dashboard istatistikleri"""
    cache_key = 'dashboard_stats'

    # Cache'den kontrol et
    cached_data = cache_get(cache_key)
    if cached_data:
        return jsonify(cached_data)

    # Cache yoksa veritabanından al
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Toplam QR kod sayısı
        # execute_query(cursor, 'SELECT COUNT(*) FROM envanter')
        total_qr_codes = cursor.fetchone()[0]

        # Toplam sayım sayısı
        execute_query(cursor, 'SELECT COUNT(*) FROM scanned_qr')
        total_scans = cursor.fetchone()[0]

        # Aktif oturum sayısı
        execute_query(cursor, 'SELECT COUNT(*) FROM count_sessions WHERE is_active = %s', (True,))
        active_sessions = cursor.fetchone()[0]

        # Son sayım tarihi
        execute_query(cursor, 'SELECT MAX(scanned_at) FROM scanned_qr')
        last_scan = cursor.fetchone()[0]

        # Bugünkü sayımlar
        execute_query(cursor, '''
            SELECT COUNT(*) FROM scanned_qr 
            WHERE DATE(scanned_at) = CURRENT_DATE
        ''')
        today_scans = cursor.fetchone()[0]

        # Bu haftaki sayımlar
        execute_query(cursor, '''
            SELECT COUNT(*) FROM scanned_qr 
            WHERE scanned_at >= CURRENT_DATE - INTERVAL '7 days'
        ''')
        week_scans = cursor.fetchone()[0]

        stats = {
            'total_qr_codes': total_qr_codes,
            'total_scans': total_scans,
            'active_sessions': active_sessions,
            'last_scan': last_scan.isoformat() if last_scan else None,
            'today_scans': today_scans,
            'week_scans': week_scans,
            'cache_time': datetime.now().isoformat()
        }

        # Cache'e kaydet
        cache_set(cache_key, stats)

        return jsonify(stats)

    finally:
        close_db(conn)

@app.route('/count')
def count_page():
    # Aktif sayım oturumu kontrolü
    conn = get_db()
    cursor = conn.cursor()
    execute_query(cursor, 'SELECT COUNT(*) FROM count_sessions WHERE is_active = %s', (True,))
    active_session = cursor.fetchone()

    if active_session[0] == 0:
        # Aktif sayım yoksa ana sayfaya yönlendir
        close_db(conn)
        return redirect('/')

    # ADMIN KONTROLÜ - Admin rolündeyse şifre isteme
    if session.get('role') == 'admin':
        print("DEBUG /count: Admin kullanıcı - şifre istenmeden direkt count.html")
        # Admin için otomatik count_access ver
        session['count_access'] = True
        close_db(conn)
        return render_template('count.html')

    # Şifre doğrulaması yapılmışsa count_access session var mı kontrol et
    print(f"DEBUG /count: session.get('count_access') = {session.get('count_access')}")  # DEBUG
    print(f"DEBUG /count: session keys = {list(session.keys())}")  # DEBUG
    if not session.get('count_access'):
        # Şifre alınmamışsa şifre sayfasını göster
        print("DEBUG /count: count_access yok, count_password.html gösteriliyor")  # DEBUG
        close_db(conn)
        return render_template('count_password.html')

    print("DEBUG /count: count_access var, count.html gösteriliyor")  # DEBUG
    close_db(conn)
    return render_template('count.html')

@app.route('/login', methods=['POST'])
@rate_limit_login
def login():
    from werkzeug.security import check_password_hash
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Kullanıcı adı ve şifre gerekli'}), 400

    conn = get_db()
    cursor = conn.cursor()
    placeholder = get_db_placeholder()
    try:
        # Dual-mode: SQLite vs PostgreSQL table compatibility
        # Get user data first, then verify password
        if USE_POSTGRESQL:
            # PostgreSQL: Full schema with envanter_users table
            execute_query(cursor, f'SELECT id, username, full_name, role, password_hash FROM envanter_users WHERE username = {placeholder}',
                         (username,))
        else:
            # SQLite: envanter_users table with full_name (after column addition)
            execute_query(cursor, f'SELECT id, username, COALESCE(full_name, username) as full_name, role, password_hash FROM envanter_users WHERE username = {placeholder}',
                         (username,))
    except psycopg2.OperationalError as oe:
        # Connection was closed unexpectedly (e.g., server-side idle timeout / SSL termination).
        logging.warning(f"OperationalError on login query, attempting one retry: {oe}")
        try:
            close_db(conn)
        except Exception:
            pass
        # Attempt to reinitialize pool and retry once
        try:
            init_db_pool()
            conn = get_db()
            cursor = conn.cursor()
            placeholder = get_db_placeholder()
            if USE_POSTGRESQL:
                execute_query(cursor, f'SELECT id, username, full_name, role, password_hash FROM envanter_users WHERE username = {placeholder}',
                             (username,))
            else:
                execute_query(cursor, f'SELECT id, username, COALESCE(full_name, username) as full_name, role, password_hash FROM envanter_users WHERE username = {placeholder}',
                             (username,))
        except Exception as e2:
            logging.exception(f"Failed to execute login query after retry: {e2}")
            try:
                close_db(conn)
            except Exception:
                pass
            return jsonify({'error': 'Database connection error'}), 500

    user = cursor.fetchone()
    close_db(conn)

    if user and check_password_hash(user[4], password):  # user[4] is password_hash
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['full_name'] = user[2]
        session['role'] = user[3]
        return jsonify({'success': True, 'role': user[3]})
    else:
        return jsonify({'error': 'Kullanıcı adı veya şifre hatalı'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/check_auth')
def check_auth():
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'username': session.get('username', None),
            'full_name': session.get('full_name', None),
            'role': session.get('role', None)
        })
    return jsonify({'authenticated': False})

@app.route('/create_test_data', methods=['POST'])
@login_required
def create_test_data():
    """Test verisi oluştur - sadece development için"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Test parçaları ekle
        test_parts = [
            ('TEST-001', 'Test Parça 1', 5),
            ('TEST-002', 'Test Parça 2', 3),
            ('TEST-003', 'Test Parça 3', 2)
        ]

        # Mevcut test verilerini sil
        execute_query(cursor, "DELETE FROM qr_codes WHERE qr_id LIKE 'TEST-%'")
        execute_query(cursor, "DELETE FROM parts WHERE part_code LIKE 'TEST-%'")

        # Test parçalarını ekle
        for part_code, part_name, quantity in test_parts:
            # Part'ı ekle (database uyumlu)
            if USE_POSTGRESQL:
                execute_query(cursor, 'INSERT INTO parts (part_code, part_name, quantity) VALUES (%s, %s, %s) ON CONFLICT (part_code) DO NOTHING',
                             (part_code, part_name, quantity))
            else:
                execute_query(cursor, 'INSERT INTO parts (part_code, part_name, quantity) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
                             (part_code, part_name, quantity))

            # QR kodları oluştur
            for i in range(quantity):
                qr_id = f"{part_code}-{i+1:03d}"
                if USE_POSTGRESQL:
                    execute_query(cursor, 'INSERT INTO qr_codes (qr_id, part_code, part_name) VALUES (%s, %s, %s) ON CONFLICT (qr_id) DO NOTHING',
                                 (qr_id, part_code, part_name))
                else:
                    execute_query(cursor, 'INSERT INTO qr_codes (qr_id, part_code, part_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
                                 (qr_id, part_code, part_name))

        conn.commit()
        close_db(conn)

        return jsonify({
            'success': True,
            'message': 'Test verileri oluşturuldu',
            'test_qr_codes': [f"{part_code}-{i+1:03d}" for part_code, _, quantity in test_parts for i in range(quantity)]
        })

    except Exception as e:
        try:
            conn.rollback()
            close_db(conn)
        except:
            pass
        return jsonify({'error': f'Test verisi oluşturulamadı: {str(e)}'}), 500

@app.route('/debug/qr_codes')
def debug_qr_codes():
    """Debug: Mevcut QR kodlarını listele"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        execute_query(cursor, 'SELECT qr_id, part_code, part_name, is_used FROM qr_codes ORDER BY qr_id LIMIT 20')
        qr_codes = cursor.fetchall()

        close_db(conn)

        result = []
        for row in qr_codes:
            result.append({
                'qr_id': row[0],
                'part_code': row[1], 
                'part_name': row[2],
                'is_used': row[3]
            })

        return jsonify({
            'total_qr_codes': len(result),
            'qr_codes': result
        })

    except Exception as e:
        return jsonify({'error': f'Hata: {str(e)}'}), 500

@app.route('/upload_parts', methods=['POST'])
@login_required
def upload_parts():
    """
    Akıllı QR Kod Ekleme Sistemi:
    - Mevcut QR kodları SİLİNMEZ
    - Excel'deki yeni parçalar için QR oluşturur
    - Eksik olan QR kod sayılarını tamamlar
    - Mevcut parçaların adetini kontrol eder
    """
    conn = get_db()
    cursor = conn.cursor()
    placeholder = get_db_placeholder()
    execute_query(cursor, f'SELECT COUNT(*) as count FROM count_sessions WHERE is_active = {placeholder}', (True,))
    active_session = cursor.fetchone()
    close_db(conn)

    if active_session[0] > 0:
        return jsonify({'error': 'Aktif bir sayım oturumu var. Önce sayımı bitirin.'}), 400

    if 'file' not in request.files:
        return jsonify({'error': 'Dosya bulunamadı'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Dosya seçilmedi'}), 400

    if not (file.filename and file.filename.endswith(('.xlsx', '.xls'))):
        return jsonify({'error': 'Sadece Excel dosyaları yüklenebilir'}), 400

    try:
        df = pd.read_excel(file)

        required_columns = ['part_code', 'part_name', 'quantity']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': 'Excel dosyası "part_code", "part_name" ve "quantity" sütunlarını içermelidir'}), 400

        conn = get_db()
        cursor = conn.cursor()
        placeholder = get_db_placeholder()

        # Admin user'ın ID'sini al (tüm upload işlemi için)
        user_id = session.get('user_id')
        if not user_id:
            # Default olarak admin user'ı al
            execute_query(cursor, f'SELECT id FROM envanter_users WHERE username = {placeholder}', ('admin',))
            admin_user = cursor.fetchone()
            user_id = admin_user[0] if admin_user else 1  # fallback ID

        # Mevcut parçaları ve QR kodları al
        execute_query(cursor, 'SELECT part_code, part_name FROM parts')
        existing_parts = {row[0]: row[1] for row in cursor.fetchall()}

        execute_query(cursor, 'SELECT part_code, COUNT(*) as qr_count FROM qr_codes GROUP BY part_code')
        existing_qr_counts = {row[0]: row[1] for row in cursor.fetchall()}

        new_qr_codes = []
        updated_parts = []
        new_parts = []
        processing_summary = {
            'new_parts': 0,
            'updated_parts': 0, 
            'new_qr_codes': 0,
            'existing_qr_codes': sum(existing_qr_counts.values())
        }

        print(f"\n🔄 AKILLI QR KOD SİSTEMİ")
        print(f"📊 Mevcut QR kod sayısı: {processing_summary['existing_qr_codes']}")
        print(f"📋 Excel'den gelen parça sayısı: {len(df)}")
        print("="*50)

        for _, row in df.iterrows():
            part_code = str(row['part_code'])
            part_name = str(row['part_name'])
            needed_quantity = int(row['quantity'])

            if part_code in existing_parts:
                # MEVCUT PARÇA - Adet kontrolü yap
                current_qr_count = existing_qr_counts.get(part_code, 0)

                if needed_quantity > current_qr_count:
                    # EKSİK QR KODLARI OLUŞTUR
                    missing_count = needed_quantity - current_qr_count
                    print(f"📦 {part_code}: {current_qr_count} mevcut → {needed_quantity} hedef = {missing_count} eksik QR")

                    for i in range(missing_count):
                        qr_id = f"{part_code}-{uuid.uuid4().hex[:8]}"
                        execute_query(cursor, f'INSERT INTO qr_codes (qr_id, part_code, part_name, created_at, created_by, is_used, is_downloaded) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})',
                                     (qr_id, part_code, part_name, datetime.now(), user_id, False, False))
                        new_qr_codes.append(qr_id)

                    # Parça bilgilerini güncelle (quantity değil, sadece isim)
                    execute_query(cursor, f'UPDATE parts SET part_name = {placeholder} WHERE part_code = {placeholder}',
                                 (part_name, part_code))
                    updated_parts.append(part_code)
                    processing_summary['updated_parts'] += 1
                    processing_summary['new_qr_codes'] += missing_count

                elif needed_quantity < current_qr_count:
                    # FAZLA QR KODLARI VAR - Sadece uyarı ver, silme!
                    extra_count = current_qr_count - needed_quantity
                    print(f"⚠️ {part_code}: {current_qr_count} mevcut > {needed_quantity} hedef = {extra_count} fazla QR (SİLİNMEDİ)")

                    # Parça bilgilerini güncelle (quantity yok, sadece isim)
                    execute_query(cursor, f'UPDATE parts SET part_name = {placeholder} WHERE part_code = {placeholder}',
                                 (part_name, part_code))
                    updated_parts.append(part_code)
                    processing_summary['updated_parts'] += 1

                else:
                    # TAM UYGUN - Sadece parça bilgilerini güncelle
                    print(f"✅ {part_code}: {current_qr_count} QR kod zaten uygun")
                    execute_query(cursor, f'UPDATE parts SET part_name = {placeholder} WHERE part_code = {placeholder}',
                                 (part_name, part_code))

            else:
                # YENİ PARÇA - Tamamen yeni QR kodları oluştur
                print(f"🆕 {part_code}: Yeni parça - {needed_quantity} QR kod oluşturuluyor")

                # Admin user'ın ID'sini al
                user_id = session.get('user_id')
                if not user_id:
                    # Default olarak admin user'ı al
                    execute_query(cursor, f'SELECT id FROM envanter_users WHERE username = {placeholder}', ('admin',))
                    admin_user = cursor.fetchone()
                    user_id = admin_user[0] if admin_user else 1  # fallback ID

                execute_query(cursor, f'INSERT INTO parts (part_code, part_name, description, created_at, created_by, is_active) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})',
                             (part_code, part_name, '', datetime.now(), user_id, True))

                for i in range(needed_quantity):
                    qr_id = f"{part_code}-{uuid.uuid4().hex[:8]}"
                    execute_query(cursor, f'INSERT INTO qr_codes (qr_id, part_code, part_name, created_at, created_by, is_used, is_downloaded) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})',
                                 (qr_id, part_code, part_name, datetime.now(), user_id, False, False))
                    new_qr_codes.append(qr_id)

                new_parts.append(part_code)
                processing_summary['new_parts'] += 1
                processing_summary['new_qr_codes'] += needed_quantity

        conn.commit()
        close_db(conn)

        print(f"\n✅ İŞLEM TAMAMLANDI")
        print(f"📈 Yeni parçalar: {processing_summary['new_parts']}")
        print(f"🔄 Güncellenen parçalar: {processing_summary['updated_parts']}")
        print(f"🆕 Yeni QR kodları: {processing_summary['new_qr_codes']}")
        print(f"💾 Toplam QR kodları: {processing_summary['existing_qr_codes'] + processing_summary['new_qr_codes']}")
        print("="*50)

        return jsonify({
            'success': True,
            'message': f'İşlem tamamlandı! {processing_summary["new_qr_codes"]} yeni QR kod oluşturuldu.',
            'summary': {
                'new_parts': processing_summary['new_parts'],
                'updated_parts': processing_summary['updated_parts'], 
                'new_qr_codes': processing_summary['new_qr_codes'],
                'total_qr_codes': processing_summary['existing_qr_codes'] + processing_summary['new_qr_codes'],
                'existing_qr_codes_preserved': processing_summary['existing_qr_codes']
            }
        })

    except Exception as e:
        logging.exception(f"Error in smart QR upload system: {e}")
        try:
            close_db(conn)
        except Exception:
            pass
        return jsonify({'error': f'İşlem sırasında hata oluştu: {str(e)}'}), 500

@app.route('/get_qr_codes')
@login_required
def get_qr_codes():
    search = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 100))
    offset = (page - 1) * limit

    conn = get_db()
    cursor = conn.cursor()

    if search:
        # Önce tam eşleşme ara
        execute_query(cursor, "SELECT qr_id, part_code, part_name, is_used, is_downloaded FROM qr_codes WHERE part_code = %s OR part_name = %s ORDER BY part_code, qr_id LIMIT %s OFFSET %s", (search, search, limit, offset))
        exact_matches = cursor.fetchall()

        if exact_matches:
            qr_codes = []
            for row in exact_matches:
                qr_codes.append({
                    'qr_id': row[0],
                    'part_code': row[1],
                    'part_name': row[2],
                    'is_used': row[3],
                    'is_downloaded': row[4]
                })
        else:
            # Tam eşleşme bulunamazsa kısmi eşleşme ara
            execute_query(cursor, "SELECT qr_id, part_code, part_name, is_used, is_downloaded FROM qr_codes WHERE part_code LIKE %s OR part_name LIKE %s ORDER BY part_code, qr_id LIMIT %s OFFSET %s", (f'%{search}%', f'%{search}%', limit, offset))
            rows = cursor.fetchall()
            qr_codes = []
            for row in rows:
                qr_codes.append({
                    'qr_id': row[0],
                    'part_code': row[1],
                    'part_name': row[2],
                    'is_used': row[3],
                    'is_downloaded': row[4]
                })
    else:
        # Arama terimi yoksa tüm QR kodları getir (sayfalama ile)
        execute_query(cursor, "SELECT qr_id, part_code, part_name, is_used, is_downloaded FROM qr_codes ORDER BY part_code, qr_id LIMIT %s OFFSET %s", (limit, offset))
        rows = cursor.fetchall()
        qr_codes = []
        for row in rows:
            qr_codes.append({
                'qr_id': row[0],
                'part_code': row[1],
                'part_name': row[2],
                'is_used': row[3],
                'is_downloaded': row[4]
            })

    # Toplam sayıyı al
    if search:
        execute_query(cursor, "SELECT COUNT(*) FROM qr_codes WHERE part_code LIKE %s OR part_name LIKE %s", (f'%{search}%', f'%{search}%'))
    else:
        execute_query(cursor, "SELECT COUNT(*) FROM qr_codes")

    total_count = cursor.fetchone()[0]

    close_db(conn)

    return jsonify({
        'qr_codes': qr_codes,
        'total_count': total_count,
        'current_page': page,
        'total_pages': (total_count + limit - 1) // limit,
        'has_more': (page * limit) < total_count
    })

@app.route('/mark_qr_used', methods=['POST'])
@login_required
def mark_qr_used():
    try:
        data = request.json
        qr_id = data.get('qr_id')

        if not qr_id:
            return jsonify({'error': 'QR ID gerekli'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # QR kodunun var olup olmadığını kontrol et
        execute_query(cursor, 'SELECT id, is_used FROM qr_codes WHERE qr_id = %s', (qr_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({'error': 'QR kod bulunamadı'}), 404

        if result[1]:  # is_used
            return jsonify({'error': 'QR kod zaten kullanılmış'}), 400

        # QR kodu kullanıldı olarak işaretle (DB-agnostic)
        execute_query(cursor, 'UPDATE qr_codes SET is_used = %s, used_at = %s WHERE qr_id = %s', (True, datetime.now(), qr_id))
        conn.commit()
        close_db(conn)

        return jsonify({'success': True, 'message': 'QR kod kullanıldı olarak işaretlendi'})

    except Exception as e:
        return jsonify({'error': f'Hata: {str(e)}'}), 500

@app.route('/clear_all_qrs', methods=['POST'])
@login_required
def clear_all_qrs():
    """Tüm QR kodlarını temizle (aktif sayım oturumu yoksa)"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Aktif sayım oturumu kontrolü
        execute_query(cursor, 'SELECT COUNT(*) FROM count_sessions WHERE is_active = %s', (True,))
        active_session = cursor.fetchone()[0]

        if active_session > 0:
            close_db(conn)
            return jsonify({'error': 'Aktif bir sayım oturumu var. QR kodları silinemez.'}), 400

        # B2 depolama kullanılıyorsa, dosyaları da sil
        if USE_B2_STORAGE and get_b2_service:
            try:
                b2_service = get_b2_service()
                # B2'deki tüm QR dosyalarını sil
                files = b2_service.list_files('qr_codes/')
                for file_info in files:
                    try:
                        b2_service.delete_file(file_info['name'])
                    except Exception as e:
                        logging.error(f"B2'den {file_info['name']} silinirken hata: {e}")
            except Exception as e:
                logging.error(f"B2 temizliği hatası: {e}")

        # Local depolama kullanılıyorsa, klasörü temizle
        if not USE_B2_STORAGE:
            qr_dir = os.path.join('static', 'qrcodes')
            if os.path.exists(qr_dir):
                for file in os.listdir(qr_dir):
                    try:
                        os.remove(os.path.join(qr_dir, file))
                    except Exception as e:
                        logging.error(f"Lokal dosya {file} silinirken hata: {e}")

        # QR kodlarını ve parçaları sil
        execute_query(cursor, 'DELETE FROM qr_codes')
        execute_query(cursor, 'DELETE FROM parts')

        conn.commit()
        close_db(conn)

        # Cache'i temizle
        cache_clear()

        logging.info("Tüm QR kodları temizlendi")
        return jsonify({
            'success': True,
            'message': 'Tüm QR kodları başarıyla silindi'
        })
    except Exception as e:
        try:
            close_db(conn)
        except:
            pass
        logging.error(f"QR kodları silinirken hata: {e}", exc_info=True)
        return jsonify({'error': f'QR kodları silinirken hata: {str(e)}'}), 500

@app.route('/generate_qr_image/<qr_id>')
@login_required
def generate_qr_image(qr_id):
    """Dual-mode QR kod oluşturma: Local (geçici) vs Production (kalıcı)"""
    try:
        # Cache'den kontrol et
        cache_key = f'qr_image_{qr_id}'
        cached_image = cache_get(cache_key)

        if cached_image:
            buf = BytesIO(cached_image)
            return send_file(buf, mimetype='image/png')

        if USE_B2_STORAGE and get_b2_service:
            # PRODUCTION: B2'den QR kod'u indir
            b2_service = get_b2_service()
            file_path = f'qr_codes/{qr_id}.png'

            # B2'den dosyayı kontrol et
            file_content = b2_service.download_file(file_path)

            if file_content:
                # B2'den var olan dosyayı cache'e kaydet ve döndür
                cache_set(cache_key, file_content)
                buf = BytesIO(file_content)
                buf.seek(0)
                return send_file(buf, mimetype='image/png')
        else:
            # LOCAL: Static dosyadan kontrol et
            static_path = os.path.join('static', 'qrcodes', f'{qr_id}.png')
            if os.path.exists(static_path):
                with open(static_path, 'rb') as f:
                    file_content = f.read()
                cache_set(cache_key, file_content)
                buf = BytesIO(file_content)
                return send_file(buf, mimetype='image/png')

        # QR kod yoksa oluştur - optimize edilmiş ayarlar
        qr = qrcode.QRCode(
            version=1, 
            box_size=8,  # Küçültüldü
            border=2,    # Küçültüldü
            error_correction=qrcode.constants.ERROR_CORRECT_L  # Minimum hata düzeltme
        )
        qr.add_data(qr_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = BytesIO()
        img.save(buf, format='PNG', optimize=True)  # Optimize edilmiş PNG
        buf.seek(0)

        # Cache'e kaydet
        img_data = buf.getvalue()
        cache_set(cache_key, img_data)

        if USE_B2_STORAGE and get_b2_service:
            # PRODUCTION: B2'ye async upload (KALICI)
            b2_service = get_b2_service()
            file_path = f'qr_codes/{qr_id}.png'
            threading.Thread(
                target=lambda: b2_service.upload_file(file_path, img_data, 'image/png'),
                daemon=True
            ).start()
        else:
            # LOCAL: Static klasörüne kaydet (GEÇİCİ)
            qr_dir = os.path.join('static', 'qrcodes')
            os.makedirs(qr_dir, exist_ok=True)
            local_path = os.path.join(qr_dir, f'{qr_id}.png')
            with open(local_path, 'wb') as f:
                f.write(img_data)

        # Dosyayı döndür
        buf.seek(0)
        return send_file(buf, mimetype='image/png')

    except Exception as e:
        logging.error(f"Error generating QR image for {qr_id}: {e}")
        # Hata durumunda basit QR oluştur
        qr = qrcode.QRCode(version=1, box_size=6, border=1)
        qr.add_data(qr_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        return send_file(buf, mimetype='image/png')

@app.route('/download_single_qr/<qr_id>')
@login_required
def download_single_qr(qr_id):
    conn = get_db()
    cursor = conn.cursor()
    execute_query(cursor, 'SELECT part_code FROM qr_codes WHERE qr_id = %s', (qr_id,))
    result = cursor.fetchone()

    if not result:
        close_db(conn)
        return jsonify({'error': 'QR kod bulunamadı'}), 404

    execute_query(cursor, 'UPDATE qr_codes SET is_downloaded = %s, downloaded_at = %s WHERE qr_id = %s',
                 (True, datetime.now(), qr_id))
    conn.commit()
    close_db(conn)

    try:
        if USE_B2_STORAGE and get_b2_service:
            # PRODUCTION: B2'den QR kod'u indir (KALICI)
            b2_service = get_b2_service()
            file_path = f'qr_codes/{qr_id}.png'

            file_content = b2_service.download_file(file_path)

            if file_content:
                # B2'den var olan dosyayı döndür
                buf = BytesIO(file_content)
                buf.seek(0)
                return send_file(buf, mimetype='image/png', as_attachment=True, download_name=f'{qr_id}.png')
        else:
            # LOCAL: Static dosyadan kontrol et (GEÇİCİ)
            static_path = os.path.join('static', 'qrcodes', f'{qr_id}.png')
            if os.path.exists(static_path):
                return send_file(static_path, mimetype='image/png', as_attachment=True, download_name=f'{qr_id}.png')

        # QR kod yoksa oluştur
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        img_data = buf.getvalue()

        if USE_B2_STORAGE and get_b2_service:
            # PRODUCTION: B2'ye yükle (KALICI)
            b2_service = get_b2_service()
            file_path = f'qr_codes/{qr_id}.png'
            upload_result = b2_service.upload_file(file_path, img_data, 'image/png')


            if upload_result['success']:
                logging.info(f"QR code uploaded to B2: {file_path}")
        else:
            # LOCAL: Static klasörüne kaydet (GEÇİCİ)
            qr_dir = os.path.join('static', 'qrcodes')
            os.makedirs(qr_dir, exist_ok=True)
            local_path = os.path.join(qr_dir, f'{qr_id}.png')
            with open(local_path, 'wb') as f:
                f.write(img_data)

        # Dosyayı döndür
        buf.seek(0)
        return send_file(buf, mimetype='image/png', as_attachment=True, download_name=f'{qr_id}.png')

    except Exception as e:
        logging.error(f"Error downloading QR image for {qr_id}: {e}")
        # Hata durumunda geleneksel yöntemle oluştur
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        return send_file(buf, mimetype='image/png', as_attachment=True, download_name=f'{qr_id}.png')

# 🚀 ULTRA QR SCANNER HANDLER
@socketio.on('scan_qr_radical')
def handle_scan_radical(data):
    """🚀 Ultra reliable QR scanning with enhanced features"""
    print("\n" + "🚀"*50)
    print("ULTRA QR SCAN RECEIVED")
    print("🚀"*50)

    try:
        qr_id = data.get('qr_id', '').strip()
        session_id = data.get('session_id', '1')
        user_id = session.get('user_id', 1)

        print(f"📱 QR ID: {qr_id}")
        print(f"📱 Session: {session_id}")  
        print(f"📱 User: {user_id}")

        if not qr_id:
            print("❌ QR ID missing")
            emit('scan_result', {'success': False, 'message': '❌ QR ID eksik!'})
            return

        conn = get_db()
        cursor = conn.cursor()

        # Check QR exists
        execute_query(cursor, 'SELECT part_code, part_name FROM qr_codes WHERE qr_id = %s', (qr_id,))
        qr_data = cursor.fetchone()

        if not qr_data:
            close_db(conn)
            print(f"❌ QR not found: {qr_id}")
            emit('scan_result', {'success': False, 'message': f'❌ QR kod bulunamadı: {qr_id}'})
            return

        part_code, part_name = qr_data
        print(f"✅ QR found: {part_code} - {part_name}")

        # Ensure session exists
        execute_query(cursor, 'SELECT COUNT(*) FROM count_sessions WHERE session_id = %s', (str(session_id),))
        if cursor.fetchone()[0] == 0:
            print(f"⚠️ Creating session {session_id}")
            execute_query(cursor, 
                'INSERT INTO count_sessions (session_id, status, started_at) VALUES (%s, %s, %s)',
                (str(session_id), 'active', datetime.now()))

        # Check duplicate
        execute_query(cursor, 'SELECT COUNT(*) FROM scanned_qr WHERE session_id = %s AND qr_id = %s', 
                     (str(session_id), qr_id))
        if cursor.fetchone()[0] > 0:
            close_db(conn)
            print(f"⚠️ Duplicate: {qr_id}")
            emit('scan_result', {'success': False, 'message': f'⚠️ {part_name} zaten sayıldı!', 'duplicate': True}, broadcast=True)
            return


            # Insert scan record
            execute_query(cursor, 
                'INSERT INTO scanned_qr (session_id, qr_id, part_code, scanned_by, scanned_at) VALUES (%s, %s, %s, %s, %s)',
                (str(session_id), qr_id, part_code, user_id, datetime.now()))

            # Mark QR as used
            execute_query(cursor, 'UPDATE qr_codes SET is_used = %s, used_at = %s WHERE qr_id = %s',
                         (True, datetime.now(), qr_id))

        conn.commit()
        close_db(conn)

        print(f"✅ SUCCESS: {part_name} scanned")

        # Get user name
        conn2 = get_db()
        cursor2 = conn2.cursor()
        execute_query(cursor2, 'SELECT full_name FROM envanter_users WHERE id = %s', (user_id,))
        user_result = cursor2.fetchone()
        user_name = user_result[0] if user_result else 'Kullanıcı'
        close_db(conn2)

        # 🔥 TRIPLE BROADCAST
        success_data = {
            'success': True,
            'message': f'✅ {part_name} sayıldı!',
            'qr_code': qr_id,
            'part_code': part_code,
            'part_name': part_name,
            'session_id': session_id,
            'scanned_by': user_name,
            'scanned_at': datetime.now().strftime('%H:%M:%S')
        }

        socketio.emit('scan_result', success_data, broadcast=True)
        socketio.emit('qr_scanned', success_data, broadcast=True)
        socketio.emit('activity_update', success_data, broadcast=True)

        print("🚀 ULTRA SUCCESS - TRIPLE BROADCAST!")
        print("🚀"*50)

    except Exception as e:
        print(f"❌ ULTRA ERROR: {e}")
        import traceback
        traceback.print_exc()
        emit('scan_result', {'success': False, 'message': f'❌ Sistem hatası: {e}'})

# 🚀 ULTRA MODERN API ENDPOINTS
@app.route('/api/scan_qr', methods=['POST'])
def api_scan_qr_ultra():
    """🚀 Ultra reliable QR scanning API endpoint with modern tech"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        qr_id = data.get('qr_id', '').strip()
        session_id = data.get('session_id', '1')

        if not qr_id:
            return jsonify({'success': False, 'message': 'QR ID required'}), 400

        print(f"🚀 ULTRA API QR Scan: {qr_id} in session {session_id}")

        # Process the scan with ultra reliability
        result = process_qr_scan_ultra(qr_id, session_id)

        # Ultra broadcast - emit to all clients for real-time updates
        socketio.emit('scan_result', result)
        socketio.emit('qr_scanned', result)
        socketio.emit('activity_update', result)

        return jsonify(result)

    except Exception as e:
        print(f"❌ ULTRA API scan error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

def process_qr_scan_ultra(qr_id, session_id):
    """🚀 Ultra reliable QR processing with enhanced features"""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Ultra session management - ensure session exists with better naming
        session_name = f"Tarama Seansı {session_id}"
        execute_query(cursor, """
            INSERT INTO count_sessions (session_id, status, started_at) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (session_id) DO NOTHING
        """, (str(session_id), 'active', datetime.now()))

        # Check if QR exists with enhanced data retrieval
        execute_query(cursor, """
            SELECT qr_id, part_code, part_name, is_used, created_at
            FROM qr_codes 
            WHERE qr_id = %s
        """, (qr_id,))

        qr_data = cursor.fetchone()

        if not qr_data:
            # Auto-create unknown QR for tracking
            unknown_name = f"Bilinmeyen Ürün ({qr_id[:8]})"
            execute_query(cursor, """
                INSERT INTO qr_codes (qr_id, part_code, part_name, is_used, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (qr_id) DO NOTHING
            """, (qr_id, qr_id[:10], unknown_name, False, datetime.now()))

            qr_data = (qr_id, qr_id[:10], unknown_name, False, datetime.now())

        qr_id_db, part_code, part_name, is_used, created_at = qr_data

        # Ultra duplicate checking with time cooldown
        execute_query(cursor, """
            SELECT scanned_at FROM scanned_qr 
            WHERE qr_id = %s AND session_id = %s
            ORDER BY scanned_at DESC LIMIT 1
        """, (qr_id, str(session_id)))

        existing_scan = cursor.fetchone()
        if existing_scan:
            time_diff = datetime.now() - existing_scan[0]
            if time_diff.total_seconds() < 5:  # 5 seconds ultra cooldown
                return {
                    'success': False,
                    'message': f'⚠️ {part_name} zaten tarandı! (5 saniye bekleyin)',
                    'item_name': part_name,
                    'cooldown_remaining': int(5 - time_diff.total_seconds()),
                    'duplicate': True
                }

        # Insert ultra scan record with enhanced data
        execute_query(cursor, """
            INSERT INTO scanned_qr (qr_id, session_id, part_code, scanned_by, scanned_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (qr_id, str(session_id), part_code, session.get('user_id', 1), datetime.now()))

        # Mark QR as used with timestamp (DB-agnostic)
        execute_query(cursor, """
            UPDATE qr_codes 
            SET is_used = %s, used_at = %s 
            WHERE qr_id = %s
        """, (True, datetime.now(), qr_id))

        # Get enhanced session statistics
        execute_query(cursor, """
            SELECT 
                COUNT(*) as total_scans,
                COUNT(DISTINCT qr_id) as unique_items
            FROM scanned_qr 
            WHERE session_id = %s
        """, (str(session_id),))

        stats = cursor.fetchone()
        total_scans = stats[0] if stats else 0
        unique_items = stats[1] if stats else 0

        conn.commit()

        # Get user info for enhanced feedback
        user_id = session.get('user_id', 1)
        execute_query(cursor, 'SELECT full_name FROM envanter_users WHERE id = %s', (user_id,))
        user_result = cursor.fetchone()
        user_name = user_result[0] if user_result else 'Kullanıcı'

        # Ultra success response
        return {
            'success': True,
            'message': f'✅ {part_name} başarıyla tarandı! (#{total_scans})',
            'item_name': part_name,
            'part_code': part_code,
            'total_scans': total_scans,
            'unique_items': unique_items,
            'qr_id': qr_id,
            'session_id': session_id,
            'scanned_by': user_name,
            'scan_time': datetime.now().isoformat(),
            'was_used_before': is_used
        }

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ ULTRA Process QR error: {e}")
        return {
            'success': False,
            'message': f'❌ Sistem hatası: {str(e)}',
            'error_detail': str(e),
            'qr_id': qr_id
        }
    finally:
        if conn:
            close_db(conn)

@app.route('/api/session/<session_id>/stats', methods=['GET'])
def get_ultra_session_stats(session_id):
    """🚀 Get ultra detailed session statistics"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Get session info
        execute_query(cursor, """
            SELECT 
                CASE 
                    WHEN is_active::integer = 1 THEN 'active'
                    WHEN is_active::integer = 0 THEN 'completed'
                    ELSE 'unknown'
                END as status, 
                started_at, 
                ended_at 
            FROM count_sessions 
            WHERE session_id = %s
        """, (str(session_id),))

        session_info = cursor.fetchone()

        if not session_info:
            return jsonify({'error': 'Session not found'}), 404

        # Get ultra scan statistics
        execute_query(cursor, """
            SELECT 
                COUNT(*) as total_scans,
                COUNT(DISTINCT qr_id) as unique_items,
                MIN(scanned_at) as first_scan,
                MAX(scanned_at) as last_scan
            FROM scanned_qr 
            WHERE session_id = %s
        """, (str(session_id),))

        stats = cursor.fetchone()

        # Get recent scans with enhanced data
        execute_query(cursor, """
            SELECT sq.qr_id, qc.part_name, sq.scanned_at, u.full_name
            FROM scanned_qr sq
            LEFT JOIN qr_codes qc ON sq.qr_id = qc.qr_id
            LEFT JOIN envanter_users u ON sq.scanned_by = u.id
            WHERE sq.session_id = %s
            ORDER BY sq.scanned_at DESC
            LIMIT 20
        """, (str(session_id),))

        recent_scans = cursor.fetchall()

        # Calculate session duration
        start_time = session_info[1]
        end_time = session_info[2] or (stats[3] if stats[3] else datetime.now())
        duration_seconds = (end_time - start_time).total_seconds() if start_time else 0

        return jsonify({
            'session_id': session_id,
            'status': session_info[0],
            'started_at': start_time.isoformat() if start_time else None,
            'ended_at': session_info[2].isoformat() if session_info[2] else None,
            'duration_seconds': duration_seconds,
            'total_scans': stats[0] or 0,
            'unique_items': stats[1] or 0,
            'first_scan': stats[2].isoformat() if stats[2] else None,
            'last_scan': stats[3].isoformat() if stats[3] else None,
            'scans_per_minute': round((stats[0] or 0) / max(duration_seconds / 60, 1), 2),
            'recent_scans': [
                {
                    'qr_id': scan[0],
                    'item_name': scan[1] or f'Unknown ({scan[0]})',
                    'scan_time': scan[2].isoformat() if scan[2] else None,
                    'scanned_by': scan[3] or 'Bilinmeyen'
                }
                for scan in recent_scans
            ]
        })

    except Exception as e:
        print(f"❌ ULTRA Stats error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            close_db(conn)

@app.route('/api/qr/<qr_id>/info', methods=['GET'])
def get_ultra_qr_info(qr_id):
    """🚀 Get ultra detailed QR code information"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Get QR info with scan history
        execute_query(cursor, """
            SELECT qc.qr_id, qc.part_code, qc.part_name, 
                   qc.is_used, qc.created_at, qc.used_at,
                   COUNT(sq.qr_id) as scan_count
            FROM qr_codes qc
            LEFT JOIN scanned_qr sq ON qc.qr_id = sq.qr_id
            WHERE qc.qr_id = %s
            GROUP BY qc.qr_id, qc.part_code, qc.part_name, 
                     qc.is_used, qc.created_at, qc.used_at
        """, (qr_id,))

        qr_info = cursor.fetchone()

        if not qr_info:
            return jsonify({'error': 'QR code not found'}), 404

        # Get scan history
        execute_query(cursor, """
            SELECT sq.session_id, sq.scanned_at, u.full_name, 
                   CASE 
                       WHEN cs.is_active::integer = 1 THEN 'active'
                       WHEN cs.is_active::integer = 0 THEN 'completed'
                       ELSE 'unknown'
                   END as status
            FROM scanned_qr sq
            LEFT JOIN envanter_users u ON sq.scanned_by = u.id
            LEFT JOIN count_sessions cs ON sq.session_id = cs.session_id
            WHERE sq.qr_id = %s
            ORDER BY sq.scanned_at DESC
            LIMIT 10
        """, (qr_id,))

        scan_history = cursor.fetchall()

        return jsonify({
            'qr_id': qr_info[0],
            'part_code': qr_info[1],
            'part_name': qr_info[2],
            'is_used': qr_info[3],
            'created_at': qr_info[4].isoformat() if qr_info[4] else None,
            'used_at': qr_info[5].isoformat() if qr_info[5] else None,
            'total_scans': qr_info[6],
            'scan_history': [
                {
                    'session_id': scan[0],
                    'scanned_at': scan[1].isoformat() if scan[1] else None,
                    'scanned_by': scan[2] or 'Bilinmeyen',
                    'session_status': scan[3] or 'unknown'
                }
                for scan in scan_history
            ]
        })

    except Exception as e:
        print(f"❌ ULTRA QR Info error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            close_db(conn)

@app.route('/finish_count', methods=['POST'])
def finish_count():
    try:
        # 🔐 ULTRA SECURITY: Sadece admin kullanıcısı sayımı bitirebilir
        current_user_id = session.get('user_id')

        if not current_user_id:
            return jsonify({'success': False, 'error': 'Oturum bulunamadı - Lütfen tekrar giriş yapın'}), 401

        # Admin kontrolü - kullanıcı bilgilerini al
        conn = get_db()
        cursor = conn.cursor()

        execute_query(cursor, "SELECT username, role FROM envanter_users WHERE id = %s", (current_user_id,))
        user_result = cursor.fetchone()

        if not user_result:
            close_db(conn)
            return jsonify({'success': False, 'error': 'Kullanıcı bulunamadı'}), 404

        username, user_role = user_result

        # 🚫 SADECE ADMIN YETKİSİ
        if username.lower() != 'admin':
            close_db(conn)
            security_logger.warning(f'USER {username} (ID: {current_user_id}) tried to finish count session - PERMISSION DENIED')
            return jsonify({
                'success': False, 
                'error': 'YETKISIZ ERİŞİM: Sadece admin kullanıcısı sayımı bitirebilir',
                'permission_required': 'admin'
            }), 403

        # Sayım erişim kontrolü (secondary check)
        if not session.get('count_access'):
            close_db(conn)
            return jsonify({'success': False, 'error': 'Sayım erişimi için şifre gerekli'}), 403

        # Aktif sayım oturumunu kontrol et
        execute_query(cursor, "SELECT session_id, is_active, created_by FROM count_sessions WHERE is_active = %s LIMIT 1", (True,))
        session_result = cursor.fetchone()

        if not session_result:
            close_db(conn)
            return jsonify({'success': False, 'error': 'Aktif sayım oturumu bulunamadı'}), 400

        session_id, is_active_status, created_by = session_result

        # Log admin action
        security_logger.info(f'ADMIN {username} finishing count session {session_id}')

        # Çift işlem kontrolü - eğer bu oturum zaten tamamlandıysa
        if not is_active_status:
            close_db(conn)
            return jsonify({'success': False, 'error': 'Bu sayım oturumu zaten tamamlanmış'}), 400

        # Sayım oturumunu sonlandır (admin yetkisiyle)
        execute_query(cursor, "UPDATE count_sessions SET is_active = %s, ended_at = %s WHERE session_id = %s",
                     (False, datetime.now(), session_id))

        # Rapor verilerini topla
        execute_query(cursor, '''
            SELECT 
                i.part_code,
                COALESCE(p.part_name, 'Bilinmeyen Parça') as part_name,
                i.expected_quantity as envanter,
                COUNT(s.qr_id) as sayim
            FROM inventory_data i
            LEFT JOIN parts p ON i.part_code = p.part_code
            LEFT JOIN scanned_qr s ON i.part_code = s.part_code AND i.id = s.id
            WHERE i.session_id = %s
            GROUP BY i.part_code, p.part_name, i.expected_quantity
        ''', (str(session_id),))

        results = cursor.fetchall()

        # Rapor verilerini hazırla
        report_data = []
        total_expected = 0
        total_scanned = 0

        for row in results:
            part_data = {
                'Parça Kodu': row[0],
                'Parça Adı': row[1],
                'Envanter Adeti': row[2],
                'Sayım Adeti': row[3],
                'Fark': row[3] - row[2]
            }
            report_data.append(part_data)
            total_expected += row[2]
            total_scanned += row[3]

        # Excel raporu oluştur
        df = pd.DataFrame(report_data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sayım Raporu')
        output.seek(0)

        # Rapor dosyasını kaydet
        report_filename = f'sayim_raporu_{str(session_id)[:8]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        report_path = os.path.join(REPORTS_DIR, report_filename)

        with open(report_path, 'wb') as f:
            f.write(output.getvalue())

        # Doğruluk oranını hesapla
        accuracy_rate = (total_scanned / total_expected * 100) if total_expected > 0 else 0.0

        # Raporu count_reports table'ına kaydet
        report_title = f"Sayım Raporu - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        execute_query(cursor, '''
            INSERT INTO count_reports (session_id, report_filename, report_title, 
                                     total_expected, total_scanned, accuracy_rate, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (str(session_id), report_filename, report_title, 
              total_expected, total_scanned, accuracy_rate, datetime.now()))

        # Database işlemini commit et
        conn.commit()
        close_db(conn)

        # WebSocket ile sayım bittiği bilgisini gönder
        try:
            socketio.emit('count_finished', {'session_id': session_id})
        except Exception as ws_error:
            logging.warning(f"WebSocket notification failed: {str(ws_error)}")

        # Session'dan sayım bilgilerini temizle
        session.pop('count_access', None)
        session.pop('current_session', None)

        return jsonify({
            'success': True,
            'message': 'Sayım başarıyla tamamlandı',
            'report_file': report_filename,
            'session_id': session_id,
            'total_expected': total_expected,
            'total_scanned': total_scanned,
            'accuracy_rate': round(accuracy_rate, 2)
        })

    except Exception as e:
        # Hata durumunda database bağlantısını kapatmayı garanti et
        try:
            if 'conn' in locals():
                close_db(conn)
        except:
            pass

        error_msg = f"Sayım tamamlama hatası: {str(e)}"
        logging.error(error_msg, exc_info=True)

        return jsonify({
            'success': False,
            'error': 'Sayım tamamlanamadı - sistem hatası',
            'debug': str(e) if app.debug else None
        }), 500

@app.route('/stop_all_counts', methods=['POST'])
def stop_all_counts():
    """Tüm aktif sayımları durdur - ACIL DURUMFONKSİYONU"""
    # Admin authentication check
    admin_password = request.json.get('admin_password')
    if admin_password != ADMIN_COUNT_PASSWORD:
        return jsonify({'success': False, 'error': 'Yetki gerekli - yanlış admin şifresi'}), 403

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Tüm aktif sayımları bul
        execute_query(cursor, "SELECT session_id FROM count_sessions WHERE is_active = TRUE")
        active_sessions = cursor.fetchall()

        if not active_sessions:
            close_db(conn)
            return jsonify({'success': True, 'message': 'Durdurulacak aktif sayım bulunamadı'})

        # Tüm aktif sayımları "completed" olarak işaretle
        stopped_count = 0
        for session_tuple in active_sessions:
            session_id = session_tuple[0]
            execute_query(cursor, 'UPDATE count_sessions SET status = %s, ended_at = %s WHERE session_id = %s',
                         ('completed', datetime.now(), session_id))
            stopped_count += 1

        # Session'ları temizle
        session.pop('count_access', None)
        session.pop('count_authenticated', None) 
        session.pop('current_session', None)

        conn.commit()
        close_db(conn)

        # WebSocket ile tüm kullanıcılara sayımların durdurulduğunu bildir
        socketio.emit('all_counts_stopped', {
            'message': f'{stopped_count} aktif sayım durduruldu',
            'stopped_sessions': [s[0] for s in active_sessions]
        })

        return jsonify({
            'success': True,
            'message': f'{stopped_count} aktif sayım başarıyla durduruldu',
            'stopped_sessions': [s[0] for s in active_sessions]
        })

    except Exception as e:
        conn.rollback()
        close_db(conn)
        return jsonify({'success': False, 'error': f'Sistem hatası: {str(e)}'}), 500

@app.route('/reports')
def reports_page():
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('reports.html')

@app.route('/qr_codes')
def qr_codes_page():
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('qr_codes.html')

@app.route('/check_existing_qrs')
@login_required
def check_existing_qrs():
    conn = get_db()
    cursor = conn.cursor()
    execute_query(cursor, 'SELECT COUNT(*) FROM qr_codes')
    count = cursor.fetchone()[0]
    close_db(conn)

    return jsonify({
        'hasQRs': count > 0,
        'count': count
    })

@app.route('/qr_management', methods=['GET'])
@login_required
def qr_management():
    """QR Yönetim Paneli - Güvenli QR işlemleri"""
    if not session.get('admin_authenticated'):
        return redirect('/admin')
    return render_template('qr_management.html')

@app.route('/get_reports')
@login_required
def get_reports():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Join count_reports with count_sessions for complete data
        execute_query(cursor, '''
            SELECT 
                cr.id, 
                cr.session_id, 
                cr.report_filename, 
                cr.report_title, 
                cr.created_at,
                cr.total_expected, 
                cr.total_scanned, 
                cr.accuracy_rate,
                CASE 
                    WHEN CAST(cs.is_active AS INTEGER) = 1 THEN 'active'
                    WHEN CAST(cs.is_active AS INTEGER) = 0 THEN 'completed'
                    ELSE 'unknown'
                END as status,
                cs.started_at
            FROM count_reports cr
            LEFT JOIN count_sessions cs ON cr.session_id = cs.session_id
            ORDER BY cr.created_at DESC
        ''')

        rows = cursor.fetchall()
        reports = []
        for row in rows:
            reports.append({
                'id': row[0],
                'session_id': row[1],
                'filename': row[2],
                'title': row[3],
                'created_at': row[4],
                'total_expected': row[5],
                'total_scanned': row[6],
                'accuracy_rate': row[7],
                'session_name': f"Session {row[1]}" if row[1] else 'Bilinmeyen Session',
                'created_by': row[8] or 'System',  # Using status as created_by
                'total_difference': (row[6] - row[5]) if (row[5] is not None and row[6] is not None) else None
            })

        return jsonify(reports)

    except Exception as e:
        logging.exception(f"Error in get_reports: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        try:
            if conn:
                close_db(conn)
        except Exception:
            pass

@app.route('/download_report/<filename>')
@login_required
def download_report(filename):
    if not re.match(r'^sayim_raporu_[a-f0-9]{8}_\d{8}_\d{6}\.xlsx$', filename):
        return jsonify({'error': 'Geçersiz dosya adı'}), 400

    safe_filename = secure_filename(filename)
    report_path = os.path.join(REPORTS_DIR, safe_filename)

    if not os.path.exists(report_path):
        return jsonify({'error': 'Rapor dosyası bulunamadı'}), 404

    real_path = os.path.realpath(report_path)
    reports_real_path = os.path.realpath(REPORTS_DIR)

    if not real_path.startswith(reports_real_path):
        return jsonify({'error': 'Geçersiz dosya yolu'}), 403

    return send_file(report_path, as_attachment=True)

@app.route('/admin_count')
@login_required
@admin_count_required
def admin_count_page():
    return render_template('admin_count.html')

@app.route('/admin_count/verify_password', methods=['POST'])
@login_required
@admin_count_required
def verify_admin_count_password():
    try:
        data = request.get_json()
        password = data.get('password', '')

        print(f"DEBUG: Admin count password attempt - received: '{password}'")  # DEBUG
        print(f"DEBUG: Admin count password attempt - expected: '{ADMIN_COUNT_PASSWORD}'")  # DEBUG

        # Türkçe karakter desteği için case-insensitive karşılaştırma
        password_lower = password.lower().replace('ı', 'i').replace('İ', 'i').replace('I', 'i')
        expected_lower = ADMIN_COUNT_PASSWORD.lower()

        print(f"DEBUG: Admin count password normalized - received: '{password_lower}'")  # DEBUG
        print(f"DEBUG: Admin count password normalized - expected: '{expected_lower}'")  # DEBUG
        print(f"DEBUG: Admin count password match: {password_lower == expected_lower}")  # DEBUG

        if password_lower == expected_lower:
            session['count_access'] = True
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Yanlış şifre'}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def count_access_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('count_access'):
            return jsonify({'error': 'Sayım erişimi için şifre gerekli'}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin_count/start_count', methods=['POST'])
@login_required
@admin_count_required
def admin_start_count():
    """Admin sayım başlatma endpoint'i"""
    print("DEBUG: admin_start_count çağrıldı")
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Aktif sayım var mı kontrol et (Dual-mode uyumlu)
        execute_query(cursor, 'SELECT COUNT(*) FROM count_sessions WHERE is_active = %s', (True,))
        active_count = cursor.fetchone()[0]
        
        if active_count > 0:
            close_db(conn)
            return jsonify({
                'success': False,
                'error': 'Zaten aktif bir sayım oturumu var!'
            }), 400
        
        # Yeni sayım oturumu oluştur
        import uuid
        session_id = str(uuid.uuid4())
        current_user_id = session.get('user_id')
        
        # Toplam beklenen adet
        execute_query(cursor, 'SELECT COUNT(*) FROM qr_codes')
        total_expected = cursor.fetchone()[0]
        
        execute_query(cursor, '''
            INSERT INTO count_sessions 
            (session_id, is_active, started_at, created_by, created_at, total_expected, total_scanned) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (session_id, True, datetime.now(), current_user_id, datetime.now(), total_expected, 0))
        
        conn.commit()
        close_db(conn)
        
        print(f"✅ Sayım oturumu başlatıldı: {session_id}")
        
        return jsonify({
            'success': True,
            'message': 'Sayım oturumu başlatıldı',
            'session_id': session_id,
            'total_expected': total_expected
        })
        
    except Exception as e:
        print(f"❌ Sayım başlatma hatası: {e}")
        import traceback
        traceback.print_exc()
        
        if conn:
            try:
                conn.rollback()
                close_db(conn)
            except:
                pass
        
        return jsonify({
            'success': False,
            'error': f'Sayım başlatılamadı: {str(e)}'
        }), 500

# API Endpoints for Dashboard Statistics
@app.route('/api/qr_codes')
@login_required
def api_get_qr_codes():
    """QR kodları listesi - istatistik için"""
    conn = get_db()
    cursor = conn.cursor()

    execute_query(cursor, '''
        SELECT qr_id, part_code, part_name, is_used, is_downloaded, created_at
        FROM qr_codes 
        ORDER BY created_at DESC
    ''')

    qr_codes = []
    for row in cursor.fetchall():
        qr_codes.append({
            'qr_id': row[0],
            'part_code': row[1],
            'part_name': row[2],
            'is_used': bool(row[3]),
            'is_downloaded': bool(row[4]),
            'created_at': row[5]
        })

    close_db(conn)
    return jsonify(qr_codes)

@app.route('/api/reports')
@login_required
def api_get_reports():
    """Raporlar listesi - istatistik için"""
    conn = get_db()
    cursor = conn.cursor()

    execute_query(cursor, '''
        SELECT id, session_id, report_name, file_path, created_at, 
               total_expected, total_scanned, accuracy_rate
        FROM count_reports
        ORDER BY created_at DESC
    ''')

    reports = []
    for row in cursor.fetchall():
        reports.append({
            'id': row[0],
            'session_id': row[1],
            'report_name': row[2],
            'file_path': row[3],
            'created_at': row[4],
            'total_expected': row[5],
            'total_scanned': row[6],
            'accuracy_rate': row[7]
        })


    close_db(conn)
    return jsonify(reports)

@app.route('/api/dashboard_stats')
def api_dashboard_stats():

    """Dashboard için genel istatistikler"""
    print("DEBUG: /api/dashboard_stats endpoint çağrıldı")  # DEBUG
    conn = get_db()
    cursor = conn.cursor()




    # QR kodları sayısı
    execute_query(cursor, 'SELECT COUNT(*) FROM qr_codes')
    total_qr_codes = cursor.fetchone()[0]

    # Raporlar sayısı
    execute_query(cursor, 'SELECT COUNT(*) FROM count_sessions')
    total_reports = cursor.fetchone()[0]

    # Sayım bilgileri geçici olarak sıfır
    active_counts = 0
    completed_counts = 0
    last_count_date = None

    close_db(conn)

    stats = {
        'total_qr_codes': total_qr_codes,
        'total_reports': total_reports,
        'active_counts': active_counts,
        'completed_counts': completed_counts,
        'last_count_date': last_count_date
    }
    print(f"DEBUG: Gönderilen stats: {stats}")  # DEBUG
    return jsonify(stats)

# Eksik endpoint'ler
@app.route('/get_session_stats')
@login_required
def get_session_stats():
    """Sayım session istatistikleri"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Toplam session sayısı
        execute_query(cursor, 'SELECT COUNT(*) FROM count_sessions')
        total = cursor.fetchone()[0]
        
        # Aktif session sayısı
        execute_query(cursor, 'SELECT COUNT(*) FROM count_sessions WHERE is_active = %s', (True,))
        active = cursor.fetchone()[0]
        
        # Tamamlanmış session sayısı
        execute_query(cursor, 'SELECT COUNT(*) FROM count_sessions WHERE is_active = %s', (False,))
        completed = cursor.fetchone()[0]
        
        close_db(conn)
        
        return jsonify({
            'total': total,
            'active': active,
            'completed': completed
        })
    except Exception as e:
        logging.error(f"Error in get_session_stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_recent_activities')
@login_required
def get_recent_activities():
    """Son aktiviteler"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        execute_query(cursor, '''
            SELECT session_id, started_at, ended_at, is_active, total_expected, total_scanned
            FROM count_sessions
            ORDER BY started_at DESC
            LIMIT 10
        ''')
        
        activities = []
        for row in cursor.fetchall():
            activities.append({
                'session_id': row[0],
                'started_at': row[1],
                'ended_at': row[2],
                'is_active': bool(row[3]),
                'total_expected': row[4],
                'total_scanned': row[5]
            })
        
        close_db(conn)
        return jsonify(activities)
    except Exception as e:
        logging.error(f"Error in get_recent_activities: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_count_status')
@login_required
def get_count_status():
    """Aktif sayım durumu"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        execute_query(cursor, '''
            SELECT session_id, started_at, total_expected, total_scanned, is_active
            FROM count_sessions
            WHERE is_active = %s
            ORDER BY started_at DESC
            LIMIT 1
        ''', (True,))
        
        row = cursor.fetchone()
        close_db(conn)
        
        if row:
            return jsonify({
                'active': True,
                'session_id': row[0],
                'started_at': row[1],
                'total_expected': row[2],
                'total_scanned': row[3]
            })
        else:
            return jsonify({'active': False})
    except Exception as e:
        logging.error(f"Error in get_count_status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin')
@login_required
def admin_panel():
    """Admin panel"""
    # Admin kontrolü
    if session.get('username') != 'admin':
        return jsonify({'error': 'Admin erişimi gerekli'}), 403
    
    return render_template('admin.html')

# Health Check ve Monitoring Endpoints
@app.route('/health')
def health_check():
    """Sistem sağlık kontrolü"""
    try:
        # Database bağlantı kontrolü
        conn = get_db()
        cursor = conn.cursor()
        execute_query(cursor, 'SELECT 1')
        cursor.fetchone()
        close_db(conn)
        db_status = "✅ OK"

        # B2 bağlantı kontrolü
        if USE_B2_STORAGE and get_b2_service:
            try:
                b2_service = get_b2_service()
                b2_status = "✅ OK (PRODUCTION)"
            except Exception:
                b2_status = "⚠️ ERROR (PRODUCTION)"
        else:
            b2_status = "🏠 LOCAL MODE (B2 Disabled)"

        # Environment durumu kontrolü
        env_info = {
            'mode': 'production' if IS_PRODUCTION else 'development',
            'database_type': 'PostgreSQL' if USE_POSTGRESQL else 'SQLite',
            'storage_type': 'B2 Cloud' if USE_B2_STORAGE else 'Local Files',
            'database_url_set': bool(os.environ.get('DATABASE_URL')) if IS_PRODUCTION else 'N/A'
        }

        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': db_status,
            'storage': b2_status,
            'environment': env_info,
            'version': '2.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/metrics')
def metrics():
    """Sistem metrikleri"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # İstatistikler
        execute_query(cursor, 'SELECT COUNT(*) FROM qr_codes')
        total_qr = cursor.fetchone()[0]

        execute_query(cursor, 'SELECT COUNT(*) FROM qr_codes WHERE is_used = 1')
        used_qr = cursor.fetchone()[0]

        execute_query(cursor, 'SELECT COUNT(*) FROM envanter_users')
        total_users = cursor.fetchone()[0]

        execute_query(cursor, "SELECT COUNT(*) FROM count_sessions WHERE is_active = TRUE")
        active_sessions = cursor.fetchone()[0]

        close_db(conn)

        return jsonify({
            'qr_codes': {
                'total': total_qr,
                'used': used_qr,
                'remaining': total_qr - used_qr
            },
            'users': total_users,
            'active_sessions': active_sessions,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Render.com deployment check
def is_render_deployment():
    """Render.com deploy kontrolü"""
    return os.environ.get('RENDER') is not None

def get_port():
    """Port numarasını al"""
    return int(os.environ.get('PORT', 5001))

# QR Admin Blueprint'ini register et
try:
    from qr_admin import qr_admin_bp
    app.register_blueprint(qr_admin_bp)
    print("✅ QR Admin Panel registered")
except Exception as e:
    print(f"⚠️ QR Admin Panel registration failed: {e}")

# Debug endpoint for frontend testing
@app.route('/debug/test_api')
def test_api():
    """Test endpoint for debugging frontend issues"""
    return jsonify({
        'success': True,
        'message': 'API is working fine',
        'timestamp': datetime.now().isoformat(),
        'session_data': {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'count_access': session.get('count_access'),
            'authenticated': 'user_id' in session
        }
    })

@app.route('/debug/server_info')
def server_info():
    """Server status information"""
    return jsonify({
        'server': 'Flask',
        'version': '1.0',
        'status': 'running',
        'database': 'PostgreSQL' if IS_PRODUCTION else 'SQLite',
        'environment': 'production' if IS_PRODUCTION else 'development',
        'endpoints_count': len([rule for rule in app.url_map.iter_rules()]),
        'debug_mode': app.debug
    })

# NOTE: This is handled by render_startup_alt.py for Render.com
# DO NOT call socketio.run() here to avoid port binding conflicts
# The render_startup_alt.py script will import this app and call socketio.run()

if __name__ == '__main__':
    print("⚠️  Direct execution detected. Please use render_startup_alt.py")
    print("    Or set RENDER=false for local development with Flask")

    # Initialize database on startup
    try:
        init_db()
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")

    # For local testing only - DO NOT use in production
    if not os.environ.get('RENDER'):
        port = 5002
        print("🚀 Starting EnvanterQR System v2.0 (LOCAL)...")
        print("📊 Dashboard: http://localhost:5002")
        print("🔐 Admin Panel: http://localhost:5002/admin")
        print("🏥 Health Check: http://localhost:5002/health")
        print("📈 Metrics: http://localhost:5002/metrics")
        print("☁️ Storage: Backblaze B2 Enabled")
        print("🔒 Security: Headers + Rate Limiting Active")
        print()
        socketio.run(app, host='127.0.0.1', port=port, debug=True, allow_unsafe_werkzeug=True)
    else:
        print("ERROR: This should not run with RENDER=true")
        print("Use: gunicorn wsgi:app --worker-class eventlet")
        print("Or:  python render_startup_alt.py")