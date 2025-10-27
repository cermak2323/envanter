import sqlite3
import hashlib

conn = sqlite3.connect('inventory_qr.db')
cursor = conn.cursor()

# Admin şifresini "admin" olarak sıfırla
new_password = "admin"
new_hash = hashlib.sha256(new_password.encode()).hexdigest()

print(f"Yeni şifre hash: {new_hash}")

cursor.execute('UPDATE users SET password_hash = ? WHERE username = ?', (new_hash, 'admin'))
conn.commit()

print("Admin şifresi 'admin' olarak güncellendi!")

# Verify
cursor.execute('SELECT username, password_hash FROM users WHERE username = ?', ('admin',))
user = cursor.fetchone()
if user:
    print(f"Güncellenmiş hash: {user[1]}")

conn.close()