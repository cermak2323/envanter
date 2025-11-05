#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# app.py dosyasını oku
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# envanter_envanter_users → envanter_users (çift hatasını düzelt)
content = content.replace('envanter_envanter_users', 'envanter_users')

# Diğer hataları düzelt
# required_tables 'users' → 'envanter_users'
content = content.replace("required_tables = ['users',", "required_tables = ['envanter_users',")

# CREATE INDEX idx_users → idx_envanter_users
content = content.replace("idx_users_username ON users(username)", "idx_envanter_users_username ON envanter_users(username)")
content = content.replace("idx_users_is_active ON users(is_active)", "idx_envanter_users_is_active ON envanter_users(is_active_user)")

# app.py dosyasını geri yaz
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Tüm users tablosu hataları düzeltildi!")
print("   - envanter_envanter_users → envanter_users  ✓")
print("   - required_tables users → envanter_users  ✓")
print("   - CREATE INDEX corrections  ✓")
