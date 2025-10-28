import psycopg2
import os
from dotenv import load_dotenv

# .env dosyasından değişkenleri yükle
load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

try:
    # Veritabanına bağlan
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("🔗 PostgreSQL bağlantısı başarılı")
    
    # Kullanıcıları listele
    cursor.execute("SELECT id, username, password, password_hash, full_name, role FROM users;")
    users = cursor.fetchall()
    
    print(f"\n📋 Toplam {len(users)} kullanıcı bulundu:")
    for user in users:
        print(f"ID: {user[0]}, Username: {user[1]}, Password: {user[2]}, Password_Hash: {user[3][:20] if user[3] else None}..., Full_Name: {user[4]}, Role: {user[5]}")
    
    # Admin kullanıcısının hash'ini test et
    import hashlib
    test_password = "admin123"
    test_hash = hashlib.sha256(test_password.encode()).hexdigest()
    
    print(f"\n🔒 Test password 'admin123' hash: {test_hash}")
    
    # admin kullanıcısını sorgula
    cursor.execute("SELECT password_hash FROM users WHERE username = %s", ('admin',))
    admin_hash = cursor.fetchone()
    
    if admin_hash:
        print(f"📊 Veritabanındaki admin hash: {admin_hash[0]}")
        print(f"✅ Hash eşleşmesi: {test_hash == admin_hash[0]}")
    else:
        print("❌ Admin kullanıcısı bulunamadı!")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Hata: {e}")