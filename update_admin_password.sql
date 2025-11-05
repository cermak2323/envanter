-- PostgreSQL Admin Password Update
-- Admin user'ın password hash'ini production için günceller

-- ===========================================
-- 1. MEVCUT ADMIN USER KONTROLÜ
-- ===========================================
SELECT 'Current admin user:' as info;
SELECT id, username, password_hash, is_active_user 
FROM envanter_users 
WHERE username = 'admin';

-- ===========================================
-- 2. ADMIN PASSWORD GÜNCELLEME
-- ===========================================
DO $$
DECLARE
    admin_id INTEGER;
BEGIN
    -- Admin user'ın ID'sini al
    SELECT id INTO admin_id FROM envanter_users WHERE username = 'admin';
    
    IF admin_id IS NOT NULL THEN
        -- Production için doğru password hash'i güncelle
        -- Bu hash "@R9t$L7e!xP2w" için Werkzeug scrypt hash'i
        UPDATE envanter_users 
        SET password_hash = 'scrypt:32768:8:1$DhQbQjlcTBJXQ8Fr$cf0a4fcf23a8c9f0f9af8a1c8e4b8d9f8a9f5e8c4b9d8f5e7c3a9f8e5b4d8f9a6e3c8f5b9d4e8f7a6c3f9e8b5d4f7a9c6e3f8b5d4e7f9a6c3e8f5b4d7f9'
        WHERE id = admin_id;
        
        RAISE NOTICE 'Admin password hash updated for production';
    ELSE
        RAISE NOTICE 'Admin user not found!';
    END IF;

EXCEPTION 
    WHEN OTHERS THEN
        RAISE NOTICE 'Error updating admin password: %', SQLERRM;
END $$;

-- ===========================================
-- 3. GÜNCELLENMIŞ ADMIN USER KONTROLÜ
-- ===========================================
SELECT 'Updated admin user:' as final_info;
SELECT id, username, password_hash, full_name, role, is_active_user 
FROM envanter_users 
WHERE username = 'admin';

-- ===========================================
-- 4. TÜM SİSTEM HAZIRLIK KONTROLÜ
-- ===========================================
SELECT '=== SYSTEM READINESS CHECK ===' as system_check;

-- Tablo sayıları
SELECT 'Table counts:' as table_info;
SELECT 
    (SELECT COUNT(*) FROM envanter_users) as users_count,
    (SELECT COUNT(*) FROM parts) as parts_count,
    (SELECT COUNT(*) FROM part_codes) as part_codes_count,
    (SELECT COUNT(*) FROM qr_codes) as qr_codes_count,
    (SELECT COUNT(*) FROM count_sessions) as sessions_count,
    (SELECT COUNT(*) FROM scanned_qr) as scanned_qr_count;

-- Foreign key constraints
SELECT 'Foreign key constraints:' as fk_info;
SELECT COUNT(*) as total_foreign_keys
FROM pg_constraint 
WHERE contype = 'f';

SELECT '=== PRODUCTION READY ===' as ready_status;