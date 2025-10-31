#!/usr/bin/env python3
"""
Generate proper Werkzeug hash for @R9t$L7e!xP2w
"""
from werkzeug.security import generate_password_hash, check_password_hash

password = "@R9t$L7e!xP2w"

# Generate hash
hash_result = generate_password_hash(password)
print(f"Password: {password}")
print(f"Werkzeug Hash: {hash_result}")

# Test verification
test_result = check_password_hash(hash_result, password)
print(f"Verification Test: {test_result}")

print("\n" + "="*60)
print("PostgreSQL UPDATE komutu:")
print(f"UPDATE envanter_users SET password_hash = '{hash_result}' WHERE username = 'admin';")