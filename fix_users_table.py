#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

# app.py dosyasını oku
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. FROM users → FROM envanter_users
content = content.replace('FROM users', 'FROM envanter_users')

# 2. JOIN users → JOIN envanter_users
content = content.replace('JOIN users', 'JOIN envanter_users')

# 3. LEFT JOIN users → LEFT JOIN envanter_users
content = content.replace('LEFT JOIN users', 'LEFT JOIN envanter_users')

# 4. users WHERE → envanter_users WHERE (for direct references)
content = re.sub(r"users\s+WHERE", "envanter_users WHERE", content)

# 5. INTO users → INTO envanter_users
content = content.replace('INTO users', 'INTO envanter_users')

# app.py dosyasını geri yaz
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Tüm users table referansları envanter_users olarak değiştirildi!")
print("   - FROM users → FROM envanter_users  ✓")
print("   - JOIN users → JOIN envanter_users  ✓")
print("   - INTO users → INTO envanter_users  ✓")
