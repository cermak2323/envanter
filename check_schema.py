#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

db_path = r"C:\Users\rsade\Desktop\Yeni klasör\EnvanterQR\EnvanterQR\EnvanterQR\EnvanterQR\instance\envanter_local.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 70)
print("DATABASE SCHEMA VERIFICATION")
print("=" * 70)

# 1. count_sessions schema
print("\n1️⃣ count_sessions tablosu:")
cursor.execute("PRAGMA table_info(count_sessions)")
for col in cursor.fetchall():
    print(f"   - {col[1]}: {col[2]}")

# 2. scanned_qr schema  
print("\n2️⃣ scanned_qr tablosu:")
cursor.execute("PRAGMA table_info(scanned_qr)")
for col in cursor.fetchall():
    print(f"   - {col[1]}: {col[2]}")

# 3. count_passwords schema
print("\n3️⃣ count_passwords tablosu:")
cursor.execute("PRAGMA table_info(count_passwords)")
for col in cursor.fetchall():
    print(f"   - {col[1]}: {col[2]}")

# 4. inventory_data schema (if exists)
try:
    print("\n4️⃣ inventory_data tablosu:")
    cursor.execute("PRAGMA table_info(inventory_data)")
    for col in cursor.fetchall():
        print(f"   - {col[1]}: {col[2]}")
except Exception as e:
    print(f"   ⚠️ Table not found: {e}")

# 5. Check for data
print("\n" + "=" * 70)
print("DATA COUNT")
print("=" * 70)
for table in ['count_sessions', 'scanned_qr', 'count_passwords']:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"✅ {table}: {count} rows")
    except Exception as e:
        print(f"❌ {table}: {e}")

conn.close()
print("\n✨ Done!")
