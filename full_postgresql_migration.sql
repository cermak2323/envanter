-- PostgreSQL Full Migration Script
-- Önce tabloları oluşturur, sonra eksik kolonları ekler

-- ===========================================
-- 1. PART_CODES TABLOSU OLUŞTUR
-- ===========================================
CREATE TABLE IF NOT EXISTS part_codes (
    id SERIAL PRIMARY KEY,
    part_code VARCHAR(50) UNIQUE NOT NULL,
    part_name VARCHAR(200),
    description TEXT,
    quantity INTEGER DEFAULT 0,
    unit VARCHAR(20),
    location VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Mevcut yapıyı kontrol et
SELECT 'part_codes table created:' as table_info;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'part_codes' 
ORDER BY ordinal_position;

-- ===========================================
-- 2. QR_CODES TABLOSU OLUŞTUR
-- ===========================================
CREATE TABLE IF NOT EXISTS qr_codes (
    id SERIAL PRIMARY KEY,
    qr_code VARCHAR(255) UNIQUE NOT NULL,
    part_code_id INTEGER REFERENCES part_codes(id),
    individual_code VARCHAR(255),
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    used_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

SELECT 'qr_codes table created:' as table_info;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'qr_codes' 
ORDER BY ordinal_position;

-- ===========================================
-- 3. COUNT_SESSIONS TABLOSU OLUŞTUR/GÜNCELLE
-- ===========================================
CREATE TABLE IF NOT EXISTS count_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    created_by INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);

-- Eksik kolonları ekle (eğer tablo zaten varsa)
ALTER TABLE count_sessions ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;
ALTER TABLE count_sessions ADD COLUMN IF NOT EXISTS session_id VARCHAR(100) UNIQUE;
ALTER TABLE count_sessions ADD COLUMN IF NOT EXISTS created_by INTEGER;
ALTER TABLE count_sessions ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
ALTER TABLE count_sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE count_sessions ADD COLUMN IF NOT EXISTS finished_at TIMESTAMP;

SELECT 'count_sessions table created:' as table_info;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'count_sessions' 
ORDER BY ordinal_position;

-- ===========================================
-- 4. SCANNED_QR TABLOSU OLUŞTUR
-- ===========================================
CREATE TABLE IF NOT EXISTS scanned_qr (
    id SERIAL PRIMARY KEY,
    qr_code_id INTEGER REFERENCES qr_codes(id),
    session_id INTEGER REFERENCES count_sessions(id),
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scanned_by INTEGER,
    location VARCHAR(200),
    notes TEXT
);

SELECT 'scanned_qr table created:' as table_info;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'scanned_qr' 
ORDER BY ordinal_position;

-- ===========================================
-- 5. COUNT_PASSWORDS TABLOSU OLUŞTUR
-- ===========================================
CREATE TABLE IF NOT EXISTS count_passwords (
    id SERIAL PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

SELECT 'count_passwords table created:' as table_info;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'count_passwords' 
ORDER BY ordinal_position;

-- ===========================================
-- 6. ENVANTER_USERS TABLOSU OLUŞTUR/GÜNCELLE
-- ===========================================
CREATE TABLE IF NOT EXISTS envanter_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Eksik kolonları ekle
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

-- Admin kullanıcısını oluştur/güncelle
-- Önce mevcut admin user'ı kontrol et:
SELECT 'Checking admin user:' as admin_check;
SELECT id, username, password_hash, full_name, role 
FROM envanter_users 
WHERE username = 'admin';

-- Admin user'ın password hash'ini güncelle veya oluştur
-- Bu hash "@R9t$L7e!xP2w" şifresinin Werkzeug hash'i:
UPDATE envanter_users 
SET password_hash = 'scrypt:32768:8:1$azpkdklq221BydYU$3d7b2715efb2a2829a7515c17a63ca8131071d32326b81e3f8cd768a24403ebe2ff6af591d09153125fef66ce535c08efe2fe40115f713923f4ac8e2681926b9' 
WHERE username = 'admin';

-- Mevcut admin user yoksa oluştur:
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

SELECT 'envanter_users table updated:' as table_info;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'envanter_users' 
ORDER BY ordinal_position;

-- ===========================================
-- 7. FOREIGN KEY CONSTRAINTS EKLE
-- ===========================================
-- Foreign key'leri güvenli şekilde ekle
-- Önce constraint var mı kontrol et, yoksa ekle

DO $$
BEGIN
    -- qr_codes -> part_codes
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_qr_codes_part_code_id' 
                   AND table_name = 'qr_codes') THEN
        ALTER TABLE qr_codes ADD CONSTRAINT fk_qr_codes_part_code_id 
        FOREIGN KEY (part_code_id) REFERENCES part_codes(id);
    END IF;

    -- qr_codes -> envanter_users
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_qr_codes_used_by' 
                   AND table_name = 'qr_codes') THEN
        ALTER TABLE qr_codes ADD CONSTRAINT fk_qr_codes_used_by 
        FOREIGN KEY (used_by) REFERENCES envanter_users(id);
    END IF;

    -- count_sessions -> envanter_users
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_count_sessions_created_by' 
                   AND table_name = 'count_sessions') THEN
        ALTER TABLE count_sessions ADD CONSTRAINT fk_count_sessions_created_by 
        FOREIGN KEY (created_by) REFERENCES envanter_users(id);
    END IF;

    -- scanned_qr -> qr_codes
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_scanned_qr_qr_code_id' 
                   AND table_name = 'scanned_qr') THEN
        ALTER TABLE scanned_qr ADD CONSTRAINT fk_scanned_qr_qr_code_id 
        FOREIGN KEY (qr_code_id) REFERENCES qr_codes(id);
    END IF;

    -- scanned_qr -> count_sessions
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_scanned_qr_session_id' 
                   AND table_name = 'scanned_qr') THEN
        ALTER TABLE scanned_qr ADD CONSTRAINT fk_scanned_qr_session_id 
        FOREIGN KEY (session_id) REFERENCES count_sessions(id);
    END IF;

    -- scanned_qr -> envanter_users
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_scanned_qr_scanned_by' 
                   AND table_name = 'scanned_qr') THEN
        ALTER TABLE scanned_qr ADD CONSTRAINT fk_scanned_qr_scanned_by 
        FOREIGN KEY (scanned_by) REFERENCES envanter_users(id);
    END IF;
END $$;

-- ===========================================
-- 8. FINAL CHECK - TÜM TABLOLARI KONTROL ET
-- ===========================================
SELECT '=== FINAL CHECK ===' as final_check;
SELECT table_name, 
       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
AND table_name IN ('part_codes', 'qr_codes', 'count_sessions', 'scanned_qr', 'envanter_users', 'count_passwords')
ORDER BY table_name;

-- Admin user kontrolü
SELECT '=== ADMIN USER CHECK ===' as admin_final;
SELECT id, username, full_name, role, is_active_user 
FROM envanter_users 
WHERE username = 'admin';

SELECT '=== MIGRATION COMPLETED SUCCESSFULLY ===' as completion;