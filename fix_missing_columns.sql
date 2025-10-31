-- PostgreSQL Missing Columns Fix
-- Mevcut tablolardaki eksik kolonları ekler

-- ===========================================
-- 1. QR_CODES TABLOSUNA EKSİK KOLONLARI EKLE
-- ===========================================
SELECT 'Fixing qr_codes table:' as fix_info;

-- Mevcut kolonları kontrol et
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'qr_codes' 
ORDER BY ordinal_position;

-- Eksik kolonları ekle
ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS part_code_id INTEGER;
ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS individual_code VARCHAR(255);
ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS is_used BOOLEAN DEFAULT FALSE;
ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS used_at TIMESTAMP;
ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS used_by INTEGER;
ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS notes TEXT;

-- Güncellenmiş yapıyı kontrol et
SELECT 'qr_codes columns after fix:' as after_fix;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'qr_codes' 
ORDER BY ordinal_position;

-- ===========================================
-- 2. SCANNED_QR TABLOSUNA EKSİK KOLONLARI EKLE  
-- ===========================================
SELECT 'Fixing scanned_qr table:' as fix_info;

-- Mevcut kolonları kontrol et
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'scanned_qr' 
ORDER BY ordinal_position;

-- Eksik kolonları ekle
ALTER TABLE scanned_qr ADD COLUMN IF NOT EXISTS qr_code_id INTEGER;
ALTER TABLE scanned_qr ADD COLUMN IF NOT EXISTS session_id INTEGER;
ALTER TABLE scanned_qr ADD COLUMN IF NOT EXISTS scanned_by INTEGER;
ALTER TABLE scanned_qr ADD COLUMN IF NOT EXISTS location VARCHAR(200);
ALTER TABLE scanned_qr ADD COLUMN IF NOT EXISTS notes TEXT;

-- Güncellenmiş yapıyı kontrol et
SELECT 'scanned_qr columns after fix:' as after_fix;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'scanned_qr' 
ORDER BY ordinal_position;

-- ===========================================
-- 3. PART_CODES TABLOSU VAR MI KONTROL ET
-- ===========================================
-- part_codes tablosu yoksa oluştur
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

SELECT 'part_codes table status:' as table_check;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'part_codes' 
ORDER BY ordinal_position;

-- ===========================================
-- 4. ADMIN USER PASSWORD HASH'İNİ GÜNCELLE
-- ===========================================
-- Admin user'ın password hash'ini güncelle
UPDATE envanter_users 
SET password_hash = 'scrypt:32768:8:1$azpkdklq221BydYU$3d7b2715efb2a2829a7515c17a63ca8131071d32326b81e3f8cd768a24403ebe2ff6af591d09153125fef66ce535c08efe2fe40115f713923f4ac8e2681926b9' 
WHERE username = 'admin';

-- Mevcut admin user yoksa oluştur
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

-- Admin user kontrolü
SELECT 'Admin user check:' as admin_info;
SELECT id, username, full_name, role, is_active_user 
FROM envanter_users 
WHERE username = 'admin';

-- ===========================================
-- 5. FOREIGN KEY CONSTRAINTS (TEKRAR DENE)
-- ===========================================
DO $$
BEGIN
    -- qr_codes -> part_codes (şimdi part_code_id kolonu var)
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
-- 6. FINAL CHECK
-- ===========================================
SELECT '=== MIGRATION FIX COMPLETED ===' as completion;

-- Tüm tabloların kolon sayısını kontrol et
SELECT table_name, 
       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
AND table_name IN ('part_codes', 'qr_codes', 'count_sessions', 'scanned_qr', 'envanter_users', 'count_passwords')
ORDER BY table_name;

-- Foreign key constraints kontrolü
SELECT '=== FOREIGN KEYS ===' as fk_check;
SELECT conname as constraint_name, 
       conrelid::regclass as table_name,
       confrelid::regclass as referenced_table
FROM pg_constraint 
WHERE contype = 'f' 
AND conrelid::regclass::text IN ('qr_codes', 'count_sessions', 'scanned_qr')
ORDER BY table_name;