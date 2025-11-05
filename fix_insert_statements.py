#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

# app.py dosyasını oku
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. INSERT INTO count_sessions - session_id → session_name veya kaldır
# "INSERT INTO count_sessions (id, status, created_by)" → "INSERT INTO count_sessions (created_by, is_active)"
content = re.sub(
    r"INSERT INTO count_sessions \(id, status, created_by\) VALUES \(%s, %s, %s\)",
    "INSERT INTO count_sessions (created_by, is_active) VALUES (%s, %s)",
    content
)

# 2. Değeri değiştir: (session_id, 'active', user_id) → (user_id, 1)
content = re.sub(
    r"\(session_id, 'active', user_id\)",
    "(user_id, 1)",
    content
)

# 3. INSERT INTO inventory_data - session_id → id olarak düzelt (session_id referansı kalacak)
# "INSERT INTO inventory_data (id, part_code, part_name, expected_quantity)" → 
# "INSERT INTO inventory_data (session_id, part_code, part_name, expected_quantity)"
content = re.sub(
    r"INSERT INTO inventory_data \(id, part_code, part_name, expected_quantity\) VALUES \(%s, %s, %s, %s\)",
    "INSERT INTO inventory_data (session_id, part_code, part_name, expected_quantity) VALUES (%s, %s, %s, %s)",
    content
)

# 4. INSERT INTO count_passwords - session_id ekle, id sütununu kaldır
# "INSERT INTO count_passwords (id, password, created_by)" →
# "INSERT INTO count_passwords (session_id, password, created_by)"
content = re.sub(
    r"INSERT INTO count_passwords \(id, password, created_by\) VALUES \(%s, %s, %s\)",
    "INSERT INTO count_passwords (session_id, password, created_by) VALUES (%s, %s, %s)",
    content
)

# 5. INSERT INTO scanned_qr - session_id sütun adı kullan
# "INSERT INTO scanned_qr (id, qr_id, part_code, scanned_by)" →
# "INSERT INTO scanned_qr (session_id, qr_id, part_code, scanned_by)"
content = re.sub(
    r"INSERT INTO scanned_qr \(id, qr_id, part_code, scanned_by\) VALUES \(%s, %s, %s, %s\)",
    "INSERT INTO scanned_qr (session_id, qr_id, part_code, scanned_by) VALUES (%s, %s, %s, %s)",
    content
)

# app.py dosyasını geri yaz
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Tüm INSERT ifadeleri düzeltildi!")
print("   - count_sessions: session_id → (auto-id), status='active' → is_active=1  ✓")
print("   - inventory_data: id → session_id referansı  ✓")
print("   - count_passwords: id → session_id referansı  ✓")
print("   - scanned_qr: id → session_id referansı  ✓")
