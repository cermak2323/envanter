#!/usr/bin/env python3
"""
Render Environment Sync Check
PostgreSQL ve B2 bilgileri zaten sistemde mevcut - kontrol edelim
"""
import os

def check_existing_credentials():
    """Mevcut credential'ları kontrol et"""
    print("🔍 MEVCUT CREDENTIAL KONTROLÜ")
    print("=" * 60)
    
    # PostgreSQL Database
    postgresql_url = "postgresql://cermak_envanter_user:N22HyFcRf3bvgMzkK1J5yNYgrXEfIgNC@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter?sslmode=require"
    
    # B2 Storage (RENDER_DEPLOY.md'den)
    b2_key_id = "00313590dd2fde60000000004"
    b2_key = "K003NeFyCuFJzM/1Qo1xYXu+f/M87WU"
    b2_bucket = "envanter-qr-bucket"
    
    # Admin passwords
    admin_count_password = "@R9t$L7e!xP2w#Mn8Zq^Y4v&Bc6*Hd3J"
    
    print("✅ PostgreSQL Database:")
    print(f"   URL: {postgresql_url[:50]}...")
    print(f"   Host: dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com")
    print(f"   Database: cermak_envanter")
    print()
    
    print("✅ Backblaze B2 Storage:")
    print(f"   Key ID: {b2_key_id}")
    print(f"   Key: {b2_key[:20]}...")
    print(f"   Bucket: {b2_bucket}")
    print()
    
    print("✅ Admin Credentials:")
    print(f"   Count Password: {admin_count_password[:15]}...")
    print()
    
    return {
        'DATABASE_URL': postgresql_url,
        'B2_APPLICATION_KEY_ID': b2_key_id,
        'B2_APPLICATION_KEY': b2_key,
        'B2_BUCKET_NAME': b2_bucket,
        'ADMIN_COUNT_PASSWORD': admin_count_password,
        'SESSION_SECRET': 'your-random-session-secret-here'  # Bu generate edilmeli
    }

def generate_session_secret():
    """Session secret oluştur"""
    import secrets
    session_secret = secrets.token_hex(32)
    print("🔑 SESSION SECRET:")
    print(f"   Generated: {session_secret}")
    return session_secret

def create_render_env_script():
    """Render environment variable'ları için script oluştur"""
    creds = check_existing_credentials()
    session_secret = generate_session_secret()
    creds['SESSION_SECRET'] = session_secret
    
    print("\n📋 RENDER DASHBOARD → ENVIRONMENT VARIABLES")
    print("=" * 60)
    print("Bu değerleri Render Dashboard'da ayarlayın:")
    print()
    
    for key, value in creds.items():
        if key in ['DATABASE_URL', 'B2_APPLICATION_KEY', 'SESSION_SECRET', 'ADMIN_COUNT_PASSWORD']:
            scope = "Secret"
        else:
            scope = "Environment Variable"
        
        print(f"Key: {key}")
        print(f"Value: {value}")
        print(f"Scope: {scope}")
        print("-" * 40)
    
    # Dosyaya kaydet
    with open('render_env_vars.txt', 'w') as f:
        f.write("RENDER ENVIRONMENT VARIABLES\n")
        f.write("=" * 40 + "\n\n")
        for key, value in creds.items():
            f.write(f"{key}={value}\n")
    
    print("\n✅ Environment variables 'render_env_vars.txt' dosyasına kaydedildi")

def test_current_environment():
    """Şu anki environment'ı test et"""
    print("\n🧪 CURRENT ENVIRONMENT TEST")
    print("=" * 60)
    
    # Check if running in production mode
    is_production = bool(os.environ.get('RENDER'))
    print(f"Production Mode: {is_production}")
    
    # Check database access
    try:
        from app import get_db, close_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM qr_codes')
        qr_count = cursor.fetchone()[0]
        close_db(conn)
        print(f"✅ Database OK: {qr_count} QR codes")
    except Exception as e:
        print(f"❌ Database Error: {e}")
    
    # Check B2 storage
    try:
        from b2_storage import get_b2_service
        if not is_production:
            print("🏠 B2 Storage: Skipped (Local mode)")
        else:
            b2_service = get_b2_service()
            print("✅ B2 Storage: OK")
    except Exception as e:
        print(f"❌ B2 Storage Error: {e}")

if __name__ == "__main__":
    print("🔧 RENDER ENVIRONMENT SYNC CHECK")
    print("PostgreSQL ve B2 bilgileri sistemde mevcut")
    print("Render Dashboard'a environment variable'ları ekleme zamanı!")
    print()
    
    create_render_env_script()
    test_current_environment()
    
    print("\n🎯 NEXT STEPS:")
    print("1. ✅ render_env_vars.txt dosyasını aç")
    print("2. 🔧 Render Dashboard → Your Service → Environment")
    print("3. ➕ Her bir variable'ı ekle (Secret olanları Secret olarak)")
    print("4. 🚀 Manual Deploy çalıştır")
    print("5. ✅ Health check: https://your-app.onrender.com/health")