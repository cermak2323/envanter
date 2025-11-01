#!/usr/bin/env python3
"""
Comprehensive fallback system diagnostic report
"""
import os
import json
import sys
from datetime import datetime

print("\n" + "=" * 70)
print("🔧 ENVANTERQR FALLBACK SYSTEM - COMPREHENSIVE DIAGNOSTIC REPORT")
print("=" * 70)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# Section 1: Environment
print("\n1️⃣  ENVIRONMENT CONFIGURATION")
print("-" * 70)

env_vars = {
    'B2_APPLICATION_KEY_ID': os.environ.get('B2_APPLICATION_KEY_ID', ''),
    'B2_APPLICATION_KEY': '***' if os.environ.get('B2_APPLICATION_KEY') else 'NOT SET',
    'B2_BUCKET_NAME': os.environ.get('B2_BUCKET_NAME', ''),
    'RENDER': os.environ.get('RENDER', ''),
    'FLASK_ENV': os.environ.get('FLASK_ENV', 'not set'),
}

for key, value in env_vars.items():
    status = "✅" if value and value != 'NOT SET' else "❌"
    print(f"{status} {key}: {value if len(str(value)) < 30 else str(value)[:27] + '...'}")

# Section 2: File Structure
print("\n2️⃣  FILE STRUCTURE CHECK")
print("-" * 70)

required_files = {
    'app.py': 'Main Flask application',
    'b2_storage.py': 'B2 storage service',
    'templates/count.html': 'QR scanning template',
    'requirements.txt': 'Python dependencies',
}

for file, desc in required_files.items():
    exists = os.path.exists(file)
    status = "✅" if exists else "❌"
    print(f"{status} {file:<30} - {desc}")

# Section 3: Code Components
print("\n3️⃣  CODE COMPONENTS CHECK")
print("-" * 70)

print("\n   Backend (@socketio.on('scan_qr') handler):")
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()
    
    checks = {
        "@socketio.on('scan_qr')": "Socket event handler",
        "def handle_scan": "Event function",
        "data.get('qr_code')": "QR code parameter (manual)",
        "data.get('qr_id')": "QR id parameter (camera)",
        "emit('scan_result'": "Response emission",
        "'success': True": "Success response",
        "'success': False": "Error response",
    }
    
    for check, desc in checks.items():
        found = check in app_content
        status = "✅" if found else "❌"
        print(f"   {status} {desc:<40} ({check})")

print("\n   Frontend (Manual QR Entry):")
with open('templates/count.html', 'r', encoding='utf-8') as f:
    html_content = f.read()
    
    checks = {
        "function submitManualQR()": "Manual submission function",
        "manualEntryModal": "Input modal element",
        "manualQRInput": "Input field element",
        "socket.emit('scan_qr'": "Socket emission",
        "socket.on('scan_result'": "Result listener",
        "function showManualInput()": "Modal show function",
        "function closeManualEntry()": "Modal close function",
        "socket.connected": "Connection check",
    }
    
    for check, desc in checks.items():
        found = check in html_content
        status = "✅" if found else "❌"
        print(f"   {status} {desc:<40} ({check})")

print("\n   QR Libraries:")
libs = {
    'html5-qrcode': 'unpkg.com/html5-qrcode',
    'jsqrcode': 'jsqrcode',
    'zxing': 'zxing',
}

for lib, check in libs.items():
    found = check in html_content
    status = "✅" if found else "❌"
    print(f"   {status} {lib:<30} CDN loaded")

# Section 4: B2 Storage
print("\n4️⃣  B2 STORAGE DIAGNOSTIC")
print("-" * 70)

try:
    from b2_storage import B2StorageService, get_b2_service
    print("✅ B2StorageService imported successfully")
    
    try:
        b2 = get_b2_service()
        print("✅ B2 service initialized")
        
        # Check download method
        if hasattr(b2, 'download_file'):
            print("✅ download_file() method exists")
        else:
            print("❌ download_file() method NOT found")
        
        # Test bucket access
        files = b2.list_files()
        print(f"✅ Bucket accessible - {len(files)} files stored")
        
        if files:
            print(f"   Sample files:")
            for f in files[:2]:
                fname = f.get('file_name', 'unknown')[:50]
                print(f"   • {fname}")
        
    except Exception as e:
        print(f"❌ B2 service error: {e}")
        
except ImportError as e:
    print(f"❌ Failed to import B2Storage: {e}")

# Section 5: Database
print("\n5️⃣  DATABASE CONNECTION CHECK")
print("-" * 70)

try:
    import psycopg2
    print("✅ psycopg2 module available")
    
    # Try to get DB connection
    from app import get_db
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'count_sessions'
            )
        """)
        
        if cursor.fetchone()[0]:
            print("✅ count_sessions table found")
        else:
            print("❌ count_sessions table NOT found")
        
        # Check for active sessions
        cursor.execute("SELECT COUNT(*) FROM count_sessions WHERE status = 'active'")
        active = cursor.fetchone()[0]
        print(f"✅ Active count sessions: {active}")
        
        # Check QR codes
        cursor.execute("SELECT COUNT(*) FROM qr_codes")
        qr_count = cursor.fetchone()[0]
        print(f"✅ Total QR codes: {qr_count}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"⚠️  Database query error: {e}")
        
except ImportError:
    print("❌ psycopg2 not available")

# Section 6: Deployment Status
print("\n6️⃣  DEPLOYMENT STATUS")
print("-" * 70)

import subprocess

try:
    result = subprocess.run(
        ['git', 'log', '-1', '--oneline'],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        print(f"✅ Latest commit: {result.stdout.strip()}")
    else:
        print("⚠️  Git info unavailable")
except Exception as e:
    print(f"⚠️  Git error: {e}")

# Section 7: Summary
print("\n" + "=" * 70)
print("📋 SUMMARY & NEXT STEPS")
print("=" * 70)

issues = []
if not os.environ.get('B2_APPLICATION_KEY_ID'):
    issues.append("B2_APPLICATION_KEY_ID not set")
if not os.environ.get('B2_BUCKET_NAME'):
    issues.append("B2_BUCKET_NAME not set")
if "@socketio.on('scan_qr')" not in app_content:
    issues.append("Socket handler not found in app.py")
if "function submitManualQR()" not in html_content:
    issues.append("Manual QR function not found in count.html")

if issues:
    print("\n⚠️  ISSUES DETECTED:")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
else:
    print("\n✅ ALL SYSTEMS OPERATIONAL")

print("\n🚀 TESTING PROCEDURE:")
print("   1. Go to Render.com production URL")
print("   2. Open browser DevTools (F12 → Console)")
print("   3. Navigate to Sayım (Count) page")
print("   4. Test camera by clicking 'Kamerayı Başlat'")
print("   5. If camera fails:")
print("      • Look for error in console")
print("      • Click 'Manuel Giriş' button")
print("      • Enter QR code: 03786-07448-975fcd66")
print("      • Press Enter or click 'Gönder'")
print("   6. Check console for success/error messages")
print("\n" + "=" * 70)
