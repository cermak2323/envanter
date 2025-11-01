#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B2 Depolaması Kontrolü Scripti
QR kodlarının B2'ye doğru kaydedilip kaydedilmediğini kontrol etmek için
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def check_env_file():
    """Check .env.production for B2 settings"""
    print("\n📋 Checking .env.production file...")
    
    env_file = Path('.env.production')
    if not env_file.exists():
        print("❌ .env.production not found!")
        return False
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Check bucket name
    if 'B2_BUCKET_NAME=Envanter' in content:
        print("✅ Bucket name correct: Envanter")
    elif 'B2_BUCKET_NAME=envanter-qr-bucket' in content:
        print("❌ OLD bucket name found: envanter-qr-bucket")
        print("   Should be: Envanter")
        return False
    else:
        print("❌ B2_BUCKET_NAME not found")
        return False
    
    # Check for required B2 credentials
    if 'B2_APPLICATION_KEY_ID' in content and 'B2_APPLICATION_KEY' in content:
        print("✅ B2 credentials present")
    else:
        print("❌ B2 credentials missing")
        return False
    
    return True

def check_b2_service():
    """Check if B2 service can connect"""
    print("\n🌐 Checking B2 service connection...")
    
    try:
        from b2_storage import B2StorageService
        
        # Initialize B2
        b2 = B2StorageService()
        
        # Try to connect
        if b2.client:
            print("✅ B2 service connected successfully")
            
            # Check bucket
            bucket_name = os.environ.get('B2_BUCKET_NAME', 'Envanter')
            print(f"✅ Using bucket: {bucket_name}")
            
            # List files in qr_codes folder
            try:
                files = b2.list_files('qr_codes/')
                if files:
                    print(f"✅ Found {len(files)} QR files in B2:")
                    for f in files[:5]:  # Show first 5
                        print(f"   📄 {f.get('name')}")
                    if len(files) > 5:
                        print(f"   ... and {len(files) - 5} more")
                else:
                    print("⚠️  No QR files in B2 yet (bucket is empty)")
            except Exception as e:
                print(f"⚠️  Could not list files: {e}")
            
            return True
        else:
            print("❌ B2 service failed to connect")
            return False
            
    except Exception as e:
        print(f"❌ Error checking B2 service: {e}")
        return False

def check_app_config():
    """Check app.py for B2 integration"""
    print("\n⚙️  Checking app.py configuration...")
    
    try:
        with open('app.py', 'r') as f:
            content = f.read()
        
        # Check for B2 storage flag
        if 'USE_B2_STORAGE' in content:
            print("✅ B2 storage mode implemented")
        else:
            print("❌ B2 storage mode not found")
            return False
        
        # Check for upload function
        if 'b2_service.upload_file' in content:
            print("✅ B2 upload function found")
        else:
            print("❌ B2 upload function not found")
            return False
        
        # Check for download function
        if 'b2_service.download_file' in content:
            print("✅ B2 download function found")
        else:
            print("❌ B2 download function not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking app.py: {e}")
        return False

def check_local_storage():
    """Check local QR storage directory"""
    print("\n💾 Checking local storage directory...")
    
    qr_dir = Path('static/qrcodes')
    if qr_dir.exists():
        files = list(qr_dir.glob('*.png'))
        if files:
            print(f"✅ Local storage exists with {len(files)} QR files")
            for f in files[:3]:
                print(f"   📄 {f.name}")
            if len(files) > 3:
                print(f"   ... and {len(files) - 3} more")
        else:
            print("⚠️  Local storage exists but is empty")
    else:
        print("ℹ️  Local storage directory doesn't exist (will be created on first use)")
    
    return True

def main():
    """Main check function"""
    print("=" * 60)
    print("🔍 B2 STORAGE VERIFICATION")
    print("=" * 60)
    
    results = {
        "Environment File": check_env_file(),
        "B2 Service": check_b2_service(),
        "App Configuration": check_app_config(),
        "Local Storage": check_local_storage(),
    }
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 B2 Integration is ready for production!")
        print("\n📝 Next steps:")
        print("1. Commit changes: git add app.py .env.production")
        print("2. Deploy: git push origin main")
        print("3. Render.com will auto-redeploy")
        print("4. QR codes will be stored in B2 permanently!")
    else:
        print("\n⚠️  Some checks failed. Please review above.")
        print("\n💡 Troubleshooting:")
        print("- Check B2 credentials in .env.production")
        print("- Verify bucket name: Envanter (not envanter-qr-bucket)")
        print("- Check app.py has B2 code (should have b2_service calls)")

if __name__ == '__main__':
    main()
