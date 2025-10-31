#!/usr/bin/env python3
"""
Test Werkzeug password verification
"""
from werkzeug.security import check_password_hash

# Hash from database
stored_hash = "scrypt:32768:8:1$XzizVu2mBsuoH5b6$ffc08c781d40b18e3548c5645b151aef2be1a928c84866c6a5c62cc1e4de5ff97302bf164a8ad273c48bfd8067585a28224472a26b1e961ee81a847124eaf24e"

# Test password
test_password = "admin123"

print("🔐 Testing Werkzeug password verification...")
print(f"Password: {test_password}")
print(f"Hash: {stored_hash[:50]}...")

result = check_password_hash(stored_hash, test_password)
print(f"✅ Password check result: {result}")

if result:
    print("🎉 Password verification SUCCESSFUL!")
else:
    print("❌ Password verification FAILED!")