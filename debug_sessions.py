#!/usr/bin/env python3
"""
Detaylı user & session analizi
"""
import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv('.env.production')
DATABASE_URL = os.getenv('DATABASE_URL')

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("\n" + "="*80)
print("📋 DETAY KONTROL")
print("="*80)

# 1. USER 1 kimdir?
cursor.execute("SELECT id, username, full_name, role FROM users WHERE id = 1")
user1 = cursor.fetchone()
if user1:
    print(f"\n👤 USER 1: {user1[1]} ({user1[2]}) - Role: {user1[3]}")
else:
    print("\n⚠️  USER 1 VAR MI? YALNIZ SILINMIS")

# 2. Tüm user'lar
print("\n👥 TÜM KULLANICILAR:")
cursor.execute("""
    SELECT id, username, full_name, role, created_at 
    FROM users 
    ORDER BY id
""")
for user_id, username, full_name, role, created_at in cursor.fetchall():
    print(f"  {user_id} | {username:20} | {full_name:30} | {role:10} | {created_at}")

# 3. Son session'lar (daha çok bilgi)
print("\n📊 SON 10 COUNT SESSION:")
cursor.execute("""
    SELECT 
        session_id, 
        created_by, 
        status, 
        created_at, 
        finished_at,
        (SELECT u.username FROM users u WHERE u.id = count_sessions.created_by) as creator
    FROM count_sessions 
    ORDER BY created_at DESC 
    LIMIT 10
""")
for session_id, created_by, status, created_at, finished_at, creator in cursor.fetchall():
    print(f"  {session_id[:12]}... | By: {creator or f'USER {created_by} (DELETED)'} | {status:10} | {created_at}")
    if finished_at:
        print(f"    └─ Bittiği: {finished_at}")

# 4. scan history for debugging
print("\n📱 SCAN GECMISI (son 10):")
cursor.execute("""
    SELECT 
        s.qr_id, 
        s.part_code,
        (SELECT u.username FROM users u WHERE u.id = s.scanned_by) as scanned_by,
        s.scanned_at,
        s.session_id
    FROM scanned_qr s
    ORDER BY s.scanned_at DESC
    LIMIT 10
""")
for qr_id, part_code, scanned_by, scanned_at, session_id in cursor.fetchall():
    print(f"  {qr_id[:12]}... | {part_code} | By: {scanned_by} | {scanned_at}")

cursor.close()
conn.close()

print("\n" + "="*80)
