#!/usr/bin/env python
"""
ÖZEL KONTROL: inventory_users tablosu - 9 kullanıcı burada olabilir!
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

DATABASE_URL = "postgresql://cermak_user:XPNP4Yt8dsWdKaaxNlQOzIiRJjWoTrfC@dpg-d2m6l5ripnbc738v4b0g-a.oregon-postgres.render.com:5432/cermak?sslmode=require"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    try:
        print("\n" + "=" * 130)
        print("🔍 ÖNEMLİ BULGU: inventory_users TABLOSU - 9 KULLANICINIZ BURDA!")
        print("=" * 130 + "\n")
        
        # 1. Kolon adlarını al
        query_cols = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'inventory_users'
            ORDER BY ordinal_position
        """)
        
        columns = db.session.execute(query_cols).fetchall()
        col_names = [col[0] for col in columns]
        
        print(f"Toplam Kolon: {len(col_names)}\n")
        print("Kolon Listesi:")
        print("-" * 130)
        for i, col_name in enumerate(col_names, 1):
            print(f"  {i:2}. {col_name}")
        
        # 2. Tüm kullanıcıları al
        print("\n\n" + "=" * 130)
        print("👥 INVENTORY_USERS - TÜM KULLANIÇILAR (9)")
        print("=" * 130 + "\n")
        
        columns_str = ", ".join(col_names)
        query = text(f"SELECT {columns_str} FROM inventory_users ORDER BY id")
        
        result = db.session.execute(query)
        users = result.fetchall()
        
        print(f"✅ Toplam Kullanıcı: {len(users)}\n")
        
        for idx, user in enumerate(users, 1):
            print(f"{idx}. KULLANICI")
            print("   " + "-" * 125)
            
            for col_idx, col_name in enumerate(col_names):
                value = user[col_idx]
                
                # Uzun değerleri kırp
                if isinstance(value, str) and len(value) > 60:
                    value = value[:60] + "..."
                
                # Önemli alanları highlight et
                if col_name in ['id', 'username', 'password', 'password_hash', 'full_name', 'email', 'role']:
                    print(f"   ⭐ {col_name:25} : {value}")
                else:
                    if value is not None:
                        print(f"      {col_name:25} : {value}")
            
            print()
        
        # 3. Özet
        print("\n" + "=" * 130)
        print("📊 ÖZET")
        print("=" * 130 + "\n")
        
        # Unique usernames
        query_usernames = text("SELECT COUNT(DISTINCT username) FROM inventory_users")
        unique_users = db.session.execute(query_usernames).scalar()
        
        # Roles
        query_roles = text("SELECT role, COUNT(*) FROM inventory_users GROUP BY role")
        roles = db.session.execute(query_roles).fetchall()
        
        print(f"  Toplam Kayıt:        {len(users)}")
        print(f"  Benzersiz Username:  {unique_users}")
        print()
        print("  Role Dağılımı:")
        for role, count in roles:
            print(f"    • {role}: {count}")
        
        # 4. Kullanıcıları users tablosuna taşıma planı
        print("\n" + "=" * 130)
        print("🚀 TAŞIMA PLANI - inventory_users → users")
        print("=" * 130 + "\n")
        
        print("""
SQL KOMUTU (Render.com pgAdmin4'te çalıştır):

-- 1. Yeni kullanıcıları users tablosuna ekle
INSERT INTO users (
    id, username, password, password_hash, full_name, role, email,
    job_title, is_active_user, created_at, updated_at
)
SELECT 
    id, username, password, password_hash, full_name, COALESCE(role, 'user'),
    email, job_title, is_active_user, created_at, updated_at
FROM inventory_users
WHERE id NOT IN (SELECT id FROM users)
ON CONFLICT (id) DO NOTHING;

-- 2. Kontrol
SELECT COUNT(*) FROM users;  -- 11 olmalı (2 + 9)
SELECT * FROM users ORDER BY id;

-- 3. inventory_users 'i yedekle (backup)
CREATE TABLE inventory_users_backup AS SELECT * FROM inventory_users;
""")
        
        print("\n" + "=" * 130)
        print("✅ ANALİZ TAMAMLANDI")
        print("=" * 130 + "\n")
        
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
