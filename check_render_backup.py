#!/usr/bin/env python
"""
Render.com PostgreSQL - Tüm Veritabanlarını Kontrol Et ve Restore Seçeneklerini Göster
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import datetime

import os
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('RENDER_INTERNAL_DATABASE_URL') or \
    "postgresql://cermak_envanter_user:N22HyFcRf3bvgMzkK1J5yNYgrXEfIgNC@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter?sslmode=require"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    try:
        print("\n" + "=" * 120)
        print("💾 RENDER.COM PostgreSQL - RECOVERY VE BACKUP ANALİZİ")
        print("=" * 120 + "\n")
        
        # 1. Veritabanı Bilgileri
        print("1️⃣  VERİTABANI BİLGİLERİ")
        print("-" * 120)
        
        query = text("""
            SELECT 
                datname
            FROM pg_database
            WHERE datname NOT IN ('template0', 'template1', 'postgres')
            ORDER BY datname
        """)
        
        dbs = db.session.execute(query).fetchall()
        
        for datname, in dbs:
            print(f"  📦 {datname}")
        print()
        
        # 2. Users tablosu - Tüm Veriler
        print("\n2️⃣  USERS TABLOSU - FULL BACKUP")
        print("-" * 120)
        
        query_users = text("""
            SELECT 
                id, username, password, password_hash, full_name, role,
                created_at, real_name, email, job_title, is_active_user
            FROM users
            ORDER BY id
        """)
        
        users = db.session.execute(query_users).fetchall()
        
        print(f"✅ Toplam Kayıt: {len(users)}\n")
        
        if users:
            # CSV formatında kaydet
            csv_content = "id,username,password,password_hash,full_name,role,created_at,real_name,email,job_title,is_active_user\n"
            
            for user_id, username, password, password_hash, full_name, role, created_at, real_name, email, job_title, is_active in users:
                csv_content += f'{user_id},"{username}","{password}","{password_hash}","{full_name}","{role}","{created_at}","{real_name}","{email}","{job_title}",{is_active}\n'
                
                print(f"  ID: {user_id}")
                print(f"    • Username: {username}")
                print(f"    • Password: {password}")
                print(f"    • Full Name: {full_name}")
                print(f"    • Role: {role}")
                print()
            
            # CSV'yi kaydet
            with open("users_backup.csv", "w", encoding="utf-8") as f:
                f.write(csv_content)
            print(f"✅ CSV Backup kaydedildi: users_backup.csv\n")
        
        # 3. Tüm Tabloların İçeriği
        print("\n3️⃣  TÜM TABLOLARIN SAYILARI")
        print("-" * 120)
        
        query_tables = text("""
            SELECT 
                schemaname,
                tablename,
                (SELECT COUNT(*) FROM information_schema.columns 
                 WHERE table_schema = schemaname AND table_name = tablename) as column_count
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        
        tables = db.session.execute(query_tables).fetchall()
        
        for schema, tablename, col_count in tables:
            count_query = text(f"SELECT COUNT(*) FROM {tablename}")
            row_count = db.session.execute(count_query).scalar()
            
            print(f"  📋 {tablename:20} | Kolonlar: {col_count:3} | Satırlar: {row_count:5}")
        
        # 4. Tarih Bilgileri
        print("\n4️⃣  VERİ OLUŞTURULMA TARİHLERİ")
        print("-" * 120)
        
        query_dates = text("""
            SELECT 
                tablename,
                (SELECT MIN(created_at) FROM users LIMIT 1) as first_user_created,
                (SELECT MAX(updated_at) FROM users LIMIT 1) as last_user_update,
                (SELECT COUNT(*) FROM users) as total_users
            FROM pg_tables
            WHERE tablename = 'users'
        """)
        
        date_info = db.session.execute(query_dates).fetchone()
        if date_info:
            print(f"  İlk Kullanıcı Tarihi: {date_info[1]}")
            print(f"  Son Güncelleme: {date_info[2]}")
            print(f"  Toplam Kullanıcı: {date_info[3]}")
        
        # 5. RESTORE SEÇENEKLERI
        print("\n" + "=" * 120)
        print("🔧 RESTORE VE RECOVERY SEÇENEKLERİ")
        print("=" * 120 + "\n")
        
        print("❌ PROBLEM: Production'da sadece 2 kullanıcı var (admin, test1)")
        print("   Diğer ~8 kullanıcı nerede?")
        print()
        print("✅ ÇÖZÜM ADAYLARI:")
        print()
        print("1. Render.com BACKUP PORTAL'dan eski backup'ı restore et:")
        print("   https://dashboard.render.com → PostgreSQL → Backups")
        print()
        print("2. Yerel SQLite'dan kullanıcıları import et:")
        print("   python migrate_from_sqlite.py")
        print()
        print("3. Eski kurulumlardaki verileri ara:")
        print("   SSH bağlantısı ile eski dizinleri kontrol et")
        print()
        print("4. Backup CSV'den restore et:")
        print("   COPY users FROM 'users_backup.csv' WITH CSV HEADER;")
        print()
        
        # 6. Suggest Commands
        print("\n" + "=" * 120)
        print("📝 TAVSIYE EDILEN KOMUTLAR")
        print("=" * 120 + "\n")
        
        print("# 1. PostgreSQL Dump Al (Production'dan)")
        print("""
    pg_dump postgresql://<DB_USER>:<DB_PASSWORD>@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter > cermak_backup.sql
""")
        
        print("\n# 2. Specific Users'ı Al")
        print("""
    psql postgresql://<DB_USER>:<DB_PASSWORD>@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter -c "\\copy (SELECT * FROM users) TO users_full_backup.csv WITH CSV HEADER"
""")
        
        print("\n# 3. Restore Öncesi Kontrol")
        print("""
    psql postgresql://<DB_USER>:<DB_PASSWORD>@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter -c "SELECT * FROM users"
""")
        
        print("\n" + "=" * 120)
        print("✅ ANALİZ TAMAMLANDI")
        print("=" * 120 + "\n")
        
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
