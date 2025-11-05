-- PostgreSQL Missing Tables Fix
-- Eksik tabloları oluşturur ve foreign key'leri güvenli şekilde kurar

-- ===========================================
-- 1. EKSİK TABLOLARI OLUŞTUR
-- ===========================================

-- part_codes tablosunu oluştur (eğer yoksa)
CREATE TABLE IF NOT EXISTS part_codes (
    id SERIAL PRIMARY KEY,
    part_code VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(100),
    unit VARCHAR(50),
    min_stock INTEGER DEFAULT 0,
    max_stock INTEGER DEFAULT 100,
    current_stock INTEGER DEFAULT 0,
    location VARCHAR(200),
    supplier VARCHAR(200),
    cost DECIMAL(10,2),
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER -- Bu foreign key daha sonra kurulacak
);

-- ===========================================
-- 2. ÖRNEK VERİ EKLE
-- ===========================================
-- Eğer part_codes boşsa, örnek veri ekle
INSERT INTO part_codes (part_code, description, category, unit) 
SELECT 'SAMPLE001', 'Örnek Parça 1', 'Genel', 'Adet'
WHERE NOT EXISTS (SELECT 1 FROM part_codes);

INSERT INTO part_codes (part_code, description, category, unit) 
SELECT 'SAMPLE002', 'Örnek Parça 2', 'Genel', 'Adet'
WHERE NOT EXISTS (SELECT 1 FROM part_codes WHERE part_code = 'SAMPLE002');

-- ===========================================
-- 3. FOREIGN KEY'LERİ GÜVENLE KUR
-- ===========================================
DO $$
BEGIN
    -- Önce mevcut constraint'leri temizle
    ALTER TABLE scanned_qr DROP CONSTRAINT IF EXISTS fk_scanned_qr_session_id;
    ALTER TABLE scanned_qr DROP CONSTRAINT IF EXISTS fk_scanned_qr_qr_code_id;
    ALTER TABLE scanned_qr DROP CONSTRAINT IF EXISTS fk_scanned_qr_scanned_by;
    ALTER TABLE qr_codes DROP CONSTRAINT IF EXISTS fk_qr_codes_part_code_id;
    ALTER TABLE qr_codes DROP CONSTRAINT IF EXISTS fk_qr_codes_used_by;
    ALTER TABLE count_sessions DROP CONSTRAINT IF EXISTS fk_count_sessions_created_by;
    ALTER TABLE part_codes DROP CONSTRAINT IF EXISTS fk_part_codes_created_by;
    
    -- Şimdi tablo kontrolü yaparak foreign key'leri ekle
    
    -- 1. part_codes -> envanter_users (created_by)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'part_codes')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'envanter_users') THEN
        
        ALTER TABLE part_codes ADD CONSTRAINT fk_part_codes_created_by 
        FOREIGN KEY (created_by) REFERENCES envanter_users(id);
        RAISE NOTICE 'Added FK: part_codes -> envanter_users';
    END IF;
    
    -- 2. qr_codes -> part_codes (part_code_id)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'qr_codes')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'part_codes') THEN
        
        ALTER TABLE qr_codes ADD CONSTRAINT fk_qr_codes_part_code_id 
        FOREIGN KEY (part_code_id) REFERENCES part_codes(id);
        RAISE NOTICE 'Added FK: qr_codes -> part_codes';
    END IF;

    -- 3. qr_codes -> envanter_users (used_by)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'qr_codes')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'envanter_users') THEN
        
        ALTER TABLE qr_codes ADD CONSTRAINT fk_qr_codes_used_by 
        FOREIGN KEY (used_by) REFERENCES envanter_users(id);
        RAISE NOTICE 'Added FK: qr_codes -> envanter_users';
    END IF;

    -- 4. count_sessions -> envanter_users (created_by)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'count_sessions')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'envanter_users') THEN
        
        ALTER TABLE count_sessions ADD CONSTRAINT fk_count_sessions_created_by 
        FOREIGN KEY (created_by) REFERENCES envanter_users(id);
        RAISE NOTICE 'Added FK: count_sessions -> envanter_users';
    END IF;

    -- 5. scanned_qr -> qr_codes (qr_code_id)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'scanned_qr')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'qr_codes') THEN
        
        ALTER TABLE scanned_qr ADD CONSTRAINT fk_scanned_qr_qr_code_id 
        FOREIGN KEY (qr_code_id) REFERENCES qr_codes(id);
        RAISE NOTICE 'Added FK: scanned_qr -> qr_codes';
    END IF;

    -- 6. scanned_qr -> count_sessions (session_id) - artık INTEGER
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'scanned_qr')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'count_sessions') THEN
        
        ALTER TABLE scanned_qr ADD CONSTRAINT fk_scanned_qr_session_id 
        FOREIGN KEY (session_id) REFERENCES count_sessions(id);
        RAISE NOTICE 'Added FK: scanned_qr -> count_sessions';
    END IF;

    -- 7. scanned_qr -> envanter_users (scanned_by)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'scanned_qr')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'envanter_users') THEN
        
        ALTER TABLE scanned_qr ADD CONSTRAINT fk_scanned_qr_scanned_by 
        FOREIGN KEY (scanned_by) REFERENCES envanter_users(id);
        RAISE NOTICE 'Added FK: scanned_qr -> envanter_users';
    END IF;

EXCEPTION 
    WHEN OTHERS THEN
        RAISE NOTICE 'Some foreign keys could not be added: %', SQLERRM;
END $$;

-- ===========================================
-- 4. FİNAL KONTROL
-- ===========================================
SELECT '=== MISSING TABLES FIX COMPLETED ===' as completion;

-- Tüm tabloları listele
SELECT '=== ALL TABLES ===' as table_list;
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Foreign key constraints kontrolü
SELECT '=== FOREIGN KEYS AFTER FIX ===' as fk_check;
SELECT conname as constraint_name, 
       conrelid::regclass as table_name,
       confrelid::regclass as referenced_table
FROM pg_constraint 
WHERE contype = 'f' 
AND conrelid::regclass::text IN ('qr_codes', 'count_sessions', 'scanned_qr', 'part_codes')
ORDER BY table_name;

-- part_codes kontrolü
SELECT '=== PART_CODES TABLE ===' as part_codes_check;
SELECT * FROM part_codes LIMIT 5;

-- Admin user kontrolü
SELECT '=== ADMIN USER ===' as admin_check;
SELECT id, username, full_name, role, is_active_user 
FROM envanter_users 
WHERE username = 'admin';