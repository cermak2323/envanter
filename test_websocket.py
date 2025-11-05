#!/usr/bin/env python3
"""
Test WebSocket connection and data flow for QR scanning
Simulates client-side QR scanning and tracks what happens on the backend
"""

import socketio
import time
import sys
import requests
import json

# Connect to the server
sio = socketio.Client(
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1,
)

connected = False
received_scan_result = False
last_scan_result = None

@sio.event
def connect():
    global connected
    connected = True
    print("✅ WebSocket bağlantısı başarılı!")

@sio.event
def disconnect():
    global connected
    connected = False
    print("❌ WebSocket bağlantısı koptu!")

@sio.on('scan_result')
def on_scan_result(data):
    global received_scan_result, last_scan_result
    received_scan_result = True
    last_scan_result = data
    print(f"📨 scan_result alındı: {json.dumps(data, indent=2)}")

@sio.on('error')
def on_error(data):
    print(f"⚠️ Error: {data}")

def test_qr_scan():
    """Simulate a QR scan"""
    global received_scan_result, last_scan_result
    
    # Test QR ID - make sure it exists in database
    test_qr_id = "TEST-QR-001"
    
    print(f"\n🔍 QR skeni simülasyonu başlıyor: {test_qr_id}")
    print(f"⏳ Server'ın cevabını bekleniyor...")
    
    # Emit the scan_qr event
    try:
        sio.emit('scan_qr', {'qr_id': test_qr_id})
        print(f"📤 scan_qr event'i gönderildi: {test_qr_id}")
    except Exception as e:
        print(f"❌ Hata gönderimi sırasında: {e}")
        return False
    
    # Wait for response
    received_scan_result = False
    last_scan_result = None
    start_time = time.time()
    timeout = 5
    
    while not received_scan_result and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if received_scan_result:
        print(f"✅ Server cevabı alındı!")
        print(f"Cevap: {json.dumps(last_scan_result, indent=2)}")
        return True
    else:
        print(f"❌ Server'dan cevap alınmadı ({timeout}s timeout)")
        return False

def check_database():
    """Check if QR data was saved to database"""
    try:
        response = requests.get('http://localhost:5000/get_recent_activities')
        if response.status_code == 200:
            activities = response.json()
            print(f"\n📊 Veritabanındaki son aktiviteler:")
            if activities:
                for activity in activities[:5]:
                    print(f"  - QR: {activity.get('qr_id')}, Tarih: {activity.get('scanned_at')}")
            else:
                print("  ⚠️ Hiç aktivite bulunamadı")
            return activities
        else:
            print(f"❌ Aktivite sorgusu başarısız: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Veritabanı sorgusu hatası: {e}")
        return []

if __name__ == '__main__':
    print("🚀 WebSocket Test Başlıyor...")
    print("=" * 50)
    
    # Try to connect
    try:
        print("📡 Server'a bağlanılıyor...")
        sio.connect('http://localhost:5000', 
                   transports=['websocket', 'polling'],
                   wait_timeout=10)
        print("✅ Bağlantı başarılı")
    except Exception as e:
        print(f"❌ Bağlantı başarısız: {e}")
        print("✅ RENDER.COM'da çalışan sistem ile test etmek için lütfen URL'yi değiştirin")
        sys.exit(1)
    
    time.sleep(1)  # Give socket time to connect fully
    
    # Check initial database state
    print("\n📋 İlk veritabanı durumu kontrol ediliyor...")
    initial_activities = check_database()
    
    # Test QR scan
    if not test_qr_scan():
        print("\n⚠️ QR skeni başarısız oldu!")
    
    time.sleep(1)
    
    # Check database after scan
    print("\n📋 QR skeni sonrası veritabanı durumu kontrol ediliyor...")
    final_activities = check_database()
    
    # Compare
    if len(final_activities) > len(initial_activities):
        print(f"\n✅ BAŞARILI: Yeni kayıt eklendi!")
    else:
        print(f"\n❌ BAŞARISIZ: Veritabanına hiçbir şey eklenmedi!")
    
    # Disconnect
    sio.disconnect()
    print("\n✅ Test tamamlandı")
