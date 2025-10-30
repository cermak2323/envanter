#!/usr/bin/env python
"""
CEMMAKSERVİS - Gerçek Schema Kontrol
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
        print("\n" + "=" * 120)
        print("� CEMMAKSERVİS - USERS TABLOSU SCHEMA")
        print("=" * 120 + "\n")
        
        # Önce kolon adlarını al
        query_cols = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        columns = db.session.execute(query_cols).fetchall()
        
        print(f"Toplam Kolon: {len(columns)}\n")
        print("Kolon Listesi:")
        print("-" * 120)
        
        col_names = []
        for col_name, data_type, is_nullable in columns:
            col_names.append(col_name)
            nullable = "✅ NULL" if is_nullable == 'YES' else "❌ NOT NULL"
            print(f"  {col_name:20} | {data_type:20} | {nullable}")
        
        print("\n" + "=" * 120)
        print("🔐 TÜM KULLANICILAR (CEMMAKSERVİS)")
        print("=" * 120 + "\n")
        
        # Dinamik olarak tüm kolonları çek
        columns_str = ", ".join(col_names)
        query = text(f"SELECT {columns_str} FROM users ORDER BY id")
        # Dinamik olarak tüm kolonları çek
        columns_str = ", ".join(col_names)
        query = text(f"SELECT {columns_str} FROM users ORDER BY id")
        
        result = db.session.execute(query)
        users = result.fetchall()
        
        if not users:
            print("❌ Kullanıcı bulunamadı!")
        else:
            print(f"✅ Toplam Kullanıcı: {len(users)}\n")
            
            for idx, user in enumerate(users, 1):
                print(f"{idx}. KULLANICI")
                print("   " + "-" * 110)
                
                for col_idx, col_name in enumerate(col_names):
                    value = user[col_idx]
                    
                    # Uzun değerleri kırp
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    
                    print(f"   {col_name:20} : {value}")
                
                print()
        
        # İstatistikler
        print("\n" + "=" * 120)
        print("📊 İSTATİSTİKLER")
        print("=" * 120 + "\n")
        
        stats_query = text("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT id) as unique_ids,
                COUNT(DISTINCT username) as unique_usernames
            FROM users
        """)
        
        total, unique_ids, unique_usernames = db.session.execute(stats_query).fetchone()
        
        print(f"  Toplam Kayıt:        {total}")
        print(f"  Benzersiz ID:        {unique_ids}")
        print(f"  Benzersiz Username:  {unique_usernames}")
        
        # Şifre raporu
        print("\n" + "-" * 120)
        print("🔑 ŞİFRE DURUM RAPORU")
        print("-" * 120 + "\n")
        
        pwd_query = text("""
            SELECT username, password, password_hash
            FROM users
            ORDER BY id
        """)
        
        pwd_results = db.session.execute(pwd_query).fetchall()
        
        for username, password, password_hash in pwd_results:
            pwd_display = password if password else "(None)"
            hash_display = password_hash[:40] + "..." if password_hash else "(None)"
            print(f"  Username: {username:20} | Password: {pwd_display:30} | Hash: {hash_display}")
        
        print("\n" + "=" * 120)
        print("✅ KONTROL TAMAMLANDI")
        print("=" * 120 + "\n")
        
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
