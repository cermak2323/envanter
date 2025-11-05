#!/usr/bin/env python
"""
B2 Setup kontrolü ve QR kodları B2'ye yüklemek için script
"""

import os
import sys
from dotenv import load_dotenv

# .env yükle
load_dotenv()

print("=" * 60)
print("🔍 B2 Environment Variables Kontrol Ediliyor...")
print("=" * 60)

# B2 credentials kontrol
b2_key_id = os.getenv('B2_APPLICATION_KEY_ID') or os.getenv('B2_KEY_ID')
b2_key = os.getenv('B2_APPLICATION_KEY')
b2_bucket = os.getenv('B2_BUCKET_NAME')

print(f"\n✅ B2_APPLICATION_KEY_ID: {'✓ SET' if b2_key_id else '✗ NOT SET'}")
print(f"   Value: {b2_key_id[:10] + '***' if b2_key_id else 'NOT SET'}")

print(f"\n✅ B2_APPLICATION_KEY: {'✓ SET' if b2_key else '✗ NOT SET'}")
print(f"   Value: {b2_key[:10] + '***' if b2_key else 'NOT SET'}")

print(f"\n✅ B2_BUCKET_NAME: {'✓ SET' if b2_bucket else '✗ NOT SET'}")
print(f"   Value: {b2_bucket if b2_bucket else 'NOT SET'}")

if not all([b2_key_id, b2_key, b2_bucket]):
    print("\n❌ B2 credentials eksik!")
    print("\n📝 Lütfen .env dosyanıza şu satırları ekleyin:")
    print("=" * 60)
    print("B2_APPLICATION_KEY_ID=your_key_id")
    print("B2_APPLICATION_KEY=your_application_key")
    print("B2_BUCKET_NAME=envanter-qr-codes")
    print("=" * 60)
    sys.exit(1)

print("\n✅ Tüm B2 credentials set edilmiş!")

# B2 Service'i test et
try:
    from b2_storage import get_b2_service
    print("\n🔗 B2 Service bağlantısı test ediliyor...")
    b2_service = get_b2_service()
    print("✅ B2 Service başarıyla bağlandı!")
    
    # Bucket bilgisi
    print(f"\n📊 Bucket Bilgisi:")
    print(f"   Bucket Name: {b2_service.bucket_name}")
    print(f"   Bucket Type: {b2_service.bucket.type_}")
    
    # Var olan dosyaları listele
    print(f"\n📁 B2'de Mevcut Dosyalar:")
    files = b2_service.list_files('qr_codes/')
    if files:
        for file in files[:5]:  # İlk 5 dosyayı göster
            print(f"   - {file['file_name']} ({file['size']} bytes)")
        if len(files) > 5:
            print(f"   ... ve {len(files) - 5} dosya daha")
    else:
        print("   (Henüz dosya yok)")
    
    print(f"\n✅ B2 Setup Başarılı!")
    print("🎯 QR kodları lokal depolama yerine B2'ye kaydedilecek")
    
except Exception as e:
    print(f"\n❌ B2 Service hatası: {e}")
    print("\n💡 Lütfen B2 credentials'ını kontrol edin")
    sys.exit(1)
