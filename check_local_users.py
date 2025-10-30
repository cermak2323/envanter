#!/usr/bin/env python
"""
LOCAL SQLite Veritabanında Kullanıcıları Kontrol Et
"""

import sqlite3
import os

db_path = "instance/envanter_local.db"

if not os.path.exists(db_path):
    print(f"❌ Veritabanı bulunamadı: {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "=" * 120)
    print("📱 LOCAL SQLite VERITABANINDA KULLANICILAR")
    print("=" * 120 + "\n")
    
    # Tüm tabloları listele
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("Mevcut Tablolar:")
    print("-" * 60)
    for table in tables:
        print(f"  • {table[0]}")
    
    # users tablosu var mı kontrol et
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cursor.fetchone():
        print("\n✅ 'users' tablosu bulundu\n")
        
        # Kolon adlarını al
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        print("Kolon Listesi:")
        print("-" * 120)
        for col in columns:
            print(f"  {col[1]:20} | {col[2]:20} | {'NOT NULL' if col[3] else 'NULL'}")
        
        # Kullanıcıları listele
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        
        print(f"\n\n✅ Toplam Kullanıcı (users): {len(users)}\n")
        
        if users:
            col_names = [col[0] for col in cursor.description]
            for idx, user in enumerate(users, 1):
                print(f"{idx}. KULLANICI")
                print("   " + "-" * 110)
                for col_idx, col_name in enumerate(col_names):
                    value = user[col_idx]
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"   {col_name:20} : {value}")
                print()
    else:
        print("\n❌ 'users' tablosu BULUNAMADI\n")
    
    # envanter_users tablosu var mı kontrol et
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='envanter_users'")
    if cursor.fetchone():
        print("\n" + "=" * 120)
        print("📱 ENVANTER_USERS TABLOSU")
        print("=" * 120 + "\n")
        
        cursor.execute("SELECT * FROM envanter_users")
        users = cursor.fetchall()
        
        print(f"✅ Toplam Kullanıcı (envanter_users): {len(users)}\n")
        
        if users:
            col_names = [col[0] for col in cursor.description]
            for idx, user in enumerate(users, 1):
                print(f"{idx}. KULLANICI")
                print("   " + "-" * 110)
                for col_idx, col_name in enumerate(col_names):
                    value = user[col_idx]
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"   {col_name:20} : {value}")
                print()
    else:
        print("\n❌ 'envanter_users' tablosu BULUNAMADI\n")
    
    # İstatistikler
    print("\n" + "=" * 120)
    print("📊 İSTATİSTİKLER")
    print("=" * 120 + "\n")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM envanter_users")
    envanter_count = cursor.fetchone()[0]
    
    print(f"  users tablosu:        {users_count} kullanıcı")
    print(f"  envanter_users tablosu: {envanter_count} kullanıcı")
    
    print("\n" + "=" * 120)
    print("✅ KONTROL TAMAMLANDI")
    print("=" * 120 + "\n")
    
    conn.close()
    
except Exception as e:
    print(f"\n❌ Hata: {e}")
    import traceback
    traceback.print_exc()
