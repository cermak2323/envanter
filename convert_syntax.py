import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ? parametrelerini %s ile değiştir
content = re.sub(r'\?', '%s', content)

# Double quotes'ları single quotes'a değiştir (SQL string literals için)
content = re.sub(r'"active"', "'active'", content)
content = re.sub(r'"completed"', "'completed'", content)
content = re.sub(r'"admin"', "'admin'", content)
content = re.sub(r'"user"', "'user'", content)

# conn.close() çağrılarını close_db(conn) ile değiştir
content = re.sub(r'conn\.close\(\)', 'close_db(conn)', content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('PostgreSQL syntax conversions completed successfully!')