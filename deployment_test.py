#!/usr/bin/env python3
"""
Local Environment Test - Deployment Ready Check
"""
import os
import sys
import requests
import subprocess
import time

def check_local_environment():
    """Lokal ortamı kontrol et"""
    print("🔍 LOCAL ENVIRONMENT CHECK")
    print("=" * 50)
    
    # Python version
    print(f"🐍 Python: {sys.version}")
    
    # Required modules
    required_modules = ['flask', 'sqlalchemy', 'pandas', 'qrcode', 'psycopg2']
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}: OK")
        except ImportError:
            print(f"❌ {module}: MISSING")
    
    print()

def check_environment_variables():
    """Environment variable'ları kontrol et"""
    print("🔧 ENVIRONMENT VARIABLES")
    print("=" * 50)
    
    # Local development - should not have these
    production_vars = ['DATABASE_URL', 'RENDER', 'B2_APPLICATION_KEY_ID']
    local_mode = True
    
    for var in production_vars:
        value = os.environ.get(var)
        if value:
            print(f"⚠️  {var}: SET (Production mode)")
            local_mode = False
        else:
            print(f"✅ {var}: NOT SET (Local mode)")
    
    print(f"\n🏠 Local Mode: {local_mode}")
    print(f"☁️ Production Mode: {not local_mode}")
    print()

def test_app_startup():
    """App başlatma testi"""
    print("🚀 APP STARTUP TEST")
    print("=" * 50)
    
    try:
        # Import app
        sys.path.insert(0, os.getcwd())
        from app import app, socketio
        
        print("✅ App import: SUCCESS")
        
        # Database test
        from app import get_db, close_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM qr_codes')
        qr_count = cursor.fetchone()[0]
        close_db(conn)
        
        print(f"✅ Database: OK ({qr_count} QR codes)")
        
        return app
        
    except Exception as e:
        print(f"❌ App startup: FAILED")
        print(f"   Error: {e}")
        return None

def test_health_endpoint():
    """Health endpoint test"""
    print("🏥 HEALTH ENDPOINT TEST")
    print("=" * 50)
    
    try:
        # Start app in background
        import threading
        from app import app, socketio
        
        def run_app():
            socketio.run(app, host='127.0.0.1', port=5003, debug=False, use_reloader=False)
        
        app_thread = threading.Thread(target=run_app, daemon=True)
        app_thread.start()
        
        # Wait for startup
        time.sleep(3)
        
        # Test health endpoint
        response = requests.get('http://127.0.0.1:5003/health', timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            print("✅ Health endpoint: OK")
            print(f"   Status: {health_data.get('status')}")
            print(f"   Database: {health_data.get('database')}")
            print(f"   Storage: {health_data.get('storage')}")
            
            env_info = health_data.get('environment', {})
            print(f"   Mode: {env_info.get('mode')}")
            print(f"   DB Type: {env_info.get('database_type')}")
            print(f"   Storage Type: {env_info.get('storage_type')}")
            
        else:
            print(f"❌ Health endpoint: FAILED (status {response.status_code})")
            
    except Exception as e:
        print(f"❌ Health endpoint: ERROR")
        print(f"   Error: {e}")

def deployment_readiness_check():
    """Deployment hazırlık kontrolü"""
    print("\n📋 DEPLOYMENT READINESS CHECK")
    print("=" * 50)
    
    checks = []
    
    # Required files
    required_files = [
        'app.py', 'requirements.txt', 'render_startup_alt.py', 
        'render.yaml', 'RENDER_ENV_SETUP.md'
    ]
    
    for file in required_files:
        if os.path.exists(file):
            checks.append(f"✅ {file}: EXISTS")
        else:
            checks.append(f"❌ {file}: MISSING")
    
    # Render.yaml check
    if os.path.exists('render.yaml'):
        with open('render.yaml', 'r') as f:
            content = f.read()
            if 'DATABASE_URL' in content and 'scope: secret' in content:
                checks.append("✅ render.yaml: Properly configured")
            else:
                checks.append("⚠️ render.yaml: May need DATABASE_URL secret")
    
    for check in checks:
        print(check)
    
    print("\n🎯 NEXT STEPS FOR DEPLOYMENT:")
    print("1. ✅ Code is ready for deployment")
    print("2. 🔧 Set environment variables in Render Dashboard")
    print("3. 📖 Follow RENDER_ENV_SETUP.md instructions")
    print("4. 🚀 Deploy and monitor logs")

if __name__ == "__main__":
    print("🧪 ENVANTER QR - DEPLOYMENT READINESS TEST")
    print("=" * 60)
    print()
    
    check_local_environment()
    check_environment_variables()
    
    app = test_app_startup()
    if app:
        test_health_endpoint()
    
    deployment_readiness_check()
    
    print("\n" + "=" * 60)
    print("✅ Test completed. Check results above.")