#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing remaining boolean parameter values...")

# is_active = %s', (1,) → is_active = %s', (True,)
content = content.replace("is_active = %s', (1,)", "is_active = %s', (True,)")

# is_active = %s', (0,) → is_active = %s', (False,) 
content = content.replace("is_active = %s', (0,)", "is_active = %s', (False,)")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Boolean parameter values fixed!")
print("   - is_active = %s', (1,) → (True,)  ✓")
print("   - is_active = %s', (0,) → (False,)  ✓")
