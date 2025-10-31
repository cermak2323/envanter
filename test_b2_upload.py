#!/usr/bin/env python
"""
B2 Storage Test ve QR Upload Script
Lokal development ortamında B2'ye QR kodları yükleme test etmek için
"""

import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# .env yükle
load_dotenv()

print("=" * 70)
print("🚀 B2 Storage Test - QR Kodlarını B2'ye Yükle")
print("=" * 70)

# B2 credentials kontrol
b2_key_id = os.getenv('B2_APPLICATION_KEY_ID') or os.getenv('B2_KEY_ID')
b2_key = os.getenv('B2_APPLICATION_KEY')
b2_bucket = os.getenv('B2_BUCKET_NAME')

print("\n1️⃣  B2 Credentials Kontrol:")
print(f"   ✓ Application Key ID: {b2_key_id[:15] + '...' if b2_key_id else '❌ NOT SET'}")
print(f"   ✓ Application Key: {'✓ SET' if b2_key else '❌ NOT SET'}")
print(f"   ✓ Bucket Name: {b2_bucket if b2_bucket else '❌ NOT SET'}")

if not all([b2_key_id, b2_key, b2_bucket]):
    print("\n❌ B2 credentials eksik!")
    print("\n📖 B2 Setup Talimatları:")
    print("-" * 70)
    print("""
1. Backblaze B2 hesabı oluşturun: https://www.backblaze.com/b2/cloud-storage.html
2. B2 Console'a giriş yapın
3. Application Keys oluşturun:
   - "Create Application Key" butonuna tıklayın
   - Key Type: "Master Application Key" seçin
   - Verilen Key ID ve Application Key'i kopyalayın
4. Bucket oluşturun:
   - "Create Bucket" butonuna tıklayın
   - Bucket Name: "envanter-qr-codes" (veya başka bir ad)
   - Type: "Private" seçin
5. .env dosyasını güncelleyin:
   
   B2_APPLICATION_KEY_ID=your_key_id_here
   B2_APPLICATION_KEY=your_app_key_here
   B2_BUCKET_NAME=envanter-qr-codes
6. FORCE_B2_LOCAL=true environment variable'ı set edin
    """)
    print("-" * 70)
    sys.exit(1)

print("✅ B2 credentials doğrulandı!")

# B2 Service'i başlat
try:
    from b2_storage import get_b2_service
    print("\n2️⃣  B2 Service Bağlantısı:")
    b2_service = get_b2_service()
    print("✅ B2 Service başarıyla bağlandı!")
except Exception as e:
    print(f"❌ B2 Service hatası: {e}")
    sys.exit(1)

# Lokal SQLite veritabanından QR kodları oku
print("\n3️⃣  Lokal QR Kodları Kontrol:")
try:
    db_path = 'instance/envanter_local.db'
    if not os.path.exists(db_path):
        print(f"❌ Database dosyası bulunamadı: {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM qr_codes')
    count = cursor.fetchone()[0]
    
    print(f"✅ {count} QR kod bulundu")
    
    # İlk 5 QR'ı listele
    cursor.execute('SELECT qr_id, part_code, part_name FROM qr_codes LIMIT 5')
    qr_records = cursor.fetchall()
    
    for qr_id, part_code, part_name in qr_records:
        print(f"   - {qr_id}: {part_code} ({part_name})")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Database hatası: {e}")
    sys.exit(1)

# Lokal QR dosyalarını kontrol et
print("\n4️⃣  Lokal QR Dosyaları Kontrol:")
qr_dir = Path('static/qrcodes')
if qr_dir.exists():
    local_qr_files = list(qr_dir.glob('*.png'))
    print(f"✅ {len(local_qr_files)} QR dosyası lokal depolama'da")
    
    if len(local_qr_files) > 0:
        print(f"\n5️⃣  B2'ye QR Dosyaları Yükleniyor:")
        uploaded_count = 0
        failed_count = 0
        
        for i, qr_file in enumerate(local_qr_files[:10]):  # İlk 10 dosyayı yükle
            try:
                qr_id = qr_file.stem  # Filename without extension
                with open(qr_file, 'rb') as f:
                    file_content = f.read()
                
                result = b2_service.upload_file(
                    f'qr_codes/{qr_id}.png',
                    file_content,
                    'image/png'
                )
                
                if result['success']:
                    print(f"   ✓ {qr_id}.png ({len(file_content)} bytes)")
                    uploaded_count += 1
                else:
                    print(f"   ✗ {qr_id}.png - {result.get('error', 'Unknown error')}")
                    failed_count += 1
                    
            except Exception as e:
                print(f"   ✗ {qr_file.name} - {e}")
                failed_count += 1
        
        print(f"\n✅ Upload Sonuç:")
        print(f"   Başarılı: {uploaded_count}")
        print(f"   Başarısız: {failed_count}")
        
        # B2'de dosyaları listele
        print(f"\n6️⃣  B2'de Mevcut Dosyalar:")
        b2_files = b2_service.list_files('qr_codes/')
        print(f"✅ {len(b2_files)} dosya B2'de depolanmış")
        
        if b2_files:
            for file in b2_files[:5]:
                print(f"   - {file['file_name']} ({file['size']} bytes)")
            if len(b2_files) > 5:
                print(f"   ... ve {len(b2_files) - 5} dosya daha")
    else:
        print("   (QR dosyası yok)")
else:
    print(f"   (QR dizini bulunamadı: {qr_dir})")

print("\n" + "=" * 70)
print("✅ B2 Storage Test Tamamlandı!")
print("=" * 70)
