-- Fix Session ID Data Type Mismatch
-- session_id alanının veri tipi çakışmasını çözer

-- ===========================================
-- 1. MEVCUT VERİ TİPLERİNİ KONTROL ET
-- ===========================================
SELECT 'Current session_id types:' as info;

-- count_sessions tablosunda session_id nasıl?
SELECT 'count_sessions.session_id type:' as table_info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'count_sessions' AND column_name = 'session_id';

-- scanned_qr tablosunda session_id nasıl?
SELECT 'scanned_qr.session_id type:' as table_info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'scanned_qr' AND column_name = 'session_id';

-- Mevcut session verilerini kontrol et
SELECT 'Sample count_sessions data:' as data_info;
SELECT id, session_id, status FROM count_sessions LIMIT 5;

-- ===========================================
-- 2. SESSION_ID VERİ TİPİ DÜZELTME
-- ===========================================
DO $$
BEGIN
    RAISE NOTICE 'Fixing session_id data type mismatch...';
    
    -- Önce scanned_qr tablosundaki session_id'yi VARCHAR yap
    -- Çünkü UUID string'leri geliyor
    
    -- Eğer session_id INTEGER ise VARCHAR'a çevir
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'scanned_qr' 
               AND column_name = 'session_id' 
               AND data_type = 'integer') THEN
        
        -- Mevcut foreign key'i kaldır
        ALTER TABLE scanned_qr DROP CONSTRAINT IF EXISTS fk_scanned_qr_session_id;
        
        -- session_id'yi VARCHAR'a çevir
        ALTER TABLE scanned_qr ALTER COLUMN session_id TYPE VARCHAR(255);
        RAISE NOTICE 'Converted scanned_qr.session_id to VARCHAR';
        
    END IF;
    
    -- count_sessions tablosunda da session_id VARCHAR olmalı
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'count_sessions' 
                   AND column_name = 'session_id') THEN
        -- session_id kolonu yoksa ekle
        ALTER TABLE count_sessions ADD COLUMN session_id VARCHAR(255) UNIQUE;
        RAISE NOTICE 'Added session_id column to count_sessions';
    ELSE
        -- Varsa ama INTEGER ise VARCHAR'a çevir
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'count_sessions' 
                   AND column_name = 'session_id' 
                   AND data_type = 'integer') THEN
            ALTER TABLE count_sessions ALTER COLUMN session_id TYPE VARCHAR(255);
            RAISE NOTICE 'Converted count_sessions.session_id to VARCHAR';
        END IF;
    END IF;
    
EXCEPTION 
    WHEN OTHERS THEN
        RAISE NOTICE 'Error in session_id type conversion: %', SQLERRM;
END $$;

-- ===========================================
-- 3. SESSION_ID DEĞERLERİNİ GÜNCELLE
-- ===========================================
DO $$
BEGIN
    -- count_sessions'daki boş session_id'leri UUID ile doldur
    UPDATE count_sessions 
    SET session_id = gen_random_uuid()::text 
    WHERE session_id IS NULL OR session_id = '';
    
    RAISE NOTICE 'Updated empty session_id values in count_sessions';
    
EXCEPTION 
    WHEN OTHERS THEN
        RAISE NOTICE 'Error updating session_id values: %', SQLERRM;
END $$;

-- ===========================================
-- 4. YENİ FOREIGN KEY KURALINI GÜNCELLE
-- ===========================================
DO $$
BEGIN
    -- scanned_qr -> count_sessions foreign key'ini session_id ile kur
    -- Ama bu sefer id değil, session_id alanı ile
    
    -- Önce constraint'i kaldır
    ALTER TABLE scanned_qr DROP CONSTRAINT IF EXISTS fk_scanned_qr_session_id;
    
    -- Yeni constraint ekle (session_id -> session_id)
    ALTER TABLE scanned_qr 
    ADD CONSTRAINT fk_scanned_qr_session_id 
    FOREIGN KEY (session_id) REFERENCES count_sessions(session_id);
    
    RAISE NOTICE 'Added FK: scanned_qr.session_id -> count_sessions.session_id';
    
EXCEPTION 
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not add session_id foreign key: %', SQLERRM;
END $$;

-- ===========================================
-- 5. FİNAL KONTROL
-- ===========================================
SELECT 'Updated session_id types:' as final_info;

SELECT 'count_sessions.session_id final:' as table_info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'count_sessions' AND column_name = 'session_id';

SELECT 'scanned_qr.session_id final:' as table_info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'scanned_qr' AND column_name = 'session_id';

-- Sample data check
SELECT 'count_sessions sample data:' as sample_info;
SELECT id, session_id, status FROM count_sessions LIMIT 3;

SELECT 'Session ID type fix completed!' as completion;