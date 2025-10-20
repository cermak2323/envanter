from flask import Flask, render_template, request, jsonify, send_file, session
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import sqlite3
import pandas as pd
import qrcode
from io import BytesIO
import base64
import os
import uuid
from datetime import datetime
import zipfile
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
socketio = SocketIO(app, cors_allowed_origins="*")

DATABASE = 'inventory.db'
REPORTS_DIR = 'reports'

os.makedirs(REPORTS_DIR, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_code TEXT NOT NULL,
            part_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qr_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_id TEXT UNIQUE NOT NULL,
            part_code TEXT NOT NULL,
            part_name TEXT NOT NULL,
            is_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS count_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'active',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            part_code TEXT NOT NULL,
            part_name TEXT NOT NULL,
            expected_quantity INTEGER NOT NULL,
            FOREIGN KEY (session_id) REFERENCES count_sessions(session_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scanned_qr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            qr_id TEXT NOT NULL,
            part_code TEXT NOT NULL,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES count_sessions(session_id)
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_parts', methods=['POST'])
def upload_parts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM count_sessions WHERE status = "active"')
    active_session = cursor.fetchone()
    conn.close()
    
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
def get_qr_codes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT qr_id, part_code, part_name, is_used FROM qr_codes ORDER BY part_code, qr_id')
    qr_codes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(qr_codes)

@app.route('/generate_qr_image/<qr_id>')
def generate_qr_image(qr_id):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    return send_file(buf, mimetype='image/png')

@app.route('/download_all_qr')
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

@app.route('/start_count', methods=['POST'])
def start_count():
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
            
            cursor.execute('INSERT INTO inventory_data (session_id, part_code, part_name, expected_quantity) VALUES (?, ?, ?, ?)',
                         (session_id, part_code, part_name, quantity))
        
        conn.commit()
        conn.close()
        
        session['current_session'] = session_id
        
        socketio.emit('count_started', {'session_id': session_id}, broadcast=True)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Sayım başlatıldı'
        })
    
    except Exception as e:
        return jsonify({'error': f'Hata: {str(e)}'}), 500

@app.route('/get_count_status')
def get_count_status():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT session_id, status FROM count_sessions WHERE status = "active" LIMIT 1')
    session = cursor.fetchone()
    conn.close()
    
    if session:
        return jsonify({
            'active': True,
            'session_id': session[0]
        })
    else:
        return jsonify({'active': False})

@socketio.on('scan_qr')
def handle_scan(data):
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
    
    cursor.execute('INSERT INTO scanned_qr (session_id, qr_id, part_code) VALUES (?, ?, ?)',
                 (session_id, qr_id, part_code))
    
    conn.commit()
    conn.close()
    
    emit('scan_result', {
        'success': True,
        'message': f'{part_name} ({part_code}) sayıldı',
        'part_code': part_code,
        'part_name': part_name
    }, broadcast=True)

@app.route('/finish_count', methods=['POST'])
def finish_count():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT session_id FROM count_sessions WHERE status = "active" LIMIT 1')
    session_result = cursor.fetchone()
    
    if not session_result:
        conn.close()
        return jsonify({'error': 'Aktif sayım oturumu bulunamadı'}), 400
    
    session_id = session_result[0]
    
    cursor.execute('UPDATE count_sessions SET status = "completed", finished_at = ? WHERE session_id = ?',
                 (datetime.now(), session_id))
    
    cursor.execute('''
        SELECT 
            i.part_code,
            i.part_name,
            i.expected_quantity as envanter,
            COUNT(s.qr_id) as sayim
        FROM inventory_data i
        LEFT JOIN scanned_qr s ON i.part_code = s.part_code AND i.session_id = s.session_id
        WHERE i.session_id = ?
        GROUP BY i.part_code, i.part_name, i.expected_quantity
    ''', (session_id,))
    
    results = cursor.fetchall()
    
    report_data = []
    for row in results:
        report_data.append({
            'Parça Kodu': row[0],
            'Parça Adı': row[1],
            'Envanter Adeti': row[2],
            'Sayım Adeti': row[3],
            'Fark': row[3] - row[2]
        })
    
    df = pd.DataFrame(report_data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sayım Raporu')
    output.seek(0)
    
    report_filename = f'sayim_raporu_{session_id[:8]}.xlsx'
    report_path = os.path.join(REPORTS_DIR, report_filename)
    
    with open(report_path, 'wb') as f:
        f.write(output.getvalue())
    
    conn.commit()
    conn.close()
    
    socketio.emit('count_finished', {'session_id': session_id}, broadcast=True)
    
    return jsonify({
        'success': True,
        'message': 'Sayım tamamlandı',
        'report_file': report_filename
    })

@app.route('/download_report/<filename>')
def download_report(filename):
    if not re.match(r'^sayim_raporu_[a-f0-9]{8}\.xlsx$', filename):
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

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
