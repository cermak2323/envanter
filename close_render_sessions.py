#!/usr/bin/env python3
"""
🌐 RENDER.COM PRODUCTION: Tüm açık sayımları kapat
Kullanım: python close_render_sessions.py
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from datetime import datetime

# .env.production'dan DATABASE_URL'yi oku
print("📂 .env.production okunuyor...")
load_dotenv('.env.production')

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ HATA: DATABASE_URL bulunamadı!")
    print("   ✓ .env.production dosyası var mı?")
    print("   ✓ DATABASE_URL tanımlanmış mı?")
    sys.exit(1)

print(f"✅ DATABASE_URL bulundu (bağlantı kuruluyor...)")

try:
    # Render.com PostgreSQL'e bağlan
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("🔍 RENDER.COM PRODUCTION - AÇIK SAYIM KONTROLÜ")
    print("="*70)
    
    # Açık sayımları bul
    cursor.execute("""
        SELECT 
            session_id, 
            status, 
            created_at, 
            created_by,
            (SELECT u.username FROM users u WHERE u.id = count_sessions.created_by) as creator
        FROM count_sessions 
        WHERE status = 'active'
        ORDER BY created_at DESC
    """)
    
    active_sessions = cursor.fetchall()
    
    if not active_sessions:
        print("\n✅ Zaten açık sayım yok! Sistem temiz.")
        cursor.close()
        conn.close()
        sys.exit(0)
    
    print(f"\n⚠️  {len(active_sessions)} AÇIK SAYIM BULUNDU:\n")
    for i, (session_id, status, created_at, created_by, creator) in enumerate(active_sessions, 1):
        # Kaç QR taranmış?
        cursor.execute("SELECT COUNT(*) FROM scanned_qr WHERE session_id = %s", (session_id,))
        scan_count = cursor.fetchone()[0]
        
        print(f"{i}. Session ID: {session_id[:16]}...")
        print(f"   Oluşturan: {creator or f'USER {created_by} (DELETED)'}")
        print(f"   Başlangıç: {created_at}")
        print(f"   Taranan QR: {scan_count}")
        print()
    
    # Onay
    print("-"*70)
    print("⚠️  UYARI: Tüm AÇIK sayımlar SONLANDIRILACAK!")
    print("-"*70)
    
    confirm = input("\n🤔 Devam et? (evet/hayır): ").strip().lower()
    
    if confirm not in ['evet', 'yes', 'y', 'e']:
        print("\n❌ İptal edildi.")
        cursor.close()
        conn.close()
        sys.exit(0)
    
    # Hepsini kapat
    print("\n🔨 Kapatılıyor...")
    cursor.execute("""
        UPDATE count_sessions 
        SET status = 'completed', finished_at = %s 
        WHERE status = 'active'
    """, (datetime.now(),))
    
    affected = cursor.rowcount
    conn.commit()
    
    print(f"✅ {affected} sayım KAPATILDI!\n")
    
    # Final kontrol
    cursor.execute("SELECT COUNT(*) FROM count_sessions WHERE status = 'active'")
    remaining = cursor.fetchone()[0]
    
    print(f"📊 Kalan açık sayımlar: {remaining}")
    
    if remaining == 0:
        print("\n✅ BAŞARILI! Render.com sistemi temizlendi.")
        print("   Admin hesabıyla şimdi giriş yapabilirsin.")
    
    cursor.close()
    conn.close()
    
except psycopg2.OperationalError as e:
    print(f"❌ VERİTABANI BAĞLANTISI BAŞARISIZ!")
    print(f"   Hata: {e}")
    print("\n   Kontrol et:")
    print("   ✓ .env.production dosyası mevcut mu?")
    print("   ✓ DATABASE_URL doğru mu?")
    print("   ✓ İnternet bağlantısı var mı?")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ HATA: {e}")
    sys.exit(1)
