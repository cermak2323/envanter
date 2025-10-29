from flask import Flask, render_template, request, jsonify, send_file, session, redirect
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from functools import wraps, lru_cache
import time
from collections import defaultdict
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
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
from b2_storage import get_b2_service
import logging
import threading
import json

# Load environment variables
load_dotenv()

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

# Static dosya sıkıştırma için
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 yıl cache

# SocketIO - Render.com compatible configuration
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e6
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
        request.is_mobile = True

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
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.socket.io; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; img-src 'self' data:;"
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

# PostgreSQL Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Connection Pool
db_pool = None

def init_db_pool():
    """Initialize database connection pool"""
    global db_pool
    try:
        # Production ortamı için optimize edilmiş pool ayarları
        db_pool = SimpleConnectionPool(
            minconn=2,  # Minimum bağlantı sayısı artırıldı
            maxconn=15, # Maximum bağlantı sayısı artırıldı
            dsn=DATABASE_URL
        )
        print("✅ PostgreSQL connection pool initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize database pool: {e}")
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
ADMIN_COUNT_PASSWORD = os.environ.get('ADMIN_COUNT_PASSWORD', generate_strong_password())

os.makedirs(REPORTS_DIR, exist_ok=True)

def get_db():
    """Get database connection from pool"""
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
            logging.warning(f"Database pool error, attempting to reinitialize pool: {e}")
            init_db_pool()
            conn = db_pool.getconn()
            return conn
        except Exception as e2:
            logging.error(f"Failed to get DB connection after reinit: {e2}")
            raise

def close_db(conn):
    """Return connection to pool"""
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
        logging.error(f"❌ Error returning connection to pool: {e}")

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
    """Initialize PostgreSQL database tables and performance indexes"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        print("🔄 Checking database tables...")
        
        # Check if users table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            );
        """)
        
        users_table_exists = cursor.fetchone()[0]
        
        if not users_table_exists:
            print("⚠️  Database tables not found. Please run the database_schema.sql script first.")
            print("   Command: psql '$DATABASE_URL' -f database_schema.sql")
            return False
        else:
            print("✅ Database tables found")
        
        # Create performance indexes if they don't exist
        create_performance_indexes(cursor)
        
        # Check if default admin user exists, if not create one
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = %s', ('admin',))
        if cursor.fetchone()[0] == 0:
            import hashlib
            # Generate strong default password
            default_admin_pass = generate_strong_password()
            admin_password_hash = hashlib.sha256(default_admin_pass.encode()).hexdigest()
            cursor.execute('INSERT INTO users (username, password, password_hash, full_name, role) VALUES (%s, %s, %s, %s, %s)',
                         ('admin', default_admin_pass, admin_password_hash, 'Administrator', 'admin'))
            print(f"✅ Default admin user created with secure password")
            print(f"⚠️  Please save this password securely: {default_admin_pass}")
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error checking database: {e}")
        print("💡 Please manually run database_schema.sql to create tables")
        return False
    finally:
        close_db(conn)

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
        cursor.execute('SELECT role FROM users WHERE id = %s', (session['user_id'],))
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
    import hashlib
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Kullanıcı adı ve şifre gerekli'}), 400
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, username, full_name, role FROM users WHERE username = %s AND password_hash = %s',
                     (username, password_hash))
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
            cursor.execute('SELECT id, username, full_name, role FROM users WHERE username = %s AND password_hash = %s',
                         (username, password_hash))
        except Exception as e2:
            logging.exception(f"Failed to execute login query after retry: {e2}")
            try:
                close_db(conn)
            except Exception:
                pass
            return jsonify({'error': 'Database connection error'}), 500

    user = cursor.fetchone()
    close_db(conn)
    
    if user:
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
            'username': session.get('username'),
            'full_name': session.get('full_name'),
            'role': session.get('role')
        })
    return jsonify({'authenticated': False})

@app.route('/upload_parts', methods=['POST'])
@login_required
def upload_parts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM count_sessions WHERE status = %s', ('active',))
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
        
        # Mevcut QR kodları için B2'den dosyaları sil
        try:
            b2_service = get_b2_service()
            cursor.execute('SELECT qr_id FROM qr_codes')
            existing_qr_codes = cursor.fetchall()
            
            for row in existing_qr_codes:
                qr_id = row[0]
                file_path = f'qr_codes/{qr_id}.png'
                b2_service.delete_file(file_path)
                logging.info(f"Deleted QR code from B2: {file_path}")
                
        except Exception as e:
            logging.error(f"Error deleting QR codes from B2: {e}")
        
        cursor.execute('DELETE FROM parts')
        cursor.execute('DELETE FROM qr_codes')
        
        qr_codes_data = []
        
        for _, row in df.iterrows():
            part_code = str(row['part_code'])
            part_name = str(row['part_name'])
            quantity = int(row['quantity'])
            
            cursor.execute('INSERT INTO parts (part_code, part_name, quantity) VALUES (%s, %s, %s)',
                         (part_code, part_name, quantity))
            
            for i in range(quantity):
                qr_id = f"{part_code}-{uuid.uuid4().hex[:8]}"
                cursor.execute('INSERT INTO qr_codes (qr_id, part_code, part_name) VALUES (%s, %s, %s)',
                             (qr_id, part_code, part_name))
                qr_codes_data.append({
                    'qr_id': qr_id,
                    'part_code': part_code,
                    'part_name': part_name
                })
        
        conn.commit()
        close_db(conn)
        
        return jsonify({
            'success': True,
            'message': f'{len(qr_codes_data)} adet QR kod oluşturuldu',
            'qr_count': len(qr_codes_data)
        })
    
    except Exception as e:
        return jsonify({'error': f'Hata: {str(e)}'}), 500

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
    """Optimize edilmiş QR kod oluşturma - cache + B2 storage"""
    try:
        # Cache'den kontrol et
        cache_key = f'qr_image_{qr_id}'
        cached_image = cache_get(cache_key)
        
        if cached_image:
            buf = BytesIO(cached_image)
            return send_file(buf, mimetype='image/png')
        
        # B2'den QR kod'u indir
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
            
            # B2'ye async upload (background'da)
            threading.Thread(
                target=lambda: b2_service.upload_file(file_path, img_data, 'image/png'),
                daemon=True
            ).start()
            
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
        # B2'den QR kod'u indir
        b2_service = get_b2_service()
        file_path = f'qr_codes/{qr_id}.png'
        
        file_content = b2_service.download_file(file_path)
        
        if file_content:
            # B2'den var olan dosyayı döndür
            buf = BytesIO(file_content)
            buf.seek(0)
            return send_file(buf, mimetype='image/png', as_attachment=True, download_name=f'{qr_id}.png')
        else:
            # QR kod yoksa oluştur ve B2'ye yükle
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(qr_id)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            
            # B2'ye yükle
            img_data = buf.getvalue()
            upload_result = b2_service.upload_file(file_path, img_data, 'image/png')
            
            if upload_result['success']:
                logging.info(f"QR code uploaded to B2: {file_path}")
            
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

# Admin password: prefer ADMIN_PASSWORD env var, fall back to ADMIN_COUNT_PASSWORD for backwards compatibility
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or os.environ.get('ADMIN_COUNT_PASSWORD', "@R9t$L7e!xP2w#Mn8Zq^Y4v&Bc6*Hd3J")

@app.route('/admin')
def admin_login():
    # Eğer session'da admin doğrulaması varsa direkt panel'e git
    if session.get('admin_authenticated'):
        return render_template('admin.html')
    
    # POST request ise şifre kontrolü yap
    if request.method == 'POST':
        password = request.form.get('admin_password')
        if password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            return redirect('/admin')
        else:
            return render_template('admin_login.html', error='Yanlış şifre!')
    
    # GET request ise login sayfasını göster
    return render_template('admin_login.html')

@app.route('/admin', methods=['POST'])
def admin_login_post():
    password = request.form.get('admin_password')
    if password == ADMIN_PASSWORD:
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
    b2_service = get_b2_service()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for row in qr_codes:
            qr_id = row[0]
            part_code = row[1]
            file_path = f'qr_codes/{qr_id}.png'
            
            try:
                # B2'den QR kod'u indir
                file_content = b2_service.download_file(file_path)
                
                if file_content:
                    # B2'den var olan dosyayı kullan
                    zipf.writestr(f'{part_code}_{qr_id}.png', file_content)
                else:
                    # QR kod yoksa oluştur ve B2'ye yükle
                    qr = qrcode.QRCode(version=1, box_size=10, border=4)
                    qr.add_data(qr_id)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                    img_buffer = BytesIO()
                    img.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    
                    img_data = img_buffer.getvalue()
                    
                    # B2'ye yükle
                    upload_result = b2_service.upload_file(file_path, img_data, 'image/png')
                    if upload_result['success']:
                        logging.info(f"QR code uploaded to B2: {file_path}")
                    
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
        
        cursor.execute("SELECT COUNT(*) as count FROM count_sessions WHERE status = \'active\'")
        active_session = cursor.fetchone()
        if active_session[0] > 0:
            close_db(conn)
            return jsonify({'error': 'Aktif bir sayım oturumu var. Önce mevcut sayımı bitirin.'}), 400
        
        session_id = uuid.uuid4().hex
        cursor.execute('INSERT INTO count_sessions (session_id, status) VALUES (%s, %s)', (session_id, 'active'))
        
        for _, row in df.iterrows():
            part_code = str(row['part_code'])
            quantity = int(row['quantity'])
            
            cursor.execute('SELECT part_name FROM parts WHERE part_code = %s LIMIT 1', (part_code,))
            part_result = cursor.fetchone()
            part_name = part_result[0] if part_result else 'Bilinmeyen Parça'
            
            cursor.execute('INSERT INTO inventory_data (session_id, part_code, expected_quantity) VALUES (%s, %s, %s)',
                         (session_id, part_code, quantity))
        
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
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT session_id, status, started_at FROM count_sessions WHERE status = \'active\' LIMIT 1")
    count_session = cursor.fetchone()
    close_db(conn)
    
    if count_session:
        return jsonify({
            'active': True,
            'session_id': count_session[0],
            'active_session': {
                'session_id': count_session[0],
                'status': count_session[1],
                'started_at': count_session[2]
            }
        })
    else:
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
    # Sayım erişim kontrolü
    if not session.get('count_access'):
        emit('scan_result', {'success': False, 'message': 'Sayım erişimi için şifre gerekli'})
        return
    
    qr_id = data.get('qr_id')
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT session_id FROM count_sessions WHERE status = \'active\' LIMIT 1")
    session_result = cursor.fetchone()
    
    if not session_result:
        emit('scan_result', {'success': False, 'message': 'Aktif sayım oturumu bulunamadı'})
        close_db(conn)
        return
    
    session_id = session_result[0]
    
    cursor.execute('SELECT qr_id, part_code, part_name, is_used FROM qr_codes WHERE qr_id = %s', (qr_id,))
    qr_result = cursor.fetchone()
    
    if not qr_result:
        emit('scan_result', {'success': False, 'message': 'QR kod bulunamadı'})
        close_db(conn)
        return
    
    if qr_result[3] == 1:
        emit('scan_result', {'success': False, 'message': 'Bu QR kod daha önce kullanıldı'})
        close_db(conn)
        return
    
    part_code = qr_result[1]
    part_name = qr_result[2]
    
    cursor.execute('UPDATE qr_codes SET is_used = 1, used_at = %s WHERE qr_id = %s',
                 (datetime.now(), qr_id))
    
    cursor.execute('INSERT INTO scanned_qr (session_id, qr_id, part_code, scanned_by) VALUES (%s, %s, %s, %s)',
                 (session_id, qr_id, part_code, session['user_id']))
    
    conn.commit()
    
    # Kullanıcı bilgisini al
    cursor.execute('SELECT full_name FROM users WHERE id = %s', (session['user_id'],))
    user_result = cursor.fetchone()
    user_name = user_result[0] if user_result else 'Bilinmeyen Kullanıcı'
    
    close_db(conn)
    
    emit('scan_result', {
        'success': True,
        'message': f'{part_name} ({part_code}) sayıldı',
        'part_code': part_code,
        'part_name': part_name,
        'scanned_by': user_name,
        'scanned_at': datetime.now().strftime('%H:%M')
    }, broadcast=True)

@app.route('/finish_count', methods=['POST'])
def finish_count():
    # Sayım erişim kontrolü
    if not session.get('count_access'):
        return jsonify({'success': False, 'error': 'Sayım erişimi için şifre gerekli'}), 403
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Aktif sayım oturumu kontrolü
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
        INSERT INTO count_reports (session_id, file_path, report_name, 
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
        
        # Tüm aktif sayımları "stopped" olarak işaretle
        stopped_count = 0
        for session_tuple in active_sessions:
            session_id = session_tuple[0]
            cursor.execute('UPDATE count_sessions SET status = "stopped", finished_at = %s WHERE session_id = %s',
                         (datetime.now(), session_id))
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
        }, broadcast=True)
        
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

@app.route('/clear_all_qrs', methods=['POST'])
@login_required
def clear_all_qrs():
    conn = get_db()
    cursor = conn.cursor()
    
    # Aktif sayım oturumu kontrolü
    cursor.execute("SELECT COUNT(*) FROM count_sessions WHERE status = \'active\'")
    active_session = cursor.fetchone()[0]
    
    if active_session > 0:
        close_db(conn)
        return jsonify({'error': 'Aktif bir sayım oturumu var. QR kodları silinemez.'}), 400
    
    try:
        # Mevcut QR kodları için B2'den dosyaları sil
        try:
            b2_service = get_b2_service()
            cursor.execute('SELECT qr_id FROM qr_codes')
            existing_qr_codes = cursor.fetchall()
            
            for row in existing_qr_codes:
                qr_id = row[0]
                file_path = f'qr_codes/{qr_id}.png'
                b2_service.delete_file(file_path)
                logging.info(f"Deleted QR code from B2: {file_path}")
                
        except Exception as e:
            logging.error(f"Error deleting QR codes from B2: {e}")
        
        # QR kodlarını ve parçaları sil
        cursor.execute('DELETE FROM qr_codes')
        cursor.execute('DELETE FROM parts')
        
        conn.commit()
        close_db(conn)
        
        return jsonify({
            'success': True,
            'message': 'Tüm QR kodları başarıyla silindi'
        })
    except Exception as e:
        close_db(conn)
        return jsonify({'error': f'QR kodları silinirken hata: {str(e)}'}), 500

@app.route('/get_reports')
@login_required
def get_reports():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Select only the columns we know exist in the schema to avoid runtime errors
        cursor.execute('''
            SELECT id, session_id, file_path, report_name, created_at,
                   total_expected, total_scanned, accuracy_rate
            FROM count_reports
            ORDER BY created_at DESC
        ''')

        reports = []
        for row in cursor.fetchall():
            reports.append({
                'id': row[0],
                'session_id': row[1],
                'filename': row[2],
                'title': row[3],
                'created_at': row[4],
                'total_expected': row[5],
                'total_scanned': row[6],
                'total_difference': (row[6] - row[5]) if (row[5] is not None and row[6] is not None) else None,
                'created_by': 'Bilinmeyen'
            })

        return jsonify(reports)

    except Exception as e:
        logging.exception(f"Error in get_reports: {e}")
        # Always return JSON error so the frontend doesn't try to parse HTML
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
        
        if password == ADMIN_COUNT_PASSWORD:
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
    
    # Aktif sayımlar
    cursor.execute("SELECT COUNT(*) FROM count_sessions WHERE status = 'active'")
    active_counts = cursor.fetchone()[0]
    
    # Tamamlanan sayımlar
    cursor.execute("SELECT COUNT(*) FROM count_sessions WHERE status = 'completed'")
    completed_counts = cursor.fetchone()[0]
    
    # Son sayım bilgisi
    cursor.execute('''
        SELECT started_at FROM count_sessions 
        WHERE status = 'completed' 
        ORDER BY started_at DESC LIMIT 1
    ''')
    last_count = cursor.fetchone()
    last_count_date = last_count[0] if last_count else None
    
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
        try:
            from b2_storage import get_b2_service
            b2_service = get_b2_service()
            b2_status = "✅ OK"
        except Exception:
            b2_status = "⚠️ ERROR"
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': db_status,
            'storage': b2_status,
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
        print("📊 Dashboard: http://localhost:5001")
        print("🔐 Admin Panel: http://localhost:5001/admin")
        print("🏥 Health Check: http://localhost:5001/health")
        print("📈 Metrics: http://localhost:5001/metrics")
        print("☁️ Storage: Backblaze B2 Enabled")
        print("🔒 Security: Headers + Rate Limiting Active")
        print()
        socketio.run(app, host='localhost', port=5001, debug=True)
