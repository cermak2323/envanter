#!/usr/bin/env python3
"""
Verify the complete data flow and identify exactly where the problem is
"""

import subprocess
import json
import time
import sys

def run_command(cmd):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"

def check_database_records():
    """Check if any new records were added to the database"""
    print("\n🔍 Veritabanı Kontrol Noktaları:")
    print("-" * 50)
    
    # Check counts
    sql_query = """
    SELECT COUNT(*) as total_records FROM scanned_qr;
    SELECT MAX(scanned_at) as latest_scan FROM scanned_qr;
    SELECT COUNT(*) as today_scans FROM scanned_qr WHERE DATE(scanned_at) = CURRENT_DATE;
    """
    
    # If we can access psql directly
    psql_cmd = 'psql -U postgres -d inventory_management -c "SELECT COUNT(*) as total_records FROM scanned_qr; SELECT MAX(scanned_at) as latest_scan FROM scanned_qr;"'
    
    print("📊 Database Record Count:")
    print(run_command(psql_cmd))
    

def check_render_logs():
    """Check if there are any errors in Render logs"""
    print("\n📋 Render Deployment Status:")
    print("-" * 50)
    print("Lütfen https://dashboard.render.com adresine giderek:")
    print("1. Services → EnvanterQR → Logs")
    print("2. Aşağıdaki debug mesajlarını arayın:")
    print("   - '🔍 scan_qr received'")
    print("   - '📤 Emitting scan_result'")
    print("   - '❌' ile başlayan hata mesajları")

def check_socket_connection():
    """Verify socket.io is working"""
    print("\n🔌 WebSocket Bağlantı Kontrolü:")
    print("-" * 50)
    print("Mobil tarayıcıda F12 (Developer Tools) açın:")
    print("1. Console sekmesine gidin")
    print("2. Aşağıdaki mesajları arayın:")
    print("   - '✅ QR DECODED: ...'")
    print("   - '📤 Emitting scan_qr to server...'")
    print("   - '📨 scan_result alındı: ...'")

def generate_diagnostics():
    """Generate a complete diagnostic report"""
    print("\n" + "="*60)
    print("🚨 SİSTEM SORUN GIDERME RAPORU")
    print("="*60)
    
    print("\n1️⃣  QR Tarama Akışı Kontrol Listesi:")
    print("   ☐ Mobil tarayıcıda kamera izni verildi mi?")
    print("   ☐ Kamera görüntüsü ekranı doldurmuyor mu?")
    print("   ☐ QR frame (yeşil çerçeve) gösteriliyor mu?")
    print("   ☐ Tarama sırasında 'QR DECODED' console mesajı görülüyor mu?")
    print("   ☐ WebSocket bağlantısı aktif mi (green indicator)?")
    
    print("\n2️⃣  Backend Yanıt Kontrolü:")
    print("   ☐ QR gönderdikten 2 saniye içinde mesaj gösterildi mi?")
    print("   ☐ Render logs'ta '🔍 scan_qr received' mesajı var mı?")
    print("   ☐ 'Permitted' veya 'count_access=True' mesajı var mı?")
    
    print("\n3️⃣  Veritabanı Kayıt Kontrolü:")
    print("   ☐ Render PostgreSQL tarafında yeni kayıt var mı?")
    print("   ☐ scanned_qr tablosunun son insert tarihini kontrol et")
    print("   ☐ INSERT command'i 'SUCCESS' dönüp dönmediğini kontrol et")
    
    print("\n" + "="*60)
    print("🔧 Hızlı Çözüm Adımları:")
    print("="*60)
    
    print("\n📱 Adım 1: Mobil Tarayıcı Konsol Kontrolü")
    print("  1. Mobil tarayıcıda count.html sayfasını açın")
    print("  2. F12 → Console sekmesini açın")
    print("  3. Bir QR kodu tarayın")
    print("  4. Console'da şu mesajları olmalı:")
    print("     - ✅ QR DECODED")
    print("     - 📤 Emitting scan_qr")
    print("     - 📨 scan_result alındı")
    print("     - ✅ SUCCESS mesaj gösterildi")
    
    print("\n⚙️  Adım 2: Backend Kontrol")
    if True:  # Can check logs
        print("  1. Render Dashboard'a gidin")
        print("  2. EnvanterQR Service → Logs sekmesi")
        print("  3. Yeni QR taraması yapın")
        print("  4. Logs'ta şu satırları bulun:")
        print("     - 🔍 scan_qr received")
        print("     - 🔐 count_access check")
        print("     - 🔍 QR_ID processed")
        print("     - 💾 INSERT INTO scanned_qr")
        
    print("\n💾 Adım 3: Veritabanı Kontrol")
    print("  1. Render PostgreSQL'e bağlanın")
    print("  2. Query: SELECT COUNT(*) FROM scanned_qr;")
    print("  3. Sonra: SELECT * FROM scanned_qr ORDER BY scanned_at DESC LIMIT 5;")
    
    print("\n" + "="*60)
    print("✅ KALITANLAR:")
    print("="*60)
    
    symptoms = {
        "Mesaj görünmüyor ama veritabanına kaydediliyor": "Frontend konteyner CSS sorunu",
        "Mesaj görünüyor ama veritabanına kaydedilmiyor": "Backend INSERT başarısız",
        "Ne mesaj ne de veri": "WebSocket bağlantısı sorunu",
        "Sadece backend logs'ta hata görünüyor": "Database permission sorunu",
    }
    
    for symptom, cause in symptoms.items():
        print(f"  ❌ {symptom}")
        print(f"     → Sebep: {cause}\n")
    

if __name__ == '__main__':
    print("🔍 EnvanterQR WebSocket Sorun Giderme")
    print("=" * 60)
    
    generate_diagnostics()
    
    print("\n" + "="*60)
    print("⏭️  SONRAKİ ADIMLAR:")
    print("="*60)
    print("\n1. Mobil tarayıcıda F12 Console'u açın ve yapıştırın:")
    print("   console.log('📱 Cihaz bilgisi:', {")
    print("       userAgent: navigator.userAgent,")
    print("       connected: socket?.connected,")
    print("       socketId: socket?.id,")
    print("   })")
    print("\n2. Output'u rapor edin")
    print("\n3. Render Logs'ta son 50 satırı kontrol edin")
    print("\n4. Veritabanında scanned_qr tablosunun son kaydını kontrol edin")
