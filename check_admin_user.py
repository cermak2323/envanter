#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
from werkzeug.security import generate_password_hash

db_path = r"C:\Users\rsade\Desktop\Yeni klasör\EnvanterQR\EnvanterQR\EnvanterQR\EnvanterQR\instance\envanter_local.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 70)
print("ADMIN USER CHECK")
print("=" * 70)

# 1. Check if admin user exists
print("\n1️⃣ Checking for admin user...")
cursor.execute("SELECT id, username, full_name, role FROM envanter_users WHERE username = 'admin'")
result = cursor.fetchone()

if result:
    print(f"✅ Admin user found:")
    print(f"   ID: {result[0]}")
    print(f"   Username: {result[1]}")
    print(f"   Full Name: {result[2]}")
    print(f"   Role: {result[3]}")
else:
    print("❌ Admin user NOT found!")
    print("\n2️⃣ Creating admin user...")
    
    # Create admin user
    username = 'admin'
    password = 'admin123'
    full_name = 'Admin User'
    role = 'admin'
    
    # Hash password
    password_hash = generate_password_hash(password)
    
    try:
        cursor.execute(
            'INSERT INTO envanter_users (username, password_hash, full_name, role, is_active_user) VALUES (?, ?, ?, ?, ?)',
            (username, password_hash, full_name, role, True)
        )
        conn.commit()
        print(f"✅ Admin user created:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Full Name: {full_name}")
        print(f"   Role: {role}")
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")

# 2. List all users
print("\n3️⃣ All users in database:")
cursor.execute("SELECT id, username, full_name, role, is_active_user FROM envanter_users ORDER BY id")
users = cursor.fetchall()

if users:
    for user in users:
        status = "🟢 ACTIVE" if user[4] else "🔴 INACTIVE"
        print(f"   ID {user[0]}: {user[1]:15} | {user[2]:20} | Role: {user[3]:10} | {status}")
else:
    print("   No users found!")

conn.close()
print("\n✨ Done!")
