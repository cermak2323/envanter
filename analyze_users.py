#!/usr/bin/env python
"""
Her iki sistem'in kullanıcılarını kontrol et - Direct Comparison
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Production PostgreSQL URI - YENİ VERİTABANI
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('RENDER_INTERNAL_DATABASE_URL') or \
    "postgresql://cermak_envanter_user:N22HyFcRf3bvgMzkK1J5yNYgrXEfIgNC@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter?sslmode=require"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    try:
        print("\n" + "=" * 100)
        print("ÜYE YÖNETİMİ ANALİZ - İKİ SİSTEM KARŞILAŞTIRMASI")
        print("=" * 100)
        
        # 1. CERMAKSERVIS USERS
        print("\n1️⃣  CEMMAKSERVİS USERS TABLOSU:")
        print("-" * 100)
        query1 = text("SELECT id, username, full_name, email, role, created_at FROM users ORDER BY id")
        result1 = db.session.execute(query1)
        cermak_users = []
        for row in result1:
            user_id, username, full_name, email, role, created_at = row
            cermak_users.append({
                'id': user_id,
                'username': username,
                'full_name': full_name,
                'email': email,
                'role': role,
                'created_at': created_at
            })
            print(f"  ID: {user_id}")
            print(f"    username: {username}")
            print(f"    full_name: {full_name}")
            print(f"    email: {email}")
            print(f"    role: {role}")
            print(f"    created_at: {created_at}")
            print()
        
        # 2. ENVANTERQR ENVANTER_USERS
        print("\n2️⃣  ENVANTERQR ENVANTER_USERS TABLOSU:")
        print("-" * 100)
        query2 = text("SELECT id, username, full_name, email, role, created_at FROM envanter_users ORDER BY id")
        result2 = db.session.execute(query2)
        envanter_users = []
        for row in result2:
            user_id, username, full_name, email, role, created_at = row
            envanter_users.append({
                'id': user_id,
                'username': username,
                'full_name': full_name,
                'email': email,
                'role': role,
                'created_at': created_at
            })
            print(f"  ID: {user_id}")
            print(f"    username: {username}")
            print(f"    full_name: {full_name}")
            print(f"    email: {email}")
            print(f"    role: {role}")
            print(f"    created_at: {created_at}")
            print()
        
        # 3. İSTATİSTİKLER
        print("\n3️⃣  İSTATİSTİKLER:")
        print("-" * 100)
        print(f"  CEMMAKSERVİS users tablosu:")
        print(f"    • Toplam üye: {len(cermak_users)}")
        print(f"    • Admin sayısı: {sum(1 for u in cermak_users if u['role'] == 'admin')}")
        print(f"    • Diğer roller: {len(cermak_users) - sum(1 for u in cermak_users if u['role'] == 'admin')}")
        
        print(f"\n  ENVANTERQR envanter_users tablosu:")
        print(f"    • Toplam üye: {len(envanter_users)}")
        print(f"    • Admin sayısı: {sum(1 for u in envanter_users if u['role'] == 'admin')}")
        print(f"    • Diğer roller: {len(envanter_users) - sum(1 for u in envanter_users if u['role'] == 'admin')}")
        
        # 4. KARŞILAŞTIRMA
        print("\n4️⃣  TABLO KARŞILAŞTIRMASI:")
        print("-" * 100)
        
        cermak_ids = {u['id'] for u in cermak_users}
        envanter_ids = {u['id'] for u in envanter_users}
        
        same_ids = cermak_ids & envanter_ids
        only_cermak = cermak_ids - envanter_ids
        only_envanter = envanter_ids - cermak_ids
        
        print(f"  • Her iki tablo'da aynı ID: {len(same_ids)} ({same_ids})")
        print(f"  • Sadece CERMAKSERVIS'te: {len(only_cermak)} ({only_cermak})")
        print(f"  • Sadece ENVANTERQR'da: {len(only_envanter)} ({only_envanter})")
        
        if same_ids:
            print(f"\n  Aynı ID'deki kullanıcılar:")
            for user_id in sorted(same_ids):
                c_user = next(u for u in cermak_users if u['id'] == user_id)
                e_user = next(u for u in envanter_users if u['id'] == user_id)
                print(f"    ID {user_id}:")
                print(f"      CERMAKSERVIS: {c_user['username']} ({c_user['full_name']})")
                print(f"      ENVANTERQR:   {e_user['username']} ({e_user['full_name']})")
                if c_user['username'] == e_user['username']:
                    print(f"      ✅ SAME USERNAME (Migrated)")
                else:
                    print(f"      ⚠️  DIFFERENT USERNAMES")
        
        # 5. KOLON KARŞILAŞTIRMASı
        print("\n5️⃣  KOLON SAYILARI:")
        print("-" * 100)
        query_cols1 = text("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'users'
        """)
        query_cols2 = text("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'envanter_users'
        """)
        
        users_cols = db.session.execute(query_cols1).scalar()
        envanter_cols = db.session.execute(query_cols2).scalar()
        
        print(f"  • users (cermakservis): {users_cols} kolon")
        print(f"  • envanter_users (envanterqr): {envanter_cols} kolon")
        
        # 6. ÖZEL KONTROL - test1 kullanıcısı
        print("\n6️⃣  ÖZEL KONTROL - test1 KULLANICISI:")
        print("-" * 100)
        
        query_test1_cerm = text("SELECT * FROM users WHERE username = 'test1'")
        test1_cerm = db.session.execute(query_test1_cerm).first()
        
        query_test1_env = text("SELECT * FROM envanter_users WHERE username = 'test1'")
        test1_env = db.session.execute(query_test1_env).first()
        
        if test1_cerm:
            print(f"  ✅ test1 CEMMAKSERVİS'te bulundu:")
            print(f"     ID: {test1_cerm[0]}, Username: {test1_cerm[1]}")
        else:
            print(f"  ❌ test1 CEMMAKSERVİS'te BULUNAMADI")
        
        if test1_env:
            print(f"  ✅ test1 ENVANTERQR'da bulundu:")
            print(f"     ID: {test1_env[0]}, Username: {test1_env[1]}")
        else:
            print(f"  ❌ test1 ENVANTERQR'da BULUNAMADI")
        
        # 7. FOREIGN KEY KONTROL
        print("\n7️⃣  FOREIGN KEY REFERANSLARI:")
        print("-" * 100)
        
        fk_query = text("""
            SELECT 
                kcu.table_name,
                kcu.column_name,
                ccu.table_name as referenced_table
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND ccu.table_name IN ('users', 'envanter_users')
        """)
        
        fk_results = db.session.execute(fk_query).fetchall()
        if fk_results:
            for row in fk_results:
                table_name, column_name, ref_table = row
                print(f"  • {table_name}.{column_name} → {ref_table}")
        else:
            print(f"  • FK referansları kontrol edildi")
        
        print("\n" + "=" * 100)
        print("✅ ANALİZ TAMAMLANDI")
        print("=" * 100 + "\n")
        
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
