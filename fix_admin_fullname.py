import sqlite3

# Fix admin user's full_name
conn = sqlite3.connect('instance/envanter_local.db')
cursor = conn.cursor()

# Update admin user's full_name
cursor.execute("UPDATE envanter_users SET full_name = 'Administrator' WHERE username = 'admin'")
conn.commit()

# Verify the update
cursor.execute("SELECT username, full_name, role FROM envanter_users WHERE username = 'admin'")
admin = cursor.fetchone()
print(f"✅ Updated admin user: {admin}")

conn.close()
print("✅ Admin user full_name updated successfully")