-- 🔧 PostgreSQL Kolon Kontrolü ve Ekleme Script'i
-- PgAdmin4'ta çalıştırın

-- 1. inventory_data tablosunun yapısını kontrol et
\d inventory_data

-- 2. Eğer part_code kolonu yoksa ekle
ALTER TABLE inventory_data
ADD COLUMN IF NOT EXISTS part_code VARCHAR(255);

-- 3. Eğer part_name kolonu yoksa ekle
ALTER TABLE inventory_data
ADD COLUMN IF NOT EXISTS part_name VARCHAR(255);

-- 4. Eğer qr_id kolonu yoksa ekle
ALTER TABLE inventory_data
ADD COLUMN IF NOT EXISTS qr_id VARCHAR(255);

-- 5. Eğer session_id kolonu yoksa ekle
ALTER TABLE inventory_data
ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);

-- 6. scanned_qr tablosunun yapısını kontrol et
\d scanned_qr

-- 7. Tüm tabloların listesini gör
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- 8. inventory_data'nın tüm kolonlarını gör
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'inventory_data' 
ORDER BY ordinal_position;

-- 9. scanned_qr'ın tüm kolonlarını gör
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'scanned_qr' 
ORDER BY ordinal_position;
