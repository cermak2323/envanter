#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('instance/envanter_local.db')
cursor = conn.cursor()

print('📋 DATABASE TABLES:')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f'  📊 {table[0]}')

print('\n📊 QR_CODES TABLO YAPISI:')  
cursor.execute('PRAGMA table_info(qr_codes)')
columns = cursor.fetchall()
for col in columns:
    print(f'  📝 {col[1]} ({col[2]})')

print('\n📊 PARTS TABLO YAPISI:')  
cursor.execute('PRAGMA table_info(parts)')
columns = cursor.fetchall()
for col in columns:
    print(f'  📝 {col[1]} ({col[2]})')

print('\n📊 MEVCUT QR CODES:')  
cursor.execute('SELECT part_code, COUNT(*) as qr_count FROM qr_codes GROUP BY part_code')
qr_counts = cursor.fetchall()
for qr in qr_counts:
    print(f'  {qr[0]}: {qr[1]} QR kod')

total_qr = sum(qr[1] for qr in qr_counts) if qr_counts else 0
print(f'\nToplam QR Codes: {total_qr}')
    
conn.close()