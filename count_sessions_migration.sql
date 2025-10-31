-- count_sessions tablosu için migration
-- Bu SQL komutlarını da pgAdmin4'te çalıştırın

-- 1. count_sessions tablosunun mevcut yapısını kontrol edin
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'count_sessions' 
ORDER BY ordinal_position;

-- 2. Eksik kolonları ekleyin
ALTER TABLE count_sessions ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE count_sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE count_sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE count_sessions ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
ALTER TABLE count_sessions ADD COLUMN IF NOT EXISTS notes TEXT;

-- 3. Mevcut kayıtları güncelleyin (is_active = TRUE yapın)
UPDATE count_sessions SET is_active = TRUE WHERE is_active IS NULL;

-- 4. Son kontrol
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'count_sessions' 
ORDER BY ordinal_position;

-- 5. count_sessions tablosundaki kayıtları kontrol edin
SELECT * FROM count_sessions LIMIT 5;