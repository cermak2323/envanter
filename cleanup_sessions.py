#!/usr/bin/env python3
"""
Tüm açık count session'ları temizle
"""
import os
import psycopg2
from dotenv import load_dotenv

# .env.production'dan konfigürasyonu yükle
load_dotenv('.env.production')

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env.production")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # 1. Tüm AÇIK session'ları kontrol et
    cursor.execute("""
        SELECT session_id, created_by, created_at, status 
        FROM count_sessions 
        WHERE status = 'active'
        ORDER BY created_at DESC
    """)
    
    active_sessions = cursor.fetchall()
    print(f"\n📊 AÇIK SAYIMLAR ({len(active_sessions)}):")
    print("-" * 70)
    
    for session_id, created_by, created_at, status in active_sessions:
        # İçinde kaç QR taranmış?
        cursor.execute("SELECT COUNT(*) FROM scanned_qr WHERE session_id = %s", (session_id,))
        scan_count = cursor.fetchone()[0]
        
        # Kimin tarafından oluşturulmuş?
        cursor.execute("SELECT full_name, role FROM users WHERE id = %s", (created_by,))
        user_info = cursor.fetchone()
        creator_name = user_info[0] if user_info else "UNKNOWN"
        creator_role = user_info[1] if user_info else "?"
        
        print(f"ID: {session_id[:12]}...")
        print(f"  Oluşturan: {creator_name} [{creator_role}]")
        print(f"  Başlangıç: {created_at}")
        print(f"  Taranan QR: {scan_count}")
        print()
    
    # 2. Seçim: Kapatmak mı istiyorsun?
    if active_sessions:
        print("\n⚠️  Tüm AÇIK sayımları kapatmak istiyorsun mu?")
        choice = input("ENTER=evet, CTRL+C=hayır: ")
        
        for session_id, _, _, _ in active_sessions:
            cursor.execute(
                "UPDATE count_sessions SET status = 'finished' WHERE session_id = %s",
                (session_id,)
            )
            print(f"✅ Kapatıldı: {session_id[:12]}...")
        
        conn.commit()
        print("\n✅ Tüm sayımlar kapatıldı!")
    
    # 3. Rol kontrolü - admin hesabı var mı?
    print("\n👥 KULLANICILAR VE ROLLERI:")
    print("-" * 70)
    cursor.execute("SELECT id, username, full_name, role FROM users ORDER BY role DESC, username")
    users = cursor.fetchall()
    for user_id, username, full_name, role in users:
        print(f"{role:10} | {username:15} | {full_name}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ DATABASE ERROR: {e}")
    exit(1)
