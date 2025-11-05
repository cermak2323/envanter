-- Correct Admin Password Update
-- Doğru password hash ile admin günceller

-- ===========================================
-- DOĞRU ADMIN PASSWORD GÜNCELLEME
-- ===========================================

-- Mevcut admin durumu
SELECT 'Current admin before update:' as info;
SELECT id, username, password_hash, full_name, role, is_active_user 
FROM envanter_users 
WHERE username = 'admin';

-- Doğru hash ile güncelle
UPDATE envanter_users 
SET password_hash = 'scrypt:32768:8:1$m6ETExQ6kYe8TXEV$5a5ddeb310e27a9d6450b7c1a605d94a3f0a908d2189d14bc0b18e06248f997c00c7bc490b9803f30e4f6231a4d2d67cec6e03b65eed8dd3beac3f1ddd7c0068'
WHERE username = 'admin';

-- Güncellenmiş admin durumu
SELECT 'Admin after update:' as info;
SELECT id, username, password_hash, full_name, role, is_active_user 
FROM envanter_users 
WHERE username = 'admin';

SELECT 'Password update completed for: admin / @R9t$L7e!xP2w' as result;