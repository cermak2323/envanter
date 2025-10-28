#!/usr/bin/env python3
"""
Acil Durum Sayım Durdurma Aracı
Tüm aktif sayımları durdurur ve session'ları temizler
"""

import sqlite3
from datetime import datetime
import sys

DATABASE = 'inventory_qr.db'
ADMIN_PASSWORD = "@R9t$L7e!xP2w#Mn8Zq^Y4v&Bc6*Hd3J"

def get_db():
    return sqlite3.connect(DATABASE)

def stop_all_active_counts():
    """Tüm aktif sayımları durdur"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Aktif sayımları kontrol et
        cursor.execute('SELECT session_id, started_at FROM count_sessions WHERE status = "active"')
        active_sessions = cursor.fetchall()
        
        if not active_sessions:
            print("✅ Durdurulacak aktif sayım bulunamadı.")
            return True
            
        print(f"🔍 {len(active_sessions)} aktif sayım bulundu:")
        for session_id, started_at in active_sessions:
            print(f"   - Session ID: {session_id[:8]}... (Başlangıç: {started_at})")
        
        # Kullanıcıdan onay al
        confirm = input(f"\n⚠️  {len(active_sessions)} aktif sayımı durdurmak istediğinizden emin misiniz? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes', 'e', 'evet']:
            print("❌ İşlem iptal edildi.")
            return False
        
        # Admin şifresi kontrolü
        admin_input = input("🔐 Admin şifresini girin: ").strip()
        if admin_input != ADMIN_PASSWORD:
            print("❌ Yanlış admin şifresi. İşlem iptal edildi.")
            return False
        
        # Tüm aktif sayımları durdur
        stopped_count = 0
        for session_id, _ in active_sessions:
            cursor.execute('UPDATE count_sessions SET status = "stopped", finished_at = ? WHERE session_id = ?',
                         (datetime.now(), session_id))
            stopped_count += 1
            print(f"🛑 Sayım durduruldu: {session_id[:8]}...")
        
        conn.commit()
        print(f"\n✅ {stopped_count} aktif sayım başarıyla durduruldu!")
        print("📝 Durum: Tüm sayımlar 'stopped' olarak işaretlendi.")
        
        return True
        
    except Exception as e:
        print(f"❌ Hata oluştu: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def show_count_status():
    """Sayım durumunu göster"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Tüm sayımları listele
        cursor.execute('''
            SELECT session_id, status, started_at, finished_at 
            FROM count_sessions 
            ORDER BY started_at DESC LIMIT 10
        ''')
        sessions = cursor.fetchall()
        
        print("\n📊 SON 10 SAYIM DURUMU:")
        print("-" * 80)
        print(f"{'Session ID':<12} {'Durum':<12} {'Başlangıç':<20} {'Bitiş':<20}")
        print("-" * 80)
        
        for session_id, status, started_at, finished_at in sessions:
            status_emoji = {
                'active': '🟢',
                'completed': '✅', 
                'stopped': '🛑'
            }.get(status, '❓')
            
            finished_str = finished_at if finished_at else 'Devam ediyor'
            print(f"{session_id[:8]+'...':<12} {status_emoji+' '+status:<12} {started_at:<20} {finished_str:<20}")
        
        # Aktif sayım sayısı
        cursor.execute('SELECT COUNT(*) FROM count_sessions WHERE status = "active"')
        active_count = cursor.fetchone()[0]
        print(f"\n🔍 Toplam aktif sayım: {active_count}")
        
    except Exception as e:
        print(f"❌ Hata oluştu: {str(e)}")
    finally:
        conn.close()

def main():
    print("=" * 60)
    print("🚨 ENVANTER QR SAYIM DURDURMA ARACI")
    print("=" * 60)
    
    while True:
        print("\nSeçenekler:")
        print("1. Sayım durumunu göster")
        print("2. Tüm aktif sayımları durdur") 
        print("3. Çıkış")
        
        choice = input("\nSeçiminizi yapın (1-3): ").strip()
        
        if choice == '1':
            show_count_status()
        elif choice == '2':
            if stop_all_active_counts():
                print("\n🎉 İşlem tamamlandı!")
            else:
                print("\n⚠️  İşlem başarısız veya iptal edildi.")
        elif choice == '3':
            print("👋 Çıkış yapılıyor...")
            break
        else:
            print("❌ Geçersiz seçim. Lütfen 1-3 arası bir sayı girin.")

if __name__ == "__main__":
    main()