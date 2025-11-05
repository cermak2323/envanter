-- PostgreSQL Parts Table Fix
-- parts tablosunu düzgün şekilde oluşturur

-- ===========================================
-- 1. PARTS TABLOSUNU DÜZELT
-- ===========================================

-- Mevcut parts tablosunun yapısını kontrol et
SELECT 'Current parts table structure:' as info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'parts' 
ORDER BY ordinal_position;

-- parts tablosuna eksik kolonları ekle
DO $$
BEGIN
    -- description kolonu ekle
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'parts' AND column_name = 'description') THEN
        ALTER TABLE parts ADD COLUMN description TEXT;
        RAISE NOTICE 'Added description column to parts';
    END IF;
    
    -- created_at kolonu ekle
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'parts' AND column_name = 'created_at') THEN
        ALTER TABLE parts ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE 'Added created_at column to parts';
    END IF;
    
    -- created_by kolonu ekle
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'parts' AND column_name = 'created_by') THEN
        ALTER TABLE parts ADD COLUMN created_by INTEGER;
        RAISE NOTICE 'Added created_by column to parts';
    END IF;
    
    -- is_active kolonu ekle
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'parts' AND column_name = 'is_active') THEN
        ALTER TABLE parts ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
        RAISE NOTICE 'Added is_active column to parts';
    END IF;
    
    -- updated_at kolonu ekle
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'parts' AND column_name = 'updated_at') THEN
        ALTER TABLE parts ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE 'Added updated_at column to parts';
    END IF;

EXCEPTION 
    WHEN OTHERS THEN
        RAISE NOTICE 'Error adding columns to parts: %', SQLERRM;
END $$;

-- ===========================================
-- 2. PARTS TABLOSU FOREIGN KEY
-- ===========================================
DO $$
BEGIN
    -- parts -> envanter_users foreign key
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'parts')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'envanter_users') THEN
        
        -- Önce mevcut constraint'i kaldır
        ALTER TABLE parts DROP CONSTRAINT IF EXISTS fk_parts_created_by;
        
        -- Yeni constraint ekle
        ALTER TABLE parts ADD CONSTRAINT fk_parts_created_by 
        FOREIGN KEY (created_by) REFERENCES envanter_users(id);
        RAISE NOTICE 'Added FK: parts -> envanter_users';
    END IF;

EXCEPTION 
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not add parts foreign key: %', SQLERRM;
END $$;

-- ===========================================
-- 3. GÜNCELLENMIŞ PARTS TABLOSU KONTROLÜ
-- ===========================================
SELECT 'Updated parts table structure:' as info;
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'parts' 
ORDER BY ordinal_position;

-- Mevcut parts verilerini kontrol et
SELECT 'Parts table data:' as data_info;
SELECT COUNT(*) as total_parts FROM parts;

SELECT * FROM parts LIMIT 5;

-- ===========================================
-- 4. PART_CODES VE PARTS İLİŞKİSİ
-- ===========================================
-- İki tablo arasında senkronizasyon sağla
DO $$
DECLARE
    rec RECORD;
BEGIN
    -- part_codes'dan parts'a veri kopyala (eğer parts boşsa)
    IF (SELECT COUNT(*) FROM parts) = 0 AND (SELECT COUNT(*) FROM part_codes) > 0 THEN
        INSERT INTO parts (part_code, part_name, description, created_at, created_by, is_active)
        SELECT part_code, part_code as part_name, description, created_at, created_by, is_active
        FROM part_codes;
        RAISE NOTICE 'Copied data from part_codes to parts';
    END IF;

EXCEPTION 
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not sync part_codes and parts: %', SQLERRM;
END $$;

-- ===========================================
-- 5. FİNAL KONTROL
-- ===========================================
SELECT '=== PARTS TABLE FIX COMPLETED ===' as completion;

-- Tüm kolonları listele
SELECT 'Final parts structure:' as final_check;
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'parts' 
ORDER BY ordinal_position;

-- Foreign key kontrolü
SELECT 'Parts foreign keys:' as fk_info;
SELECT conname as constraint_name, 
       conrelid::regclass as table_name,
       confrelid::regclass as referenced_table
FROM pg_constraint 
WHERE contype = 'f' 
AND conrelid::regclass::text = 'parts';

-- Son veri kontrolü
SELECT 'Parts data summary:' as data_summary;
SELECT COUNT(*) as total_parts, 
       COUNT(CASE WHEN is_active THEN 1 END) as active_parts
FROM parts;