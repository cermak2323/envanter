-- PostgreSQL Migration Script for envanter_users table
-- Bu SQL komutlarını pgAdmin4'te çalıştırın

-- 1. Önce mevcut tabloyu kontrol edin
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'envanter_users' 
ORDER BY ordinal_position;

-- 2. Eksik kolonları ekleyin
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS real_name VARCHAR(255);
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS job_title VARCHAR(120);
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS title VARCHAR(120);
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS work_position VARCHAR(120);
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS user_group VARCHAR(120);
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS user_role VARCHAR(120);
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS signature_path VARCHAR(500);
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS profile_image_path VARCHAR(500);
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS is_active_user BOOLEAN DEFAULT TRUE;
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS can_mark_used BOOLEAN DEFAULT FALSE;
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS email_2fa_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS email_2fa_code VARCHAR(10);
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS email_2fa_expires TIMESTAMP;
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS email_2fa_attempts INTEGER DEFAULT 0;
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS email_2fa_locked_until TIMESTAMP;
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS tc_number VARCHAR(20);
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS last_password_change TIMESTAMP;
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS force_password_change BOOLEAN DEFAULT FALSE;
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS force_tutorial BOOLEAN DEFAULT TRUE;
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS first_login_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN DEFAULT FALSE;
ALTER TABLE envanter_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 3. Admin kullanıcısının password hash'ini güncelleyin
-- (Werkzeug hash'i manuel olarak oluşturacağız)
-- Önce mevcut admin user'ı kontrol edin:
SELECT id, username, password_hash, full_name, role 
FROM envanter_users 
WHERE username = 'admin';

-- 4. Admin user'ın password hash'ini güncelleyin
-- Bu hash "@R9t$L7e!xP2w" şifresinin Werkzeug hash'i:
UPDATE envanter_users 
SET password_hash = 'scrypt:32768:8:1$azpkdklq221BydYU$3d7b2715efb2a2829a7515c17a63ca8131071d32326b81e3f8cd768a24403ebe2ff6af591d09153125fef66ce535c08efe2fe40115f713923f4ac8e2681926b9' 
WHERE username = 'admin';

-- 5. Mevcut admin user yoksa oluşturun:
INSERT INTO envanter_users (
    username, 
    password_hash, 
    full_name, 
    role, 
    created_at, 
    is_active_user
) 
SELECT 
    'admin',
    'scrypt:32768:8:1$azpkdklq221BydYU$3d7b2715efb2a2829a7515c17a63ca8131071d32326b81e3f8cd768a24403ebe2ff6af591d09153125fef66ce535c08efe2fe40115f713923f4ac8e2681926b9',
    'Administrator',
    'admin',
    CURRENT_TIMESTAMP,
    TRUE
WHERE NOT EXISTS (SELECT 1 FROM envanter_users WHERE username = 'admin');

-- 6. Son kontrol - admin user'ı doğrulayın:
SELECT id, username, password_hash, full_name, role, is_active_user 
FROM envanter_users 
WHERE username = 'admin';

-- 7. Tüm kolonları kontrol edin:
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'envanter_users' 
ORDER BY ordinal_position;