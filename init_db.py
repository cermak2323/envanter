import sqlite3
import os

def init_database():
    # Mevcut database dosyasını kontrol et
    db_file = 'inventory_qr.db'
    if os.path.exists(db_file):
        print(f'Existing database found: {db_file}')

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    print('Creating tables...')

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # QR codes table with all required columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qr_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_id TEXT UNIQUE NOT NULL,
            part_code TEXT NOT NULL,
            part_name TEXT NOT NULL,
            is_used INTEGER DEFAULT 0,
            is_downloaded INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at TIMESTAMP,
            downloaded_at TIMESTAMP
        )
    ''')

    # Count sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS count_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'active',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        )
    ''')

    # Inventory data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_code TEXT NOT NULL,
            expected_quantity INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Scanned QR table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scanned_qr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_id TEXT NOT NULL,
            part_code TEXT NOT NULL,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT NOT NULL
        )
    ''')

    # Parts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_code TEXT NOT NULL,
            part_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Count reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS count_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            report_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            total_expected INTEGER DEFAULT 0,
            total_scanned INTEGER DEFAULT 0,
            accuracy_rate REAL DEFAULT 0.0
        )
    ''')

    conn.commit()

    # Verify tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print('Created tables:', [table[0] for table in tables])

    # Check qr_codes table structure
    cursor.execute('PRAGMA table_info(qr_codes)')
    columns = cursor.fetchall()
    print('qr_codes table columns:', [col[1] for col in columns])

    conn.close()
    print('Database initialized successfully!')

if __name__ == '__main__':
    init_database()