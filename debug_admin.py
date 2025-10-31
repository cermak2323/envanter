#!/usr/bin/env python3
"""
Debug admin user in database
"""
import sqlite3
import hashlib
import os

# Database path
db_path = "instance/envanter_local.db"

def debug_admin():
    """Check admin user in database"""
    print("🔍 Debugging admin user...")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check table structure
        print("\n📋 Table structure:")
        cursor.execute("PRAGMA table_info(envanter_users)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Check all users
        print("\n👥 All users in database:")
        cursor.execute("SELECT id, username, password_hash, full_name, role FROM envanter_users")
        users = cursor.fetchall()
        
        if not users:
            print("  No users found!")
        else:
            for user in users:
                print(f"  ID: {user[0]}, Username: {user[1]}, Password Hash: {user[2][:20]}..., Full Name: {user[3]}, Role: {user[4]}")
        
        # Test admin password hash
        test_password = "admin123"
        test_hash = hashlib.sha256(test_password.encode()).hexdigest()
        print(f"\n🔐 Testing password hash for 'admin123':")
        print(f"  Generated hash: {test_hash}")
        
        # Check if admin exists with correct hash
        cursor.execute("SELECT * FROM envanter_users WHERE username = ? AND password_hash = ?", 
                      ("admin", test_hash))
        admin_user = cursor.fetchone()
        
        if admin_user:
            print("✅ Admin user found with correct password!")
            print(f"  User data: {admin_user}")
        else:
            print("❌ Admin user NOT found with password 'admin123'")
            
            # Check if admin exists with different password
            cursor.execute("SELECT * FROM envanter_users WHERE username = ?", ("admin",))
            admin_any = cursor.fetchone()
            if admin_any:
                print(f"  Admin exists but with different password hash: {admin_any[2]}")
            else:
                print("  Admin user doesn't exist at all!")
        
    finally:
        conn.close()

if __name__ == "__main__":
    debug_admin()