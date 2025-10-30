#!/usr/bin/env python
"""
USERS TABLOSU - Silinmiş veya pasif (deleted) kullanıcıları ara
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
        print("🔍 USERS TABLOSU - KAYIP KULLANIÇILARI ARA (Silinmiş/Pasif/Arşiv)")
        print("=" * 130 + "\n")
        
        # Kolon adlarını kontrol et
        query_cols = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        columns = db.session.execute(query_cols).fetchall()
        col_names = [col[0] for col in columns]
        
        print(f"Mevcut Kolonlar ({len(col_names)}):")
        for i, col in enumerate(col_names, 1):
            print(f"  {i:2}. {col}")
        
        # Silinmiş veya pasif kullanıcıları ara
        print("\n" + "=" * 130)
        print("🔍 ARAŞTIRMA 1: is_active_user = false (Pasif Kullanıcılar)")
        print("=" * 130 + "\n")
        
        query_inactive = text("""
            SELECT id, username, full_name, role, is_active_user, created_at, updated_at
            FROM users
            WHERE is_active_user = false
            ORDER BY id
        """)
        
        inactive = db.session.execute(query_inactive).fetchall()
        print(f"Pasif kullanıcı: {len(inactive)}")
        for row in inactive:
            print(f"  {row}")
        
        # is_deleted kontrolü varsa
        print("\n" + "=" * 130)
        print("🔍 ARAŞTIRMA 2: is_deleted = true (Silinmiş Kullanıcılar)")
        print("=" * 130 + "\n")
        
        if 'is_deleted' in col_names:
            query_deleted = text("""
                SELECT id, username, full_name, role, is_deleted, deleted_at, created_at
                FROM users
                WHERE is_deleted = true
                ORDER BY id
            """)
            
            deleted = db.session.execute(query_deleted).fetchall()
            print(f"Silinmiş kullanıcı: {len(deleted)}")
            for row in deleted:
                print(f"  {row}")
        else:
            print("is_deleted kolonu YOK!")
        
        # Tüm ID'leri kontrol et
        print("\n" + "=" * 130)
        print("🔍 ARAŞTIRMA 3: TÜMLÜ USERS TABLOSU (Active + Inactive + Deleted)")
        print("=" * 130 + "\n")
        
        query_all = text("""
            SELECT id, username, full_name, role, created_at
            FROM users
            ORDER BY id
        """)
        
        all_users = db.session.execute(query_all).fetchall()
        print(f"TÜMLÜ Kullanıcı: {len(all_users)}")
        for row in all_users:
            print(f"  {row}")
        
        # Maksimum ID'yi kontrol et
        print("\n" + "=" * 130)
        print("🔍 ARAŞTIRMA 4: ID ANALIZI")
        print("=" * 130 + "\n")
        
        query_id_stats = text("""
            SELECT 
                COUNT(*) as total_count,
                MIN(id) as min_id,
                MAX(id) as max_id,
                COUNT(DISTINCT id) as distinct_ids
            FROM users
        """)
        
        stats = db.session.execute(query_id_stats).fetchone()
        total, min_id, max_id, distinct_ids = stats
        
        print(f"Toplam Kullanıcı: {total}")
        print(f"Min ID: {min_id}")
        print(f"Max ID: {max_id}")
        print(f"Benzersiz ID: {distinct_ids}")
        print(f"Eksik kayıt: {(max_id - min_id + 1) - distinct_ids} (ID boşlukları)")
        
        # Boşlukları bul
        print("\n" + "-" * 130)
        print("ID Boşluklarını Kontrol Et:")
        print("-" * 130 + "\n")
        
        query_all_ids = text("SELECT id FROM users ORDER BY id")
        ids = [row[0] for row in db.session.execute(query_all_ids).fetchall()]
        
        missing_ids = []
        for i in range(min_id, max_id + 1):
            if i not in ids:
                missing_ids.append(i)
        
        if missing_ids:
            print(f"⚠️  KAYIP ID'LER: {missing_ids}")
            print(f"   {len(missing_ids)} tane kayıt SİLİNMİŞ olabilir!")
        else:
            print(f"✅ Hiçbir ID boşluğu yok")
        
        # Tabloyu structure'ını göster
        print("\n" + "=" * 130)
        print("📋 USERS TABLOSU - KOLON DETAYLARı")
        print("=" * 130 + "\n")
        
        query_structure = text("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        structure = db.session.execute(query_structure).fetchall()
        for col_name, data_type, is_nullable, col_default in structure:
            nullable = "NULL" if is_nullable == 'YES' else "NOT NULL"
            default = f" DEFAULT {col_default}" if col_default else ""
            print(f"  {col_name:25} | {data_type:20} | {nullable}{default}")
        
        print("\n" + "=" * 130)
        print("✅ ARAŞTIRMA TAMAMLANDI")
        print("=" * 130 + "\n")
        
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
