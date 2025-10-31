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
    # LOCAL: SQLite + Local Storage (GEÇİCİ)
    print("🏠 Local Mode: SQLite + Local Storage (GEÇİCİ)")
    USE_B2_STORAGE = False
    USE_POSTGRESQL = False
    
    # db_config.py kullan
    app.config.from_object(DevelopmentConfig)

# Database setup

print(f"💾 Database: {'PostgreSQL' if USE_POSTGRESQL else 'SQLite'}")
print(f"📁 Storage: {'B2 Cloud' if USE_B2_STORAGE else 'Local Files'}")
print(f"🔄 Data: {'KALICI' if IS_PRODUCTION else 'GEÇİCİ'}")
print("="*60)

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

# Admin sayım şifresi
ADMIN_COUNT_PASSWORD = "admin123"
print(f"DEBUG: ADMIN_COUNT_PASSWORD = '{ADMIN_COUNT_PASSWORD}'")  # DEBUG

os.makedirs(REPORTS_DIR, exist_ok=True)

def get_db_placeholder():
    """Database'e göre doğru placeholder döndür (%s for PostgreSQL, ? for SQLite)"""
    return '?' if not USE_POSTGRESQL else '%s'

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
    
    if USE_POSTGRESQL:
        # PRODUCTION: Return to PostgreSQL pool
        try:
            if conn:
                # If connection is already closed at the libpq level, tell the pool to close it
                try:
                    if getattr(conn, 'closed', 1):
                        db_pool.putconn(conn, close=True)
                    else:
                        db_pool.putconn(conn)
                except TypeError:
                    # Older psycopg2 versions may not accept close kwarg; fallback
                    try:
                        db_pool.putconn(conn)
                    except Exception:
                        pass
        except Exception as e:
            logging.error(f"Error returning PostgreSQL connection to pool: {e}")
    else:
        # LOCAL: Close SQLite connection
        try:
            if conn:
                conn.close()
        except Exception as e:
            logging.error(f"Error closing SQLite connection: {e}")

def create_performance_indexes(cursor):
    """Performans için kritik indexleri oluştur"""
    indexes = [
        # Envanter tablosu indexleri
        "CREATE INDEX IF NOT EXISTS idx_envanter_qr_code ON envanter(qr_code);",
        "CREATE INDEX IF NOT EXISTS idx_envanter_urun_kodu ON envanter(urun_kodu);",
        "CREATE INDEX IF NOT EXISTS idx_envanter_created_at ON envanter(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_envanter_last_scanned ON envanter(last_scanned);",
        
        # Sayım geçmişi indexleri
        "CREATE INDEX IF NOT EXISTS idx_sayim_gecmisi_envanter_id ON sayim_gecmisi(envanter_id);",
        "CREATE INDEX IF NOT EXISTS idx_sayim_gecmisi_scanned_at ON sayim_gecmisi(scanned_at);",
        "CREATE INDEX IF NOT EXISTS idx_sayim_gecmisi_user_id ON sayim_gecmisi(user_id);",
        
        # Sayım oturum indexleri
        "CREATE INDEX IF NOT EXISTS idx_sayim_oturum_status ON sayim_oturum(status);",
        "CREATE INDEX IF NOT EXISTS idx_sayim_oturum_created_at ON sayim_oturum(created_at);",
        
        # Kullanıcı indexleri
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
        "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);",
        
        # Composite indexler (çoklu sütun)
        "CREATE INDEX IF NOT EXISTS idx_envanter_compound ON envanter(qr_code, urun_kodu);",
        "CREATE INDEX IF NOT EXISTS idx_sayim_compound ON sayim_gecmisi(envanter_id, scanned_at);",
    ]
    
    try:
        for index_sql in indexes:
            cursor.execute(index_sql)
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
                inspector = db.inspect(db.engine)
                existing_tables = inspector.get_table_names()
                required_tables = ['users', 'part_codes', 'qr_codes', 'count_sessions', 'count_passwords', 'scanned_qr']
                
                missing_tables = [t for t in required_tables if t not in existing_tables]
                
                if missing_tables:
                    print(f"☁️ Creating missing PostgreSQL tables: {', '.join(missing_tables)}")
                    db.create_all()
                    print("✅ PostgreSQL tables created successfully")
                else:
                    print("✅ PostgreSQL tables already exist")
                
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
                # LOCAL: SQLite - Raw SQL ile (basit tablo yapısı)
                print("🏠 Local SQLite mode - checking simple table structure")
                
                # SQLite bağlantısı al
                conn = get_db()
                cursor = conn.cursor()
                
                # SQLite schema'yı güncelle (full_name column ekle)
                try:
                    cursor.execute("ALTER TABLE envanter_users ADD COLUMN full_name VARCHAR(255)")
                    print("✅ Added full_name column to SQLite")
                except sqlite3.OperationalError:
                    # Column zaten varsa veya başka hata
                    pass
                
                # Admin user var mı kontrol et (SQLite raw SQL)
                cursor.execute("SELECT * FROM envanter_users WHERE username = 'admin'")
                admin_exists = cursor.fetchone()
                
                if not admin_exists:
                    print("➕ Creating default SQLite admin user...")
                    from werkzeug.security import generate_password_hash
                    admin_password_hash = generate_password_hash("admin123")
                    cursor.execute('''
                        INSERT INTO envanter_users (username, password_hash, full_name, role, created_at, is_active)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', ('admin', admin_password_hash, 'Administrator', 'admin', datetime.now(), 1))
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
        cursor.execute(f'SELECT role FROM envanter_users WHERE id = {placeholder}', (session['user_id'],))
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
        cursor.execute('SELECT role FROM users WHERE id = %s', (session['user_id'],))
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
        cursor.execute('SELECT COUNT(*) FROM envanter')
        total_qr_codes = cursor.fetchone()[0]
        
        # Toplam sayım sayısı
        cursor.execute('SELECT COUNT(*) FROM sayim_gecmisi')
        total_scans = cursor.fetchone()[0]
        
        # Aktif oturum sayısı
        cursor.execute('SELECT COUNT(*) FROM count_sessions WHERE status = %s', ('active',))
        active_sessions = cursor.fetchone()[0]
        
        # Son sayım tarihi
        cursor.execute('SELECT MAX(scanned_at) FROM sayim_gecmisi')
        last_scan = cursor.fetchone()[0]
        
        # Bugünkü sayımlar
        cursor.execute('''
            SELECT COUNT(*) FROM sayim_gecmisi 
            WHERE DATE(scanned_at) = CURRENT_DATE
        ''')
        today_scans = cursor.fetchone()[0]
        
        # Bu haftaki sayımlar
        cursor.execute('''
            SELECT COUNT(*) FROM sayim_gecmisi 
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
    cursor.execute('SELECT COUNT(*) FROM count_sessions WHERE status = %s', ('active',))
    active_session = cursor.fetchone()
    
    if active_session[0] == 0:
        # Aktif sayım yoksa ana sayfaya yönlendir
        close_db(conn)
        return redirect('/')
    
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
            cursor.execute(f'SELECT id, username, full_name, role, password_hash FROM envanter_users WHERE username = {placeholder}',
                         (username,))
        else:
            # SQLite: envanter_users table with full_name (after column addition)
            cursor.execute(f'SELECT id, username, COALESCE(full_name, username) as full_name, role, password_hash FROM envanter_users WHERE username = {placeholder}',
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
                cursor.execute(f'SELECT id, username, full_name, role, password_hash FROM envanter_users WHERE username = {placeholder}',
                             (username,))
            else:
                cursor.execute(f'SELECT id, username, COALESCE(full_name, username) as full_name, role, password_hash FROM envanter_users WHERE username = {placeholder}',
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
        cursor.execute("DELETE FROM qr_codes WHERE qr_id LIKE 'TEST-%'")
        cursor.execute("DELETE FROM parts WHERE part_code LIKE 'TEST-%'")
        
        # Test parçalarını ekle
        for part_code, part_name, quantity in test_parts:
            # Part'ı ekle
            cursor.execute('INSERT INTO parts (part_code, part_name, quantity) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
                         (part_code, part_name, quantity))
            
            # QR kodları oluştur
            for i in range(quantity):
                qr_id = f"{part_code}-{i+1:03d}"
                cursor.execute('INSERT INTO qr_codes (qr_id, part_code, part_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
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
        
        cursor.execute('SELECT qr_id, part_code, part_name, is_used FROM qr_codes ORDER BY qr_id LIMIT 20')
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
    cursor.execute(f'SELECT COUNT(*) as count FROM count_sessions WHERE status = {placeholder}', ('active',))
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
        
        # Mevcut parçaları ve QR kodları al
        cursor.execute('SELECT part_code, part_name FROM parts')
        existing_parts = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('SELECT part_code, COUNT(*) as qr_count FROM qr_codes GROUP BY part_code')
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
                        cursor.execute(f'INSERT INTO qr_codes (qr_id, part_code, part_name, created_at, created_by, is_used, is_downloaded) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})',
                                     (qr_id, part_code, part_name, datetime.now(), session.get('username', 'system'), False, False))
                        new_qr_codes.append(qr_id)
                    
                    # Parça bilgilerini güncelle (quantity değil, sadece isim)
                    cursor.execute(f'UPDATE parts SET part_name = {placeholder} WHERE part_code = {placeholder}',
                                 (part_name, part_code))
                    updated_parts.append(part_code)
                    processing_summary['updated_parts'] += 1
                    processing_summary['new_qr_codes'] += missing_count
                    
                elif needed_quantity < current_qr_count:
                    # FAZLA QR KODLARI VAR - Sadece uyarı ver, silme!
                    extra_count = current_qr_count - needed_quantity
                    print(f"⚠️ {part_code}: {current_qr_count} mevcut > {needed_quantity} hedef = {extra_count} fazla QR (SİLİNMEDİ)")
                    
                    # Parça bilgilerini güncelle (quantity yok, sadece isim)
                    cursor.execute(f'UPDATE parts SET part_name = {placeholder} WHERE part_code = {placeholder}',
                                 (part_name, part_code))
                    updated_parts.append(part_code)
                    processing_summary['updated_parts'] += 1
                    
                else:
                    # TAM UYGUN - Sadece parça bilgilerini güncelle
                    print(f"✅ {part_code}: {current_qr_count} QR kod zaten uygun")
                    cursor.execute(f'UPDATE parts SET part_name = {placeholder} WHERE part_code = {placeholder}',
                                 (part_name, part_code))
                    
            else:
                # YENİ PARÇA - Tamamen yeni QR kodları oluştur
                print(f"🆕 {part_code}: Yeni parça - {needed_quantity} QR kod oluşturuluyor")
                
                cursor.execute(f'INSERT INTO parts (part_code, part_name, description, created_at, created_by, is_active) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})',
                             (part_code, part_name, '', datetime.now(), session.get('username', 'system'), True))
                
                for i in range(needed_quantity):
                    qr_id = f"{part_code}-{uuid.uuid4().hex[:8]}"
                    cursor.execute(f'INSERT INTO qr_codes (qr_id, part_code, part_name, created_at, created_by, is_used, is_downloaded) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})',
                                 (qr_id, part_code, part_name, datetime.now(), session.get('username', 'system'), False, False))
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
        cursor.execute("SELECT qr_id, part_code, part_name, is_used, is_downloaded FROM qr_codes WHERE part_code = %s OR part_name = %s ORDER BY part_code, qr_id LIMIT %s OFFSET %s", (search, search, limit, offset))
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
            cursor.execute("SELECT qr_id, part_code, part_name, is_used, is_downloaded FROM qr_codes WHERE part_code LIKE %s OR part_name LIKE %s ORDER BY part_code, qr_id LIMIT %s OFFSET %s", (f'%{search}%', f'%{search}%', limit, offset))
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
        cursor.execute("SELECT qr_id, part_code, part_name, is_used, is_downloaded FROM qr_codes ORDER BY part_code, qr_id LIMIT %s OFFSET %s", (limit, offset))
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
        cursor.execute("SELECT COUNT(*) FROM qr_codes WHERE part_code LIKE %s OR part_name LIKE %s", (f'%{search}%', f'%{search}%'))
    else:
        cursor.execute("SELECT COUNT(*) FROM qr_codes")
    
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
        cursor.execute('SELECT id, is_used FROM qr_codes WHERE qr_id = %s', (qr_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'error': 'QR kod bulunamadı'}), 404
            
        if result[1]:  # is_used
            return jsonify({'error': 'QR kod zaten kullanılmış'}), 400
            
        # QR kodu kullanıldı olarak işaretle
        cursor.execute('UPDATE qr_codes SET is_used = 1, used_at = CURRENT_TIMESTAMP WHERE qr_id = %s', (qr_id,))
        conn.commit()
        close_db(conn)
        
        return jsonify({'success': True, 'message': 'QR kod kullanıldı olarak işaretlendi'})
        
    except Exception as e:
        return jsonify({'error': f'Hata: {str(e)}'}), 500

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
    cursor.execute('SELECT part_code FROM qr_codes WHERE qr_id = %s', (qr_id,))
    result = cursor.fetchone()
    
    if not result:
        close_db(conn)
        return jsonify({'error': 'QR kod bulunamadı'}), 404
    
    cursor.execute('UPDATE qr_codes SET is_downloaded = 1, downloaded_at = %s WHERE qr_id = %s',
                 (datetime.now(), qr_id))
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

# Admin password: set to admin123 for development
ADMIN_PASSWORD = "admin123"
print(f"DEBUG: ADMIN_PASSWORD = '{ADMIN_PASSWORD}'")  # DEBUG

@app.route('/admin')
def admin_login():
    # Eğer session'da admin doğrulaması varsa direkt panel'e git
    if session.get('admin_authenticated'):
        return render_template('admin.html')
    
    # POST request ise şifre kontrolü yap
    if request.method == 'POST':
        password = request.form.get('admin_password')
        print(f"DEBUG: Admin login (GET/POST) - received password: '{password}'")  # DEBUG
        print(f"DEBUG: Admin login (GET/POST) - expected password: '{ADMIN_PASSWORD}'")  # DEBUG
        
        # Türkçe karakter desteği için case-insensitive karşılaştırma
        password_lower = password.lower().replace('ı', 'i').replace('İ', 'i').replace('I', 'i') if password else ''
        expected_lower = ADMIN_PASSWORD.lower()
        
        if password_lower == expected_lower:
            session['admin_authenticated'] = True
            return redirect('/admin')
        else:
            return render_template('admin_login.html', error='Yanlış şifre!')
    
    # GET request ise login sayfasını göster
    return render_template('admin_login.html')

@app.route('/admin', methods=['POST'])
def admin_login_post():
    password = request.form.get('admin_password')
    print(f"DEBUG: Admin login attempt - received password: '{password}'")  # DEBUG
    print(f"DEBUG: Admin login attempt - expected password: '{ADMIN_PASSWORD}'")  # DEBUG
    
    # Türkçe karakter desteği için case-insensitive karşılaştırma
    password_lower = password.lower().replace('ı', 'i').replace('İ', 'i').replace('I', 'i') if password else ''
    expected_lower = ADMIN_PASSWORD.lower()
    
    print(f"DEBUG: Admin login normalized - received: '{password_lower}'")  # DEBUG
    print(f"DEBUG: Admin login normalized - expected: '{expected_lower}'")  # DEBUG
    print(f"DEBUG: Admin login passwords match: {password_lower == expected_lower}")  # DEBUG
    
    if password_lower == expected_lower:
        session['admin_authenticated'] = True
        return redirect('/admin')
    else:
        return render_template('admin_login.html', error='Yanlış şifre!')

@app.route('/admin/users')
@admin_required
def get_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, full_name, role, created_at FROM users ORDER BY created_at DESC')
    rows = cursor.fetchall()
    
    # PostgreSQL row'larını dictionary'ye çevir
    users = []
    for row in rows:
        user_dict = {
            'id': row[0],
            'username': row[1], 
            'full_name': row[2],
            'role': row[3],
            'created_at': row[4]
        }
        users.append(user_dict)
    
    close_db(conn)
    return render_template('admin_users.html', users=users)

@app.route('/admin/users', methods=['POST'])
@admin_required
def create_user():
    import hashlib
    
    full_name = request.form.get('full_name')
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'user')
    
    if not all([full_name, username, password]):
        return jsonify({'error': 'Tüm alanlar gereklidir'}), 400
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password, password_hash, full_name, role) VALUES (%s, %s, %s, %s, %s)',
                     (username, password, password_hash, full_name, role))
        conn.commit()
        return jsonify({'success': True, 'message': 'Kullanıcı oluşturuldu'})
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Bu kullanıcı adı zaten kullanılıyor'}), 400
    finally:
        close_db(conn)

@app.route('/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    import hashlib
    
    full_name = request.form.get('full_name')
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'user')
    
    if not all([full_name, username]):
        return jsonify({'error': 'Ad soyad ve kullanıcı adı gereklidir'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        if password:  # Şifre değiştiriliyorsa
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('UPDATE users SET username = %s, password = %s, full_name = %s, role = %s WHERE id = %s',
                         (username, password_hash, full_name, role, user_id))
        else:  # Şifre değiştirilmiyorsa
            cursor.execute('UPDATE users SET username = %s, full_name = %s, role = %s WHERE id = %s',
                         (username, full_name, role, user_id))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Kullanıcı güncellendi'})
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Bu kullanıcı adı zaten kullanılıyor'}), 400
    finally:
        close_db(conn)

@app.route('/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if session.get('user_id') == user_id:
        return jsonify({'error': 'Kendi hesabınızı silemezsiniz'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
    conn.commit()
    close_db(conn)
    return jsonify({'success': True, 'message': 'Kullanıcı silindi'})

@app.route('/admin/users/<int:user_id>/change_password', methods=['POST'])
@admin_required
def change_user_password(user_id):
    """Admin tarafından kullanıcı şifresi değiştirme"""
    import hashlib
    
    data = request.get_json()
    new_password = data.get('password', '').strip()
    
    if not new_password or len(new_password) < 6:
        return jsonify({'error': 'Şifre en az 6 karakter olmalıdır'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # User'ın kendi hesabı mı kontrol et
        cursor.execute('SELECT id FROM users WHERE id = %s', (user_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Kullanıcı bulunamadı'}), 404
        
        # Şifre hash'le ve güncelle
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        cursor.execute('UPDATE users SET password = %s WHERE id = %s',
                     (new_password, user_id))
        # Eski hash'ı de güncelle compat için
        cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s',
                     (password_hash, user_id))
        
        conn.commit()
        return jsonify({'success': True, 'message': f'Şifre başarıyla değiştirildi'})
    
    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Hata: {str(e)}'}), 500
    finally:
        close_db(conn)

@app.route('/admin/reset_active_sessions', methods=['POST'])
@admin_required
def reset_active_sessions():
    conn = get_db()
    cursor = conn.cursor()
    
    # Aktif oturumları kontrol et
    cursor.execute("SELECT COUNT(*) FROM count_sessions WHERE status = \'active\'")
    active_count = cursor.fetchone()[0]
    
    if active_count == 0:
        close_db(conn)
        return jsonify({'success': True, 'message': 'Aktif sayım oturumu bulunamadı'})
    
    # Aktif oturumları kapat
    cursor.execute("UPDATE count_sessions SET status = 'completed', finished_at = %s WHERE status = 'active'",
                 (datetime.now(),))
    conn.commit()
    close_db(conn)
    
    # WebSocket ile tüm istemcilere bildir
    socketio.emit('sessions_reset', {'message': 'Aktif sayım oturumları yönetici tarafından kapatıldı'})
    
    return jsonify({'success': True, 'message': f'{active_count} aktif sayım oturumu kapatıldı'})

@app.route('/download_all_qr')
@login_required
def download_all_qr():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT qr_id, part_code, part_name FROM qr_codes WHERE is_used = 0 ORDER BY part_code, qr_id')
    qr_codes = cursor.fetchall()
    close_db(conn)
    
    memory_file = BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for row in qr_codes:
            qr_id = row[0]
            part_code = row[1]
            file_path = f'qr_codes/{qr_id}.png'
            
            try:
                file_content = None
                
                if USE_B2_STORAGE and get_b2_service:
                    # PRODUCTION: B2'den QR kod'u indir (KALICI)
                    b2_service = get_b2_service()
                    file_content = b2_service.download_file(file_path)
                else:
                    # LOCAL: Static dosyadan kontrol et (GEÇİCİ)
                    static_path = os.path.join('static', 'qrcodes', f'{qr_id}.png')
                    if os.path.exists(static_path):
                        with open(static_path, 'rb') as f:
                            file_content = f.read()
                
                if file_content:
                    # Var olan dosyayı kullan
                    zipf.writestr(f'{part_code}_{qr_id}.png', file_content)
                else:
                    # QR kod yoksa oluştur
                    qr = qrcode.QRCode(version=1, box_size=10, border=4)
                    qr.add_data(qr_id)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                    img_buffer = BytesIO()
                    img.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    
                    img_data = img_buffer.getvalue()
                    
                    if USE_B2_STORAGE and get_b2_service:
                        # PRODUCTION: B2'ye yükle (KALICI)
                        b2_service = get_b2_service()
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
                    
                    # ZIP'e ekle
                    zipf.writestr(f'{part_code}_{qr_id}.png', img_data)
                    
            except Exception as e:
                logging.error(f"Error processing QR code {qr_id}: {e}")
                # Hata durumunda geleneksel yöntemle oluştur
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(qr_id)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                img_buffer = BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                zipf.writestr(f'{part_code}_{qr_id}.png', img_buffer.getvalue())
    
    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='qr_codes.zip')

def start_count_internal():
    if 'file' not in request.files:
        return jsonify({'error': 'Dosya bulunamadı'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Dosya seçilmedi'}), 400
    
    try:
        df = pd.read_excel(file)


        required_columns = ['part_code', 'quantity']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': 'Excel dosyası "part_code" ve "quantity" sütunlarını içermelidir'}), 400

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM count_sessions WHERE status = 'active'")
        active_session = cursor.fetchone()
        if active_session[0] > 0:
            close_db(conn)
            return jsonify({'error': 'Aktif bir sayım oturumu var. Önce mevcut sayımı bitirin.'}), 400

        session_id = uuid.uuid4().hex
        cursor.execute('INSERT INTO count_sessions (session_id, status) VALUES (%s, %s)', (session_id, 'active'))

        for _, row in df.iterrows():
            part_code = str(row['part_code'])
            quantity = int(row['quantity'])
            # part_name veritabanından alınacak
            cursor.execute('SELECT part_name FROM parts WHERE part_code = %s LIMIT 1', (part_code,))
            part_result = cursor.fetchone()
            part_name = part_result[0] if part_result and part_result[0] else 'Unknown Part'

            cursor.execute('INSERT INTO inventory_data (session_id, part_code, part_name, expected_quantity) VALUES (%s, %s, %s, %s)',
                         (session_id, part_code, part_name, quantity))

        # Güçlü parola oluştur ve kaydet
        count_password = generate_strong_password()
        print(f"DEBUG: Oluşturulan şifre: {count_password}")  # Debug
        cursor.execute('INSERT INTO count_passwords (session_id, password, created_by) VALUES (%s, %s, %s)',
                     (session_id, count_password, session['user_id']))

        conn.commit()
        close_db(conn)

        session['current_session'] = session_id

        socketio.emit('count_started', {'session_id': session_id})

        response_data = {
            'success': True,
            'session_id': session_id,
            'count_password': count_password,
            'message': 'Sayım başlatıldı! Lütfen bu parolayı not alın'
        }
        print(f"DEBUG: Response data: {response_data}")  # Debug
        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': f'Hata: {str(e)}'}), 500

@app.route('/start_count', methods=['POST'])
@login_required
def start_count():
    # Eski API - artık admin panelinden erişilebilir
    return jsonify({'error': 'Bu özellik artık admin panelinden erişilebilir'}), 403

@app.route('/verify_count_password', methods=['POST'])
def verify_count_password():
    data = request.get_json()
    password = data.get('password')
    
    if not password:
        return jsonify({'error': 'Parola girilmedi'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Aktif sayım oturumunu bul
    cursor.execute("SELECT session_id FROM count_sessions WHERE status = \'active\' LIMIT 1")
    session_result = cursor.fetchone()
    
    if not session_result:
        close_db(conn)
        return jsonify({'error': 'Aktif sayım oturumu bulunamadı'}), 404
    
    session_id = session_result[0]
    
    # Parolayı kontrol et
    cursor.execute('SELECT password FROM count_passwords WHERE session_id = %s', (session_id,))
    password_result = cursor.fetchone()
    
    close_db(conn)
    
    if not password_result:
        return jsonify({'error': 'Bu sayım için parola bulunamadı'}), 404
    
    if password_result[0] == password:
        session['count_access'] = True
        session['current_session'] = session_id
        return jsonify({'success': True, 'message': 'Parola doğru, sayım ekranına yönlendiriliyorsunuz'})
    else:
        return jsonify({'error': 'Yanlış parola'}), 401

@app.route('/get_count_status')
@login_required
def get_count_status():
    # Geçici basit response - sayım sistemi şimdilik kapalı
    return jsonify({
        'active': False,
        'active_session': None
    })

@app.route('/get_session_stats')
@login_required
def get_session_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    # Aktif sayım oturumunu bul
    cursor.execute("SELECT session_id FROM count_sessions WHERE status = \'active\' LIMIT 1")
    session_result = cursor.fetchone()
    
    if not session_result:
        close_db(conn)
        return jsonify({'success': False, 'error': 'Aktif sayım oturumu bulunamadı'})
    
    session_id = session_result[0]
    
    # Beklenen toplam sayıyı hesapla
    cursor.execute('SELECT SUM(expected_quantity) FROM inventory_data WHERE session_id = %s', (session_id,))
    expected_total = cursor.fetchone()[0] or 0
    
    # Okutulan sayıyı hesapla
    cursor.execute('SELECT COUNT(*) FROM scanned_qr WHERE session_id = %s', (session_id,))
    scanned_total = cursor.fetchone()[0] or 0
    
    close_db(conn)
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'expected': expected_total,
        'scanned': scanned_total,
        'accuracy': round((scanned_total / expected_total * 100) if expected_total > 0 else 0, 1)
    })

@app.route('/get_recent_activities')
@login_required
def get_recent_activities():
    conn = get_db()
    cursor = conn.cursor()
    
    # Aktif sayım oturumunu bul
    cursor.execute("SELECT session_id FROM count_sessions WHERE status = \'active\' LIMIT 1")
    session_result = cursor.fetchone()
    
    if not session_result:
        close_db(conn)
        return jsonify({'success': False, 'error': 'Aktif sayım oturumu bulunamadı'})
    
    session_id = session_result[0]
    
    # Son 20 aktiviteyi getir
    cursor.execute('''
        SELECT 
            sq.qr_code,
            sq.scanned_at,
            sq.scanned_by,
            u.full_name,
            id.part_name
        FROM scanned_qr sq
        LEFT JOIN users u ON sq.scanned_by = u.id
        LEFT JOIN inventory_data id ON sq.qr_code = id.qr_code AND sq.session_id = id.session_id
        WHERE sq.session_id = %s
        ORDER BY sq.scanned_at DESC
        LIMIT 20
    ''', (session_id,))
    
    activities = []
    for row in cursor.fetchall():
        activities.append({
            'qr_code': row[0],
            'scanned_at': row[1],
            'scanned_by_id': row[2],
            'scanned_by': row[3] or 'Bilinmeyen Kullanıcı',
            'part_name': row[4]
        })
    
    close_db(conn)
    return jsonify({'success': True, 'activities': activities})

@socketio.on('scan_qr')
def handle_scan(data):
    print(f"DEBUG: handle_scan çağrıldı, data: {data}")  # DEBUG
    print(f"DEBUG: session keys: {list(session.keys())}")  # DEBUG
    print(f"DEBUG: count_access: {session.get('count_access')}")  # DEBUG
    
    # Sayım erişim kontrolü - önce aktif sayım olup olmadığını kontrol et
    conn = get_db()
    cursor = conn.cursor()
    
    # Aktif sayım oturumu kontrolü
    cursor.execute("SELECT session_id FROM count_sessions WHERE status = 'active' LIMIT 1")
    session_result = cursor.fetchone()
    
    if not session_result:
        emit('scan_result', {'success': False, 'message': 'Aktif sayım oturumu bulunamadı'})
        close_db(conn)
        print("DEBUG: Aktif sayım oturumu bulunamadı")
        return
    
    session_id = session_result[0]
    print(f"DEBUG: Aktif session_id: {session_id}")
    
    # Sayım erişim kontrolü - sadece aktif sayım varsa kontrol et
    if not session.get('count_access'):
        emit('scan_result', {'success': False, 'message': 'Sayım erişimi için şifre gerekli'})
        close_db(conn)
        print("DEBUG: count_access yok")
        return
    
    qr_id = data.get('qr_id')
    if not qr_id:
        emit('scan_result', {'success': False, 'message': 'QR kod verisi eksik'})
        close_db(conn)
        print("DEBUG: QR kod verisi eksik")
        return
    
    print(f"DEBUG: QR kod okutuldu: {qr_id}")
    
    # QR kod kontrolü - hem tam QR ID hem de part code ile ara
    cursor.execute('SELECT qr_id, part_code, part_name, is_used FROM qr_codes WHERE qr_id = %s OR part_code = %s', (qr_id, qr_id))
    qr_result = cursor.fetchone()
    
    if not qr_result:
        emit('scan_result', {'success': False, 'message': f'QR kod bulunamadı: {qr_id}'})
        close_db(conn)
        print(f"DEBUG: QR kod bulunamadı: {qr_id}")
        return
    
    if qr_result[3] == 1:
        emit('scan_result', {'success': False, 'message': 'Bu QR kod daha önce kullanıldı'})
        close_db(conn)
        print(f"DEBUG: QR kod zaten kullanılmış: {qr_id}")
        return
    
    # Bulunan QR kodun gerçek bilgilerini al
    actual_qr_id = qr_result[0]  # Gerçek QR ID
    part_code = qr_result[1]
    part_name = qr_result[2]
    
    print(f"DEBUG: Bulunan QR - ID: {actual_qr_id}, Part: {part_code}, Name: {part_name}")
    
    try:
        # QR kodu kullanıldı olarak işaretle - gerçek QR ID kullan
        cursor.execute('UPDATE qr_codes SET is_used = 1, used_at = %s WHERE qr_id = %s',
                     (datetime.now(), actual_qr_id))
        
        # Sayım kaydı ekle - gerçek QR ID kullan
        cursor.execute('INSERT INTO scanned_qr (session_id, qr_id, part_code, scanned_by) VALUES (%s, %s, %s, %s)',
                     (session_id, actual_qr_id, part_code, session.get('user_id')))
        
        conn.commit()
        print(f"DEBUG: QR kod başarıyla işlendi: {qr_id}")
        
        # Kullanıcı bilgisini al
        cursor.execute('SELECT full_name FROM users WHERE id = %s', (session.get('user_id'),))
        user_result = cursor.fetchone()
        user_name = user_result[0] if user_result else 'Bilinmeyen Kullanıcı'
        
        close_db(conn)
        
        emit('scan_result', {
            'success': True,
            'message': f'{part_name} ({part_code}) sayıldı',
            'qr_code': actual_qr_id,
            'part_code': part_code,
            'part_name': part_name,
            'scanned_by': user_name,
            'scanned_at': datetime.now().strftime('%H:%M')
        })
        
        print(f"DEBUG: scan_result emit edildi: success=True")
        
    except Exception as e:
        conn.rollback()
        close_db(conn)
        print(f"DEBUG: Veritabanı hatası: {e}")
        emit('scan_result', {'success': False, 'message': f'Veritabanı hatası: {str(e)}'})
        return

@app.route('/finish_count', methods=['POST'])
def finish_count():
    # Sayım erişim kontrolü
    if not session.get('count_access'):
        return jsonify({'success': False, 'error': 'Sayım erişimi için şifre gerekli'}), 403
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Aktif sayım oturumunu kontrol et
    cursor.execute("SELECT session_id, status FROM count_sessions WHERE status = \'active\' LIMIT 1")
    session_result = cursor.fetchone()
    
    if not session_result:
        close_db(conn)
        return jsonify({'error': 'Aktif sayım oturumu bulunamadı'}), 400
    
    session_id = session_result[0]
    
    # Çift işlem kontrolü - eğer bu oturum zaten tamamlandıysa
    cursor.execute('SELECT status FROM count_sessions WHERE session_id = %s', (session_id,))
    current_status = cursor.fetchone()
    if current_status and current_status[0] != 'active':
        close_db(conn)
        return jsonify({'error': 'Bu sayım oturumu zaten tamamlanmış'}), 400
    
    cursor.execute("UPDATE count_sessions SET status = 'completed', finished_at = %s WHERE session_id = %s",
                 (datetime.now(), session_id))
    
    cursor.execute('''
        SELECT 
            i.part_code,
            COALESCE(p.part_name, 'Bilinmeyen Parça') as part_name,
            i.expected_quantity as envanter,
            COUNT(s.qr_id) as sayim
        FROM inventory_data i
        LEFT JOIN parts p ON i.part_code = p.part_code
        LEFT JOIN scanned_qr s ON i.part_code = s.part_code AND i.session_id = s.session_id
        WHERE i.session_id = %s
        GROUP BY i.part_code, p.part_name, i.expected_quantity
    ''', (session_id,))
    
    results = cursor.fetchall()
    
    report_data = []
    total_expected = 0
    total_scanned = 0
    total_difference = 0
    
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
        total_difference += (row[3] - row[2])
    
    df = pd.DataFrame(report_data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sayım Raporu')
    output.seek(0)
    
    report_filename = f'sayim_raporu_{session_id[:8]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    report_path = os.path.join(REPORTS_DIR, report_filename)
    
    with open(report_path, 'wb') as f:
        f.write(output.getvalue())
    
    # Doğruluk oranını hesapla
    accuracy_rate = (total_scanned / total_expected * 100) if total_expected > 0 else 0.0
    
    # Raporu veritabanına kaydet
    report_title = f"Sayım Raporu - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    cursor.execute('''
        INSERT INTO count_reports (session_id, report_filename, report_title, 
                                 total_expected, total_scanned, accuracy_rate)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (session_id, report_filename, report_title, 
          total_expected, total_scanned, accuracy_rate))
    
    conn.commit()
    close_db(conn)
    
    # WebSocket ile sayım bittiği bilgisini gönder
    socketio.emit('count_finished', {'session_id': session_id})
    
    # Session'dan sayım bilgilerini temizle
    session.pop('count_authenticated', None)
    session.pop('current_session', None)
    
    return jsonify({
        'success': True,
        'message': 'Sayım başarıyla tamamlandı',
        'report_file': report_filename,
        'session_id': session_id
    })

@app.route('/stop_all_counts', methods=['POST'])
def stop_all_counts():
    """Tüm aktif sayımları durdur - ACIL DURUM FONKSİYONU"""
    # Admin authentication check
    admin_password = request.json.get('admin_password')
    if admin_password != ADMIN_COUNT_PASSWORD:
        return jsonify({'success': False, 'error': 'Yetki gerekli - yanlış admin şifresi'}), 403
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Tüm aktif sayımları bul
        cursor.execute("SELECT session_id FROM count_sessions WHERE status = \'active\'")
        active_sessions = cursor.fetchall()
        
        if not active_sessions:
            close_db(conn)
            return jsonify({'success': True, 'message': 'Durdurulacak aktif sayım bulunamadı'})
        
        # Tüm aktif sayımları "completed" olarak işaretle
        stopped_count = 0
        for session_tuple in active_sessions:
            session_id = session_tuple[0]
            cursor.execute('UPDATE count_sessions SET status = %s, finished_at = %s WHERE session_id = %s',
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
    cursor.execute('SELECT COUNT(*) FROM qr_codes')
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
        # Use the correct column names from schema
        cursor.execute('''
            SELECT id, session_id, report_filename, report_title, created_at,
                   total_expected, total_scanned, accuracy_rate
            FROM count_reports
            ORDER BY created_at DESC
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
                'total_difference': (row[6] - row[5]) if (row[5] is not None and row[6] is not None) else None,
                'created_by': 'Bilinmeyen'  # Default since we don't track creator
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
    print("DEBUG: admin_start_count çağrıldı")  # Debug
    return start_count_internal()

# API Endpoints for Dashboard Statistics
@app.route('/api/qr_codes')
@login_required
def api_get_qr_codes():
    """QR kodları listesi - istatistik için"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
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
    
    cursor.execute('''
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
    cursor.execute('SELECT COUNT(*) FROM qr_codes')
    total_qr_codes = cursor.fetchone()[0]
    
    # Raporlar sayısı
    cursor.execute('SELECT COUNT(*) FROM count_reports')
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

# Health Check ve Monitoring Endpoints
@app.route('/health')
def health_check():
    """Sistem sağlık kontrolü"""
    try:
        # Database bağlantı kontrolü
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
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
        cursor.execute('SELECT COUNT(*) FROM qr_codes')
        total_qr = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM qr_codes WHERE is_used = 1')
        used_qr = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM count_sessions WHERE status = 'active'")
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

if __name__ == '__main__':
    # Initialize database on startup
    try:
        init_db()
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")

    port = get_port()
    is_production = is_render_deployment()

    if is_production:
        print("🌐 Starting EnvanterQR on Render.com...")
        print(f"� Production Mode - Port: {port}")
        print("☁️ Storage: Backblaze B2 Enabled")
        print("🔒 Security: Production Headers Active")
        socketio.run(app, host='0.0.0.0', port=port, debug=False)
    else:
        print("�🚀 Starting EnvanterQR System v2.0...")
        print("📊 Dashboard: http://localhost:5002")
        print("🔐 Admin Panel: http://localhost:5002/admin")
        print("🏥 Health Check: http://localhost:5002/health")
        print("📈 Metrics: http://localhost:5002/metrics")
        print("☁️ Storage: Backblaze B2 Enabled")
        print("🔒 Security: Headers + Rate Limiting Active")
        print()
        socketio.run(app, host='127.0.0.1', port=5002, debug=True)

# ===== MIGRATION ENDPOINTS =====
@app.route('/migrate/update_admin_password')
def migrate_update_admin_password():
    """Production migration: Update admin password to use Werkzeug hashing"""
    try:
        from werkzeug.security import generate_password_hash
        
        if USE_POSTGRESQL:
            # First, create missing columns if they don't exist
            try:
                with db.engine.connect() as conn:
                    # Add missing columns to envanter_users table
                    missing_columns = [
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS real_name VARCHAR(255);",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS email VARCHAR(255);", 
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS job_title VARCHAR(120);",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS title VARCHAR(120);",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS work_position VARCHAR(120);",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS user_group VARCHAR(120);",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS user_role VARCHAR(120);",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS signature_path VARCHAR(500);",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS profile_image_path VARCHAR(500);",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS is_active_user BOOLEAN DEFAULT TRUE;",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS can_mark_used BOOLEAN DEFAULT FALSE;",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS email_2fa_enabled BOOLEAN DEFAULT FALSE;",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS email_2fa_code VARCHAR(10);",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS email_2fa_expires TIMESTAMP;",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS email_2fa_attempts INTEGER DEFAULT 0;",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS email_2fa_locked_until TIMESTAMP;",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS tc_number VARCHAR(20);",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS last_password_change TIMESTAMP;",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS force_password_change BOOLEAN DEFAULT FALSE;",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS force_tutorial BOOLEAN DEFAULT TRUE;",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS first_login_completed BOOLEAN DEFAULT FALSE;",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN DEFAULT FALSE;",
                        "ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                    ]
                    
                    for sql in missing_columns:
                        try:
                            conn.execute(db.text(sql))
                            conn.commit()
                        except Exception as col_error:
                            # Column might already exist, continue
                            pass
                            
                print("✅ PostgreSQL schema updated")
            except Exception as schema_error:
                return {'success': False, 'error': f'Schema update failed: {str(schema_error)}'}
            
            # Now try to work with admin user
            try:
                admin_user = User.query.filter_by(username='admin').first()
                if admin_user:
                    # Update password hash
                    admin_user.password_hash = generate_password_hash("@R9t$L7e!xP2w")
                    db.session.commit()
                    return {
                        'success': True, 
                        'message': 'PostgreSQL admin password updated to Werkzeug hash',
                        'username': 'admin',
                        'note': 'Password: @R9t$L7e!xP2w'
                    }
                else:
                    # Create new admin user
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
                    return {
                        'success': True, 
                        'message': 'PostgreSQL admin user created with Werkzeug hash',
                        'username': 'admin',
                        'note': 'Password: @R9t$L7e!xP2w'
                    }
            except Exception as user_error:
                return {'success': False, 'error': f'User operation failed: {str(user_error)}'}
                
        else:
            # SQLite - Raw SQL
            conn = get_db()
            cursor = conn.cursor()
            
            # Check if admin exists
            cursor.execute("SELECT id FROM envanter_users WHERE username = 'admin'")
            admin_exists = cursor.fetchone()
            
            if admin_exists:
                # Update existing admin
                new_hash = generate_password_hash("admin123")
                cursor.execute("UPDATE envanter_users SET password_hash = ? WHERE username = 'admin'", (new_hash,))
                conn.commit()
                close_db(conn)
                return {
                    'success': True, 
                    'message': 'SQLite admin password updated to Werkzeug hash',
                    'username': 'admin',
                    'note': 'Password: admin123'
                }
            else:
                # Create new admin
                new_hash = generate_password_hash("admin123")
                cursor.execute('''
                    INSERT INTO envanter_users (username, password_hash, full_name, role, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', ('admin', new_hash, 'Administrator', 'admin', datetime.now(), 1))
                conn.commit()
                close_db(conn)
                return {
                    'success': True, 
                    'message': 'SQLite admin user created with Werkzeug hash',
                    'username': 'admin',
                    'note': 'Password: admin123'
                }
                
    except Exception as e:
        return {'success': False, 'error': str(e), 'message': 'Migration failed'}
