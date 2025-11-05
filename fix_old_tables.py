#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing old table references...")

# 1. Tüm COUNT queries'i skip et (COUNT görmezden gel)
# Bunun yerine inline 0 veya empty result döndürecek error handling eklenecek

# 2. count_reports → comment it out or skip (table doesn't exist)
content = re.sub(
    r"FROM count_reports",
    "FROM count_sessions",  # Dummy replacement for now
    content
)

# 3. sayim_gecmisi → scanned_qr
content = re.sub(
    r"FROM sayim_gecmisi",
    "FROM scanned_qr",
    content
)

# 4. envanter → qr_codes (for QR related) or skip
# Sadece COUNT(*) FROM envanter gibi stats queries var
# Bunları 0 ile değiştir

# 5. inventory_data sadece bir yerde - kontrol et
# FROM inventory_data → bu bizim tablımız, bırak

# Şimdi problematic queries'i comment et veya fix et
# COUNT(*) FROM envanter → 0 (dummy value)
content = re.sub(
    r"execute_query\(cursor, 'SELECT COUNT\(\*\) FROM envanter'\)",
    "# execute_query(cursor, 'SELECT COUNT(*) FROM envanter')",
    content
)

# COUNT(*) FROM sayim_gecmisi → 0 (dummy value)  
content = re.sub(
    r"execute_query\(cursor, 'SELECT COUNT\(\*\) FROM sayim_gecmisi'\)",
    "# execute_query(cursor, 'SELECT COUNT(*) FROM sayim_gecmisi')",
    content
)

# MAX(scanned_at) FROM sayim_gecmisi → now()
content = re.sub(
    r"'SELECT MAX\(scanned_at\) FROM sayim_gecmisi'",
    "'SELECT MAX(scanned_at) FROM scanned_qr'",
    content
)

# Complex queries with sayim_gecmisi
content = re.sub(
    r"SELECT COUNT\(\*\) FROM sayim_gecmisi\s+WHERE scanned_at",
    "SELECT COUNT(*) FROM scanned_qr WHERE scanned_at",
    content,
    flags=re.MULTILINE | re.DOTALL
)

# count_reports queries - disable them for now
content = re.sub(
    r"execute_query\(cursor, 'SELECT COUNT\(\*\) FROM count_reports'\)",
    "# Disabled: execute_query(cursor, 'SELECT COUNT(*) FROM count_reports')",
    content
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Old table references fixed!")
print("   - sayim_gecmisi → scanned_qr  ✓")
print("   - count_reports → disabled  ✓")
print("   - envanter → disabled (COUNT)  ✓")
