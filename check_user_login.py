#!/usr/bin/env python
"""
Production PostgreSQL'deki 'M.Emir ERSÜT' kullanıcısını kontrol et
Login hatası debug'ı
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Production PostgreSQL URI
DATABASE_URL = "postgresql://cermak_user:XPNP4Yt8dsWdKaaxNlQOzIiRJjWoTrfC@dpg-d2m6l5ripnbc738v4b0g-a.oregon-postgres.render.com:5432/cermak?sslmode=require"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    try:
        # 1. Tüm users'ları listele
        print("📋 USERS TABLOSUNDAKI TÜM KULLANICILAR:")
        print("=" * 80)
        query = text("""
            SELECT id, username, full_name, email, password, password_hash, role, created_at
            FROM users
            ORDER BY id
        """)
        result = db.session.execute(query)
        for row in result:
            id_val, username, full_name, email, pwd, pwd_hash, role, created = row
            print(f"ID: {id_val}")
            print(f"  username: {username!r}")
            print(f"  full_name: {full_name!r}")
            print(f"  email: {email!r}")
            print(f"  password: {pwd!r}")
            print(f"  password_hash: {pwd_hash!r}")
            print(f"  role: {role!r}")
            print(f"  created_at: {created}")
            print()
        
        # 2. 'M.Emir ERSÜT' kullanıcısını özel olarak ara
        print("\n🔍 'M.Emir ERSÜT' KULLANICISINUN ARAMA SONUÇLARI:")
        print("=" * 80)
        
        # Exact match
        query2 = text("SELECT * FROM users WHERE username = :username")
        result2 = db.session.execute(query2, {"username": "M.Emir ERSÜT"})
        rows = result2.fetchall()
        print(f"Exact match ('M.Emir ERSÜT'): {len(rows)} sonuç")
        if rows:
            for row in rows:
                print(f"  {dict(row)}")
        
        # Case-insensitive
        query3 = text("SELECT * FROM users WHERE LOWER(username) = LOWER(:username)")
        result3 = db.session.execute(query3, {"username": "M.Emir ERSÜT"})
        rows = result3.fetchall()
        print(f"Case-insensitive match: {len(rows)} sonuç")
        if rows:
            for row in rows:
                print(f"  {dict(row)}")
        
        # LIKE pattern
        query4 = text("SELECT * FROM users WHERE username LIKE :pattern")
        result4 = db.session.execute(query4, {"pattern": "%Emir%"})
        rows = result4.fetchall()
        print(f"LIKE '%Emir%' match: {len(rows)} sonuç")
        if rows:
            for row in rows:
                print(f"  {dict(row)}")
        
        # 3. SQL sorgusu örneği - pgAdmin4'te çalıştırabilirsin
        print("\n\n📝 pgAdmin4'te çalıştırılacak SQL SORGUSU:")
        print("=" * 80)
        sql = """
-- Tüm kullanıcıları listele
SELECT id, username, full_name, email, password, password_hash, role, created_at
FROM users
ORDER BY id;

-- 'M.Emir ERSÜT' kullanıcısını ara
SELECT * FROM users WHERE username = 'M.Emir ERSÜT';

-- Username'de 'Emir' geçen kullanıcıları ara
SELECT * FROM users WHERE username LIKE '%Emir%';

-- Tüm username'leri ve case varyasyonlarını listele
SELECT username, LENGTH(username) as len, md5(username) as hash
FROM users
ORDER BY username;
"""
        print(sql)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
