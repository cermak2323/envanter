import sqlite3

conn = sqlite3.connect('inventory.db')
cursor = conn.cursor()

cursor.execute('SELECT session_id, status, started_at FROM count_sessions')
sessions = cursor.fetchall()

print('Tüm oturumlar:')
if sessions:
    for s in sessions:
        print(f'ID: {s[0]}, Status: {s[1]}, Started: {s[2]}')
else:
    print('Hiç oturum yok')

conn.close()