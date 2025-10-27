import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# İlk geçiş: ? parametrelerini %s ile değiştir
content = re.sub(r'\?', '%s', content)

# İkinci geçiş: Çakışan tırnaklı durumları düzelt
# cursor.execute('...'active'...') -> cursor.execute("...'active'...")
patterns = [
    (r"cursor\.execute\('([^']*)'active'([^']*)'\)", r'cursor.execute("\1\'active\'\2")'),
    (r"cursor\.execute\('([^']*)'completed'([^']*)'\)", r'cursor.execute("\1\'completed\'\2")'),
    (r"cursor\.execute\('([^']*)'admin'([^']*)'\)", r'cursor.execute("\1\'admin\'\2")'),
    (r"cursor\.execute\('([^']*)'user'([^']*)'\)", r'cursor.execute("\1\'user\'\2")'),
]

for pattern, replacement in patterns:
    content = re.sub(pattern, replacement, content)

# conn.close() çağrılarını close_db(conn) ile değiştir
content = re.sub(r'conn\.close\(\)', 'close_db(conn)', content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('PostgreSQL syntax fixed successfully!')