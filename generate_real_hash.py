from werkzeug.security import generate_password_hash

# @R9t$L7e!xP2w için doğru hash üret
password = "@R9t$L7e!xP2w"
hash_value = generate_password_hash(password)

print(f"Password: {password}")
print(f"Hash: {hash_value}")