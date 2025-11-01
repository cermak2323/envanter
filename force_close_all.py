#!/usr/bin/env python3
"""
FORCE: Tüm açık sayımları kapat - database'de kapatıldı olarak işaretle
"""
import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime

load_dotenv('.env.production')
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not found")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("🔍 Açık sayımları kontrol ediyorum...")
    cursor.execute("SELECT session_id, status FROM count_sessions WHERE status = 'active'")
    active = cursor.fetchall()
    
    if active:
        print(f"\n⚠️  {len(active)} AÇIK SAYIM BULUNDU!")
        for session_id, status in active:
            print(f"   - {session_id[:12]}... ({status})")
        
        print("\n🔨 Force closing...")
        cursor.execute("""
            UPDATE count_sessions 
            SET status = 'completed', finished_at = %s 
            WHERE status = 'active'
        """, (datetime.now(),))
        
        affected = cursor.rowcount
        conn.commit()
        print(f"✅ {affected} sayım KAPATILDI!")
    else:
        print("✅ Zaten hiç açık sayım yok!")
    
    # Kontrol et
    cursor.execute("SELECT COUNT(*) FROM count_sessions WHERE status = 'active'")
    remaining = cursor.fetchone()[0]
    print(f"\n📊 Kalan açık sayımlar: {remaining}")
    
    cursor.close()
    conn.close()
    print("\n✅ TAMAM - Admin hesabıyla giriş yapabilirsin!")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    exit(1)
