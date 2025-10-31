import sqlite3
import os

# Database path
db_path = 'instance/envanter_local.db'

if os.path.exists(db_path):
    print(f"📍 Database exists: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"📋 Tables: {[t[0] for t in tables]}")
    
    # Check envanter_users table schema
    if ('envanter_users',) in tables:
        cursor.execute("PRAGMA table_info(envanter_users)")
        columns = cursor.fetchall()
        print(f"\n📊 envanter_users columns:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Check if full_name column exists
        column_names = [col[1] for col in columns]
        print(f"\n🔍 full_name column exists: {'full_name' in column_names}")
        
        # Check admin user
        cursor.execute("SELECT username, full_name, role FROM envanter_users WHERE username = 'admin'")
        admin = cursor.fetchone()
        print(f"\n👤 Admin user: {admin if admin else 'Not found'}")
        
        # Check all users
        cursor.execute("SELECT COUNT(*) FROM envanter_users")
        user_count = cursor.fetchone()[0]
        print(f"👥 Total users: {user_count}")
        
    else:
        print("⚠️ envanter_users table not found")
    
    conn.close()
else:
    print(f"❌ Database not found: {db_path}")