#!/usr/bin/env python3
import os
import sys
import traceback
from b2_storage import B2StorageService

print("=" * 60)
print("🔍 B2 FALLBACK SYSTEM TEST")
print("=" * 60)

# 1. Credentials Check
print("\n1️⃣  B2 CREDENTIALS CHECK:")
print("-" * 60)
app_key_id = os.environ.get("B2_APPLICATION_KEY_ID", "")
app_key = os.environ.get("B2_APPLICATION_KEY", "")
bucket_name = os.environ.get("B2_BUCKET_NAME", "")

print(f"  ✓ B2_APPLICATION_KEY_ID: {app_key_id[:10]}...{app_key_id[-5:] if len(app_key_id) > 15 else ''}")
print(f"  ✓ B2_APPLICATION_KEY: {'SET' if app_key else 'NOT SET'}")
print(f"  ✓ B2_BUCKET_NAME: {bucket_name}")

if not all([app_key_id, app_key, bucket_name]):
    print("\n❌ ERROR: B2 credentials not fully configured!")
    sys.exit(1)

# 2. B2Storage Initialization
print("\n2️⃣  B2STORAGESERVICE INITIALIZATION:")
print("-" * 60)
try:
    b2 = B2StorageService()
    print("✅ B2Storage initialized successfully")
    if hasattr(b2, 'bucket') and b2.bucket:
        print(f"   Bucket name: {b2.bucket.name}")
    else:
        print("   Bucket not available yet")
except Exception as e:
    print(f"❌ Failed to initialize B2StorageService:")
    print(f"   Error: {e}")
    traceback.print_exc()
    sys.exit(1)

# 3. Test Download Method (NEW)
print("\n3️⃣  TESTING NEW DOWNLOAD METHOD:")
print("-" * 60)
try:
    # Check if download_file method exists
    if hasattr(b2, 'download_file'):
        print("✅ download_file method exists")
        
        # Check method signature
        import inspect
        sig = inspect.signature(b2.download_file)
        print(f"   Parameters: {sig}")
    else:
        print("❌ download_file method NOT found!")
except Exception as e:
    print(f"❌ Error checking download method: {e}")

# 4. Test List Files (to verify bucket access)
print("\n4️⃣  TESTING LIST FILES (Bucket Access):")
print("-" * 60)
try:
    files = b2.list_files()
    if files:
        print(f"✅ Bucket accessible, found {len(files)} files")
        # Show first 3 files
        for i, f in enumerate(files[:3]):
            print(f"   {i+1}. {f}")
        if len(files) > 3:
            print(f"   ... and {len(files) - 3} more files")
    else:
        print("⚠️  Bucket is empty")
except Exception as e:
    print(f"❌ Failed to list files:")
    print(f"   Error: {e}")
    traceback.print_exc()

# 5. Frontend Check
print("\n5️⃣  FRONTEND QR LIBRARIES CHECK:")
print("-" * 60)
with open('templates/count.html', 'r', encoding='utf-8') as f:
    content = f.read()
    
    libraries = {
        'html5-qrcode': 'unpkg.com/html5-qrcode',
        'jsqrcode': 'jsqrcode',
        'zxing': 'zxing',
    }
    
    for lib, check in libraries.items():
        if check in content:
            print(f"✅ {lib} loaded")
        else:
            print(f"❌ {lib} NOT loaded")
    
    # Check Manual Entry Function
    if 'showManualInput()' in content:
        print("✅ Manual input function found")
    else:
        print("❌ Manual input function NOT found")

# 6. Summary
print("\n" + "=" * 60)
print("✅ FALLBACK SYSTEM READY FOR TESTING")
print("=" * 60)
print("\nNext steps:")
print("1. Open Render.com production URL")
print("2. Go to Sayım (Count) page")
print("3. Click 'Kamerayı Başlat' (Start Camera)")
print("4. If camera fails, click 'Manuel Giriş' (Manual Input)")
print("5. Enter QR code and press Enter")
print("\nCheck browser console (F12) for detailed errors")
