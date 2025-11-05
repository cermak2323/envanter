-- PostgreSQL Data Type Fix
-- Veri tipi uyumsuzluklarını düzeltir

-- ===========================================
-- 1. MEVCUT VERİ TİPLERİNİ KONTROL ET
-- ===========================================
SELECT 'Current data types:' as info;

-- count_sessions tablosu
SELECT 'count_sessions columns:' as table_name;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'count_sessions' 
ORDER BY ordinal_position;

-- scanned_qr tablosu  
SELECT 'scanned_qr columns:' as table_name;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'scanned_qr' 
ORDER BY ordinal_position;

-- qr_codes tablosu
SELECT 'qr_codes columns:' as table_name;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'qr_codes' 
ORDER BY ordinal_position;

-- ===========================================
-- 2. VERİ TİPİ DÜZELTME STRATEJİSİ
-- ===========================================
-- Seçenek 1: scanned_qr.session_id'yi INTEGER yap
-- Seçenek 2: count_sessions'da session_id kullan (VARCHAR)

-- Önce mevcut verileri kontrol edelim
SELECT 'Data check - count_sessions:' as data_info;
SELECT id, session_id, status FROM count_sessions LIMIT 5;

SELECT 'Data check - scanned_qr:' as data_info;  
-- Sadece mevcut kolonları kontrol et
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'scanned_qr' 
ORDER BY ordinal_position;

-- Mevcut veriler varsa göster (güvenli şekilde)
DO $$
BEGIN
    -- scanned_qr tablosundaki mevcut kayıtları kontrol et
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'scanned_qr') THEN
        -- Sadece kesinlikle var olan kolonları seç
        PERFORM * FROM scanned_qr LIMIT 1;
        RAISE NOTICE 'scanned_qr table exists and accessible';
    END IF;
EXCEPTION 
    WHEN OTHERS THEN
        RAISE NOTICE 'scanned_qr table access issue, continuing...';
END $$;

-- ===========================================
-- 3. EKSİK KOLONLARI ÖNCE EKLE
-- ===========================================
-- Önce eksik kolonları ekleyelim
SELECT 'Adding missing columns:' as step_info;

-- scanned_qr tablosuna eksik kolonları ekle
ALTER TABLE scanned_qr ADD COLUMN IF NOT EXISTS qr_code_id INTEGER;
ALTER TABLE scanned_qr ADD COLUMN IF NOT EXISTS session_id INTEGER; -- Direkt INTEGER olarak ekle
ALTER TABLE scanned_qr ADD COLUMN IF NOT EXISTS scanned_by INTEGER;
ALTER TABLE scanned_qr ADD COLUMN IF NOT EXISTS location VARCHAR(200);
ALTER TABLE scanned_qr ADD COLUMN IF NOT EXISTS notes TEXT;

-- qr_codes tablosuna eksik kolonları ekle  
ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS part_code_id INTEGER;
ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS individual_code VARCHAR(255);
ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS is_used BOOLEAN DEFAULT FALSE;
ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS used_at TIMESTAMP;
ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS used_by INTEGER;
ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS notes TEXT;

-- ===========================================
-- 4. VERİ TİPİ DÜZELTME (GÜVENLI YÖNTEM)
-- ===========================================
-- Artık session_id INTEGER olarak var, ama eğer VARCHAR olarak varsa düzelt

-- Mevcut veriler varsa yedek al
CREATE TABLE IF NOT EXISTS scanned_qr_backup AS 
SELECT * FROM scanned_qr;

-- session_id kolonunu güvenli şekilde düzelt
DO $$
BEGIN
    -- session_id'nin tipini kontrol et
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'scanned_qr' 
               AND column_name = 'session_id' 
               AND data_type = 'character varying') THEN
               
        -- VARCHAR ise INTEGER'a çevir
        BEGIN
            ALTER TABLE scanned_qr ALTER COLUMN session_id TYPE INTEGER USING session_id::integer;
            RAISE NOTICE 'session_id successfully converted from VARCHAR to INTEGER';
        EXCEPTION 
            WHEN OTHERS THEN
                -- Çevrilemezse, kolonu yeniden oluştur
                ALTER TABLE scanned_qr DROP COLUMN session_id;
                ALTER TABLE scanned_qr ADD COLUMN session_id INTEGER;
                RAISE NOTICE 'session_id column recreated as INTEGER';
        END;
    ELSE
        RAISE NOTICE 'session_id already INTEGER or properly typed';
    END IF;
END $$;

-- ===========================================
-- 4. QR_CODES İÇİN DE AYNI KONTROLÜ YAP
-- ===========================================
-- qr_code_id ve part_code_id için de kontrol
DO $$
BEGIN
    -- qr_code_id'yi integer yap (eğer değilse)
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'scanned_qr' 
               AND column_name = 'qr_code_id' 
               AND data_type != 'integer') THEN
        ALTER TABLE scanned_qr ALTER COLUMN qr_code_id TYPE INTEGER USING qr_code_id::integer;
        RAISE NOTICE 'qr_code_id converted to INTEGER';
    END IF;
    
EXCEPTION 
    WHEN OTHERS THEN
        -- Alternatif: kolonu yeniden oluştur
        ALTER TABLE scanned_qr DROP COLUMN IF EXISTS qr_code_id;
        ALTER TABLE scanned_qr ADD COLUMN qr_code_id INTEGER;
        RAISE NOTICE 'qr_code_id column recreated as INTEGER';
END $$;

-- ===========================================
-- 5. GÜNCELLENMIŞ VERİ TİPLERİNİ KONTROL ET
-- ===========================================
SELECT 'Updated data types:' as info;

SELECT 'count_sessions after fix:' as table_name;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'count_sessions' 
ORDER BY ordinal_position;

SELECT 'scanned_qr after fix:' as table_name;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'scanned_qr' 
ORDER BY ordinal_position;

-- ===========================================
-- 6. FOREIGN KEY CONSTRAINTS (TEKRAR DENE)
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
    
    -- Şimdi doğru tiplerle tekrar ekle
    
    -- qr_codes -> part_codes
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_qr_codes_part_code_id' 
                   AND table_name = 'qr_codes') THEN
        ALTER TABLE qr_codes ADD CONSTRAINT fk_qr_codes_part_code_id 
        FOREIGN KEY (part_code_id) REFERENCES part_codes(id);
        RAISE NOTICE 'Added FK: qr_codes -> part_codes';
    END IF;

    -- qr_codes -> envanter_users
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_qr_codes_used_by' 
                   AND table_name = 'qr_codes') THEN
        ALTER TABLE qr_codes ADD CONSTRAINT fk_qr_codes_used_by 
        FOREIGN KEY (used_by) REFERENCES envanter_users(id);
        RAISE NOTICE 'Added FK: qr_codes -> envanter_users';
    END IF;

    -- count_sessions -> envanter_users
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_count_sessions_created_by' 
                   AND table_name = 'count_sessions') THEN
        ALTER TABLE count_sessions ADD CONSTRAINT fk_count_sessions_created_by 
        FOREIGN KEY (created_by) REFERENCES envanter_users(id);
        RAISE NOTICE 'Added FK: count_sessions -> envanter_users';
    END IF;

    -- scanned_qr -> qr_codes
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_scanned_qr_qr_code_id' 
                   AND table_name = 'scanned_qr') THEN
        ALTER TABLE scanned_qr ADD CONSTRAINT fk_scanned_qr_qr_code_id 
        FOREIGN KEY (qr_code_id) REFERENCES qr_codes(id);
        RAISE NOTICE 'Added FK: scanned_qr -> qr_codes';
    END IF;

    -- scanned_qr -> count_sessions (şimdi integer olmalı)
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_scanned_qr_session_id' 
                   AND table_name = 'scanned_qr') THEN
        ALTER TABLE scanned_qr ADD CONSTRAINT fk_scanned_qr_session_id 
        FOREIGN KEY (session_id) REFERENCES count_sessions(id);
        RAISE NOTICE 'Added FK: scanned_qr -> count_sessions';
    END IF;

    -- scanned_qr -> envanter_users
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_scanned_qr_scanned_by' 
                   AND table_name = 'scanned_qr') THEN
        ALTER TABLE scanned_qr ADD CONSTRAINT fk_scanned_qr_scanned_by 
        FOREIGN KEY (scanned_by) REFERENCES envanter_users(id);
        RAISE NOTICE 'Added FK: scanned_qr -> envanter_users';
    END IF;

END $$;

-- ===========================================
-- 7. FINAL CHECK
-- ===========================================
SELECT '=== DATA TYPE FIX COMPLETED ===' as completion;

-- Foreign key constraints kontrolü
SELECT '=== FOREIGN KEYS AFTER FIX ===' as fk_check;
SELECT conname as constraint_name, 
       conrelid::regclass as table_name,
       confrelid::regclass as referenced_table
FROM pg_constraint 
WHERE contype = 'f' 
AND conrelid::regclass::text IN ('qr_codes', 'count_sessions', 'scanned_qr')
ORDER BY table_name;

-- Admin user final check
SELECT '=== ADMIN USER ===' as admin_check;
SELECT id, username, full_name, role, is_active_user 
FROM envanter_users 
WHERE username = 'admin';