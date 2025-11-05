-- PgAdmin4'te çalıştırılacak SQL Sorguları
-- M.Emir ERSÜT kullanıcısı login sorunları debug

-- 1. Tüm kullanıcıları göster
SELECT id, username, full_name, email, password, password_hash, role
FROM users
ORDER BY id;

-- 2. test1 kullanıcısının detayları
SELECT id, username, full_name, email, password, password_hash, role, created_at
FROM users
WHERE username = 'test1';

-- 3. Emir içeren kullanıcıları ara
SELECT id, username, full_name, password, password_hash
FROM users
WHERE full_name ILIKE '%Emir%' OR username ILIKE '%Emir%';

-- 4. Şifre doğru mu kontrol - '123456789' hash'i
SELECT id, username, full_name, password, password_hash
FROM users
WHERE password = '123456789';

-- 5. Username ve full_name görülüp görülmediğini kontrol
SELECT id, username, full_name, LENGTH(username) as username_len, LENGTH(full_name) as fullname_len
FROM users;

-- 6. Tüm username'leri hex formatında göster (encoding problemini tespit et)
SELECT id, username, convert_to(username, 'UTF8') as username_utf8, 
       full_name, convert_to(full_name, 'UTF8') as fullname_utf8
FROM users;
