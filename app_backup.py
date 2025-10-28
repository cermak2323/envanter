from flask import Flask, render_template, request, jsonify, send_file, session, redirect
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import pandas as pd
import qrcode
from io import BytesIO
import base64
import os
import uuid
from datetime import datetime
import zipfile
import re
import hashlib
import secrets
import random
import string
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
socketio = SocketIO(app, cors_allowed_origins="*")

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
        db_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
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
ADMIN_COUNT_PASSWORD = os.environ.get('ADMIN_COUNT_PASSWORD', "@R9t$L7e!xP2w#Mn8Zq^Y4v&Bc6*Hd3J")

os.makedirs(REPORTS_DIR, exist_ok=True)

def get_db():
    """Get database connection from pool"""
    try:
        conn = db_pool.getconn()
        # PostgreSQL connection pool handles transactions automatically
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        raise

def close_db(conn):
    """Return connection to pool"""
    try:
        if conn:
            db_pool.putconn(conn)
    except Exception as e:
        print(f"❌ Error returning connection to pool: {e}")

def init_db():
    """Initialize PostgreSQL database tables"""
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
        
        # Check if default admin user exists, if not create one
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = %s', ('admin',))
        if cursor.fetchone()[0] == 0:
            import hashlib
            admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute('INSERT INTO users (username, password, password_hash, full_name, role) VALUES (%s, %s, %s, %s, %s)',
                         ('admin', 'admin123', admin_password, 'Administrator', 'admin'))
            print("✅ Default admin user created")
        
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
        conn.close()
        return render_template('count_password.html')
    
    print("DEBUG /count: count_access var, count.html gösteriliyor")  # DEBUG
    conn.close()
    return render_template('count.html')

@app.route('/login', methods=['POST'])
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
    cursor.execute('SELECT id, username, full_name, role FROM users WHERE username = %s AND password_hash = %s',
                 (username, password_hash))
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
        
        cursor.execute('DELETE FROM parts')
        cursor.execute('DELETE FROM qr_codes')
        
        qr_codes_data = []
        
        for _, row in df.iterrows():
            part_code = str(row['part_code'])
            part_name = str(row['part_name'])
            quantity = int(row['quantity'])
            
            cursor.execute('INSERT INTO parts (part_code, part_name, quantity) VALUES (?, ?, ?)',
                         (part_code, part_name, quantity))
            
            for i in range(quantity):
                qr_id = f"{part_code}-{uuid.uuid4().hex[:8]}"
                cursor.execute('INSERT INTO qr_codes (qr_id, part_code, part_name) VALUES (?, ?, ?)',
                             (qr_id, part_code, part_name))
                qr_codes_data.append({
                    'qr_id': qr_id,
                    'part_code': part_code,
                    'part_name': part_name
                })
        
        conn.commit()
        conn.close()
        
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
        cursor.execute("SELECT qr_id, part_code, part_name, is_used, is_downloaded FROM qr_codes WHERE part_code = ? OR part_name = ? ORDER BY part_code, qr_id LIMIT ? OFFSET ?", (search, search, limit, offset))
        exact_matches = cursor.fetchall()
        
        if exact_matches:
            qr_codes = [dict(row) for row in exact_matches]
        else:
            # Tam eşleşme bulunamazsa kısmi eşleşme ara
            cursor.execute("SELECT qr_id, part_code, part_name, is_used, is_downloaded FROM qr_codes WHERE part_code LIKE ? OR part_name LIKE ? ORDER BY part_code, qr_id LIMIT ? OFFSET ?", (f'%{search}%', f'%{search}%', limit, offset))
            qr_codes = [dict(row) for row in cursor.fetchall()]
    else:
        # Arama terimi yoksa tüm QR kodları getir (sayfalama ile)
        cursor.execute("SELECT qr_id, part_code, part_name, is_used, is_downloaded FROM qr_codes ORDER BY part_code, qr_id LIMIT ? OFFSET ?", (limit, offset))
        qr_codes = [dict(row) for row in cursor.fetchall()]
    
    # Toplam sayıyı al
    if search:
        cursor.execute("SELECT COUNT(*) FROM qr_codes WHERE part_code LIKE ? OR part_name LIKE ?", (f'%{search}%', f'%{search}%'))
    else:
        cursor.execute("SELECT COUNT(*) FROM qr_codes")
    
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
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
        cursor.execute('SELECT id, is_used FROM qr_codes WHERE qr_id = ?', (qr_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'error': 'QR kod bulunamadı'}), 404
            
        if result[1]:  # is_used
            return jsonify({'error': 'QR kod zaten kullanılmış'}), 400
            
        # QR kodu kullanıldı olarak işaretle
        cursor.execute('UPDATE qr_codes SET is_used = 1, used_at = CURRENT_TIMESTAMP WHERE qr_id = ?', (qr_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'QR kod kullanıldı olarak işaretlendi'})
        
    except Exception as e:
        return jsonify({'error': f'Hata: {str(e)}'}), 500

@app.route('/generate_qr_image/<qr_id>')
@login_required
def generate_qr_image(qr_id):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
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
    cursor.execute('SELECT part_code FROM qr_codes WHERE qr_id = ?', (qr_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return jsonify({'error': 'QR kod bulunamadı'}), 404
    
    cursor.execute('UPDATE qr_codes SET is_downloaded = 1, downloaded_at = ? WHERE qr_id = ?',
                 (datetime.now(), qr_id))
    conn.commit()
    conn.close()
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    return send_file(buf, mimetype='image/png', as_attachment=True, download_name=f'{qr_id}.png')

# Admin şifre konstansı
ADMIN_PASSWORD = "@R9t$L7e!xP2w#Mn8Zq^Y4v&Bc6*Hd3J"

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
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
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
        cursor.execute('INSERT INTO users (username, password, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)',
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
            cursor.execute('UPDATE users SET username = ?, password = ?, full_name = ?, role = ? WHERE id = ?',
                         (username, password_hash, full_name, role, user_id))
        else:  # Şifre değiştirilmiyorsa
            cursor.execute('UPDATE users SET username = ?, full_name = ?, role = ? WHERE id = ?',
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
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Kullanıcı silindi'})

@app.route('/admin/reset_active_sessions', methods=['POST'])
@admin_required
def reset_active_sessions():
    conn = get_db()
    cursor = conn.cursor()
    
    # Aktif oturumları kontrol et
    cursor.execute('SELECT COUNT(*) FROM count_sessions WHERE status = "active"')
    active_count = cursor.fetchone()[0]
    
    if active_count == 0:
        conn.close()
        return jsonify({'success': True, 'message': 'Aktif sayım oturumu bulunamadı'})
    
    # Aktif oturumları kapat
    cursor.execute('UPDATE count_sessions SET status = "completed", finished_at = ? WHERE status = "active"',
                 (datetime.now(),))
    conn.commit()
    conn.close()
    
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
    conn.close()
    
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for row in qr_codes:
            qr_id = row[0]
            part_code = row[1]
            
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
        
        cursor.execute('SELECT COUNT(*) as count FROM count_sessions WHERE status = "active"')
        active_session = cursor.fetchone()
        if active_session[0] > 0:
            conn.close()
            return jsonify({'error': 'Aktif bir sayım oturumu var. Önce mevcut sayımı bitirin.'}), 400
        
        session_id = uuid.uuid4().hex
        cursor.execute('INSERT INTO count_sessions (session_id, status) VALUES (?, ?)', (session_id, 'active'))
        
        for _, row in df.iterrows():
            part_code = str(row['part_code'])
            quantity = int(row['quantity'])
            
            cursor.execute('SELECT part_name FROM parts WHERE part_code = ? LIMIT 1', (part_code,))
            part_result = cursor.fetchone()
            part_name = part_result[0] if part_result else 'Bilinmeyen Parça'
            
            cursor.execute('INSERT INTO inventory_data (session_id, part_code, expected_quantity) VALUES (?, ?, ?)',
                         (session_id, part_code, quantity))
        
        # Güçlü parola oluştur ve kaydet
        count_password = generate_strong_password()
        print(f"DEBUG: Oluşturulan şifre: {count_password}")  # Debug
        cursor.execute('INSERT INTO count_passwords (session_id, password, created_by) VALUES (?, ?, ?)',
                     (session_id, count_password, session['user_id']))
        
        conn.commit()
        conn.close()
        
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
    cursor.execute('SELECT session_id FROM count_sessions WHERE status = "active" LIMIT 1')
    session_result = cursor.fetchone()
    
    if not session_result:
        conn.close()
        return jsonify({'error': 'Aktif sayım oturumu bulunamadı'}), 404
    
    session_id = session_result[0]
    
    # Parolayı kontrol et
    cursor.execute('SELECT password FROM count_passwords WHERE session_id = ?', (session_id,))
    password_result = cursor.fetchone()
    
    conn.close()
    
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
    cursor.execute('SELECT session_id, status, started_at FROM count_sessions WHERE status = "active" LIMIT 1')
    count_session = cursor.fetchone()
    conn.close()
    
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
    cursor.execute('SELECT session_id FROM count_sessions WHERE status = "active" LIMIT 1')
    session_result = cursor.fetchone()
    
    if not session_result:
        conn.close()
        return jsonify({'success': False, 'error': 'Aktif sayım oturumu bulunamadı'})
    
    session_id = session_result[0]
    
    # Beklenen toplam sayıyı hesapla
    cursor.execute('SELECT SUM(expected_quantity) FROM inventory_data WHERE session_id = ?', (session_id,))
    expected_total = cursor.fetchone()[0] or 0
    
    # Okutulan sayıyı hesapla
    cursor.execute('SELECT COUNT(*) FROM scanned_qr WHERE session_id = ?', (session_id,))
    scanned_total = cursor.fetchone()[0] or 0
    
    conn.close()
    
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
    cursor.execute('SELECT session_id FROM count_sessions WHERE status = "active" LIMIT 1')
    session_result = cursor.fetchone()
    
    if not session_result:
        conn.close()
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
        WHERE sq.session_id = ?
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
    
    conn.close()
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
    
    cursor.execute('SELECT session_id FROM count_sessions WHERE status = "active" LIMIT 1')
    session_result = cursor.fetchone()
    
    if not session_result:
        emit('scan_result', {'success': False, 'message': 'Aktif sayım oturumu bulunamadı'})
        conn.close()
        return
    
    session_id = session_result[0]
    
    cursor.execute('SELECT qr_id, part_code, part_name, is_used FROM qr_codes WHERE qr_id = ?', (qr_id,))
    qr_result = cursor.fetchone()
    
    if not qr_result:
        emit('scan_result', {'success': False, 'message': 'QR kod bulunamadı'})
        conn.close()
        return
    
    if qr_result[3] == 1:
        emit('scan_result', {'success': False, 'message': 'Bu QR kod daha önce kullanıldı'})
        conn.close()
        return
    
    part_code = qr_result[1]
    part_name = qr_result[2]
    
    cursor.execute('UPDATE qr_codes SET is_used = 1, used_at = ? WHERE qr_id = ?',
                 (datetime.now(), qr_id))
    
    cursor.execute('INSERT INTO scanned_qr (session_id, qr_id, part_code, scanned_by) VALUES (?, ?, ?, ?)',
                 (session_id, qr_id, part_code, session['user_id']))
    
    conn.commit()
    
    # Kullanıcı bilgisini al
    cursor.execute('SELECT full_name FROM users WHERE id = ?', (session['user_id'],))
    user_result = cursor.fetchone()
    user_name = user_result[0] if user_result else 'Bilinmeyen Kullanıcı'
    
    conn.close()
    
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
    cursor.execute('SELECT session_id, status FROM count_sessions WHERE status = "active" LIMIT 1')
    session_result = cursor.fetchone()
    
    if not session_result:
        conn.close()
        return jsonify({'error': 'Aktif sayım oturumu bulunamadı'}), 400
    
    session_id = session_result[0]
    
    # Çift işlem kontrolü - eğer bu oturum zaten tamamlandıysa
    cursor.execute('SELECT status FROM count_sessions WHERE session_id = ?', (session_id,))
    current_status = cursor.fetchone()
    if current_status and current_status[0] != 'active':
        conn.close()
        return jsonify({'error': 'Bu sayım oturumu zaten tamamlanmış'}), 400
    
    cursor.execute('UPDATE count_sessions SET status = "completed", finished_at = ? WHERE session_id = ?',
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
        WHERE i.session_id = ?
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
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, report_filename, report_title, 
          total_expected, total_scanned, accuracy_rate))
    
    conn.commit()
    conn.close()
    
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
        cursor.execute('SELECT session_id FROM count_sessions WHERE status = "active"')
        active_sessions = cursor.fetchall()
        
        if not active_sessions:
            conn.close()
            return jsonify({'success': True, 'message': 'Durdurulacak aktif sayım bulunamadı'})
        
        # Tüm aktif sayımları "stopped" olarak işaretle
        stopped_count = 0
        for session_tuple in active_sessions:
            session_id = session_tuple[0]
            cursor.execute('UPDATE count_sessions SET status = "stopped", finished_at = ? WHERE session_id = ?',
                         (datetime.now(), session_id))
            stopped_count += 1
        
        # Session'ları temizle
        session.pop('count_access', None)
        session.pop('count_authenticated', None) 
        session.pop('current_session', None)
        
        conn.commit()
        conn.close()
        
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
        conn.close()
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
    conn.close()
    
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
    cursor.execute('SELECT COUNT(*) FROM count_sessions WHERE status = "active"')
    active_session = cursor.fetchone()[0]
    
    if active_session > 0:
        conn.close()
        return jsonify({'error': 'Aktif bir sayım oturumu var. QR kodları silinemez.'}), 400
    
    try:
        # QR kodlarını ve parçaları sil
        cursor.execute('DELETE FROM qr_codes')
        cursor.execute('DELETE FROM parts')
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Tüm QR kodları başarıyla silindi'
        })
    except Exception as e:
        conn.close()
        return jsonify({'error': f'QR kodları silinirken hata: {str(e)}'}), 500

@app.route('/get_reports')
@login_required
def get_reports():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT cr.id, cr.session_id, cr.file_path, cr.report_name, 
               cr.created_at, cr.total_expected, cr.total_scanned, cr.accuracy_rate,
               u.full_name as created_by_name
        FROM count_reports cr
        LEFT JOIN users u ON cr.id = u.id
        ORDER BY cr.created_at DESC
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
            'total_difference': row[7],
            'created_by': row[8] or 'Bilinmeyen'
        })
    
    conn.close()
    return jsonify(reports)

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
    
    conn.close()
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
    
    conn.close()
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
    cursor.execute('SELECT COUNT(*) FROM count_sessions WHERE status = "active"')
    active_counts = cursor.fetchone()[0]
    
    # Tamamlanan sayımlar
    cursor.execute('SELECT COUNT(*) FROM count_sessions WHERE status = "completed"')
    completed_counts = cursor.fetchone()[0]
    
    # Son sayım bilgisi
    cursor.execute('''
        SELECT started_at FROM count_sessions 
        WHERE status = "completed" 
        ORDER BY started_at DESC LIMIT 1
    ''')
    last_count = cursor.fetchone()
    last_count_date = last_count[0] if last_count else None
    
    conn.close()
    
    stats = {
        'total_qr_codes': total_qr_codes,
        'total_reports': total_reports,
        'active_counts': active_counts,
        'completed_counts': completed_counts,
        'last_count_date': last_count_date
    }
    print(f"DEBUG: Gönderilen stats: {stats}")  # DEBUG
    return jsonify(stats)

if __name__ == '__main__':
    # Initialize database on startup
    try:
        init_db()
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
    
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)
