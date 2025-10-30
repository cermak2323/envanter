#!/usr/bin/env python
"""
USERS TABLOSU - Login olan tüm hesapları kontrol et
CEMMAKSERVİS sistemine doğrudan giriş yapan kullanıcılar
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

import os
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('RENDER_INTERNAL_DATABASE_URL') or \
    "postgresql://cermak_envanter_user:N22HyFcRf3bvgMzkK1J5yNYgrXEfIgNC@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter?sslmode=require"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    try:
        print("\n" + "=" * 130)
        print("🔑 USERS TABLOSU - SİSTEME DOĞRUDAN GİRİŞ YAPAN KULLANIÇILAR")
        print("=" * 130 + "\n")
        
        # Tüm kolonları al
        query_cols = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        columns = db.session.execute(query_cols).fetchall()
        col_names = [col[0] for col in columns]
        
        print(f"Tablo: users")
        print(f"Toplam Kolon: {len(col_names)}\n")
        
        # Tüm kullanıcıları çek
        columns_str = ", ".join(col_names)
        query = text(f"SELECT {columns_str} FROM users ORDER BY id")
        
        result = db.session.execute(query)
        users = result.fetchall()
        
        print(f"🔴 BULUNDU: {len(users)} KULLANIÇI\n")
        print("=" * 130 + "\n")
        
        if len(users) < 10:
            print(f"⚠️  SİSTEMDE {len(users)} KULLANIÇI VAR (10 değil!)\n")
        else:
            print(f"✅ {len(users)} KULLANIÇI BULUNDU!\n")
        
        for idx, user in enumerate(users, 1):
            print(f"{idx}. KULLANIÇI")
            print("   " + "-" * 125)
            
            for col_idx, col_name in enumerate(col_names):
                value = user[col_idx]
                
                # Uzun değerleri kırp
                if isinstance(value, str) and len(value) > 60:
                    value = value[:60] + "..."
                
                # Önemli alanları highlight et
                if col_name in ['id', 'username', 'password', 'password_hash', 'full_name', 'email', 'role', 'created_at', 'last_login']:
                    print(f"   ⭐ {col_name:25} : {value}")
                else:
                    if value is not None and value != False and value != 0:
                        print(f"      {col_name:25} : {value}")
            
            print()
        
        # İstatistikler
        print("\n" + "=" * 130)
        print("📊 İSTATİSTİKLER")
        print("=" * 130 + "\n")
        
        # Username vs Full_name kontrolü
        print("Kullanıcı Listesi (Basit):")
        print("-" * 130)
        
        for user in users:
            user_id = user[0]  # id
            username = user[1]  # username
            full_name = user[4]  # full_name
            created_at = user[6]  # created_at
            
            print(f"  ID: {user_id:3} | Username: {username:25} | Full Name: {full_name:30} | Created: {created_at}")
        
        # Tarih analizi
        print("\n\n" + "=" * 130)
        print("📅 OLUŞTURULMA TARİHLERİ (Creation Timeline)")
        print("=" * 130 + "\n")
        
        query_dates = text("""
            SELECT id, username, full_name, created_at, last_login
            FROM users
            ORDER BY created_at ASC
        """)
        
        dated_users = db.session.execute(query_dates).fetchall()
        
        for user_id, username, full_name, created_at, last_login in dated_users:
            last_login_str = str(last_login) if last_login else "Hiç giriş yok"
            print(f"  {created_at} | {username:20} | Login: {last_login_str}")
        
        print("\n" + "=" * 130)
        print(f"✅ TOPLAM: {len(users)} kullanıcı")
        print("=" * 130 + "\n")
        
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
