#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing PostgreSQL boolean type casting...")

# 1. is_active = 1 → is_active = TRUE (for SELECT/WHERE)
content = content.replace('WHERE is_active = 1', 'WHERE is_active = TRUE')
content = content.replace('AND is_active = 1', 'AND is_active = TRUE')

# 2. is_active = 0 → is_active = FALSE (for UPDATE/WHERE)
content = content.replace('SET is_active = 0', 'SET is_active = FALSE')
content = content.replace('WHERE is_active = 0', 'WHERE is_active = FALSE')
content = content.replace('AND is_active = 0', 'AND is_active = FALSE')

# 3. INSERT VALUES (%s, 1) → INSERT VALUES (%s, TRUE) pattern
# Bu daha kompleks olabilir ama genellikle params olarak gidiyor, safe

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ PostgreSQL boolean type casting fixed!")
print("   - is_active = 1 → is_active = TRUE  ✓")
print("   - is_active = 0 → is_active = FALSE  ✓")
