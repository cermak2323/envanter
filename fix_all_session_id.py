#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

# app.py dosyasını oku
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ÖNEMLI: Sadece SQL sorgularında session_id → id değiştir
# Değişken isimleri, JSON keyleri vs. bırak

# 1. SQL INSERT INTO count_sessions - column adını değiştir (değişken DEĞİL)
content = re.sub(
    r"INSERT INTO count_sessions \(session_id,",
    "INSERT INTO count_sessions (id,",
    content
)

# 2. SQL INSERT INTO inventory_data - column adını değiştir
content = re.sub(
    r"INSERT INTO inventory_data \(session_id,",
    "INSERT INTO inventory_data (id,",
    content
)

# 3. SQL INSERT INTO count_passwords - column adını değiştir
content = re.sub(
    r"INSERT INTO count_passwords \(session_id,",
    "INSERT INTO count_passwords (id,",
    content
)

# 4. SQL INSERT INTO scanned_qr - column adını değiştir
content = re.sub(
    r"INSERT INTO scanned_qr \(session_id,",
    "INSERT INTO scanned_qr (id,",
    content
)

# 5. SQL WHERE session_id = - tüm WHERE cümlelerini değiştir
content = re.sub(
    r"WHERE session_id = %s",
    "WHERE id = %s",
    content
)

content = re.sub(
    r"WHERE session_id = \?",
    "WHERE id = ?",
    content
)

# 6. SQL JOIN cümlelerinde session_id → id
content = re.sub(
    r"i\.session_id = s\.session_id",
    "i.id = s.id",
    content
)

# 7. SQL SELECT - SELECT s.session_id → SELECT s.id
content = re.sub(
    r"SELECT s\.session_id,",
    "SELECT s.id,",
    content
)

# 8. UPDATE WHERE session_id = %s
content = re.sub(
    r"WHERE session_id = %s",
    "WHERE id = %s",
    content
)

# app.py dosyasını geri yaz
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ TÜM session_id SQL sütunu referansları id olarak değiştirildi!")
print("   - INSERT INTO ... (id, ...)  ✓")
print("   - WHERE id = ...              ✓")
print("   - JOIN ... id = ...           ✓")
print("   - SELECT ... id ...           ✓")
