#!/usr/bin/env python3
"""
Lokal SQLite Database Initialization (GEÇİCİ)
- Bu script sadece local development için SQLite database oluşturur
- Production PostgreSQL'e hiçbir etkisi yoktur
- Tablolar, admin kullanıcıları ve temel verileri oluşturur
"""

import sqlite3
import os
from pathlib import Path
from werkzeug.security import generate_password_hash
from datetime import datetime
import secrets

def init_local_sqlite():
    """Lokal SQLite database'ini başlat"""
    
    # Instance klasörünü oluştur
    instance_dir = Path('instance')
    instance_dir.mkdir(exist_ok=True)
    
    db_path = instance_dir / 'envanter_local.db'
    
    print(f"🏠 LOCAL SQLite Database Initialization")
    print(f"📁 Database Path: {db_path}")
    print(f"⚠️  Bu işlem SADECE local development environment'ı etkiler")
    print(f"⚠️  Production PostgreSQL database etkilenmez")
    print("="*60)
    
    # Varsa eski database'i sil
    if db_path.exists():
        db_path.unlink()
        print("🗑️  Eski SQLite database silindi")
    
    # SQLite connection
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        print("\n📋 Creating tables...")
        
        # 1. Users tablosu (Normal kullanıcılar)
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                last_login TIMESTAMP
            )
        ''')
        print("✅ Users table created")
        
        # 2. Envanter Users tablosu (Envanter kullanıcıları)
        cursor.execute('''
            CREATE TABLE envanter_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                last_login TIMESTAMP
            )
        ''')
        print("✅ Envanter_users table created")
        
        # 3. Parts tablosu
        cursor.execute('''
            CREATE TABLE parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_code VARCHAR(100) UNIQUE NOT NULL,
                part_name VARCHAR(200) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(50),
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        print("✅ Parts table created")
        
        # 4. QR Codes tablosu
        cursor.execute('''
            CREATE TABLE qr_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qr_id VARCHAR(50) UNIQUE NOT NULL,
                part_code VARCHAR(100) NOT NULL,
                part_name VARCHAR(200) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(50),
                is_used BOOLEAN DEFAULT 0,
                is_downloaded BOOLEAN DEFAULT 0,
                downloaded_at TIMESTAMP,
                used_at TIMESTAMP,
                used_by VARCHAR(50),
                notes TEXT
            )
        ''')
        print("✅ QR_codes table created")
        
        # 5. Count Sessions tablosu
        cursor.execute('''
            CREATE TABLE count_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name VARCHAR(100) NOT NULL,
                session_password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(50),
                is_active BOOLEAN DEFAULT 1,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                description TEXT
            )
        ''')
        print("✅ Count_sessions table created")
        
        # 6. Count Passwords tablosu
        cursor.execute('''
            CREATE TABLE count_passwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_used BOOLEAN DEFAULT 0,
                used_at TIMESTAMP,
                used_by VARCHAR(50),
                FOREIGN KEY (session_id) REFERENCES count_sessions (id)
            )
        ''')
        print("✅ Count_passwords table created")
        
        # 7. Scanned QR tablosu
        cursor.execute('''
            CREATE TABLE scanned_qr (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qr_id VARCHAR(50) NOT NULL,
                session_id INTEGER NOT NULL,
                scanned_by VARCHAR(50),
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (session_id) REFERENCES count_sessions (id)
            )
        ''')
        print("✅ Scanned_qr table created")
        
        # 8. Count Reports tablosu
        cursor.execute('''
            CREATE TABLE count_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                report_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(50),
                FOREIGN KEY (session_id) REFERENCES count_sessions (id)
            )
        ''')
        print("✅ Count_reports table created")
        
        # 9. Inventory Data tablosu
        cursor.execute('''
            CREATE TABLE inventory_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_code VARCHAR(100) NOT NULL,
                part_name VARCHAR(200) NOT NULL,
                location VARCHAR(100),
                quantity INTEGER DEFAULT 0,
                unit VARCHAR(20),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by VARCHAR(50),
                notes TEXT
            )
        ''')
        print("✅ Inventory_data table created")
        
        print("\n🔧 Creating indexes...")
        
        # Index'ler
        cursor.execute('CREATE INDEX idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX idx_envanter_users_username ON envanter_users(username)')
        cursor.execute('CREATE INDEX idx_parts_code ON parts(part_code)')
        cursor.execute('CREATE INDEX idx_qr_codes_qr_id ON qr_codes(qr_id)')
        cursor.execute('CREATE INDEX idx_qr_codes_part_code ON qr_codes(part_code)')
        cursor.execute('CREATE INDEX idx_scanned_qr_session ON scanned_qr(session_id)')
        cursor.execute('CREATE INDEX idx_scanned_qr_qr_id ON scanned_qr(qr_id)')
        cursor.execute('CREATE INDEX idx_inventory_part_code ON inventory_data(part_code)')
        
        print("✅ All indexes created")
        
        print("\n👤 Creating admin users...")
        
        # Admin kullanıcıları oluştur
        admin_password = 'admin123'
        admin_hash = generate_password_hash(admin_password)
        
        # Users tablosuna admin ekle
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, created_at)
            VALUES (?, ?, ?, ?)
        ''', ('admin', admin_hash, 'admin', datetime.now()))
        
        # Envanter_users tablosuna admin ekle
        cursor.execute('''
            INSERT INTO envanter_users (username, password_hash, role, created_at)
            VALUES (?, ?, ?, ?)
        ''', ('admin', admin_hash, 'admin', datetime.now()))
        
        print("✅ Admin users created:")
        print(f"   📧 Username: admin")
        print(f"   🔑 Password: {admin_password}")
        
        print("\n📊 Sample data creation...")
        
        # Örnek parça ekle
        cursor.execute('''
            INSERT INTO parts (part_code, part_name, description, created_by)
            VALUES (?, ?, ?, ?)
        ''', ('SAMPLE_001', 'Test Parça', 'Local test için örnek parça', 'admin'))
        
        # Örnek QR kod ekle
        sample_qr_id = f"QR_{secrets.token_hex(4).upper()}"
        cursor.execute('''
            INSERT INTO qr_codes (qr_id, part_code, part_name, created_by)
            VALUES (?, ?, ?, ?)
        ''', (sample_qr_id, 'SAMPLE_001', 'Test Parça', 'admin'))
        
        print(f"✅ Sample data created:")
        print(f"   📦 Part: SAMPLE_001 - Test Parça")
        print(f"   🏷️  QR Code: {sample_qr_id}")
        
        # Değişiklikleri kaydet
        conn.commit()
        
        print("\n✅ LOCAL SQLite Database Successfully Initialized!")
        print(f"📁 Database file: {db_path}")
        print(f"📊 Tables: 9 tables created")
        print(f"👤 Admin users: admin/admin123")
        print(f"🏷️  Sample QR: {sample_qr_id}")
        print("\n🚀 LOCAL DEVELOPMENT READY!")
        print("="*60)
        
        # Database stats
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n📋 Database contains {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")
            
    except Exception as e:
        print(f"❌ Error creating SQLite database: {e}")
        conn.rollback()
        raise
        
    finally:
        conn.close()

if __name__ == '__main__':
    init_local_sqlite()