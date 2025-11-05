import re

# app.py dosyasını oku
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# WHERE status = 'active' -> WHERE is_active = 1
content = content.replace("WHERE status = 'active'", "WHERE is_active = 1")
content = content.replace("WHERE status = \\'active\\'", "WHERE is_active = 1")

# WHERE status = %s', ('active',) -> WHERE is_active = %s', (1,)
content = content.replace("WHERE status = %s', ('active',)", "WHERE is_active = %s', (1,)")
content = content.replace("WHERE status = {placeholder}', ('active',)", "WHERE is_active = {placeholder}', (1,)")

# SET status = 'completed' -> SET is_active = 0
content = content.replace("SET status = 'completed'", "SET is_active = 0")

# Kaydet
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Tüm status referansları is_active olarak değiştirildi')
