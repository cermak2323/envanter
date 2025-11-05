🗄️ PgAdmin4'ta PostgreSQL Kolon Ekleme Rehberi
================================================

## ADIM 1: PgAdmin4'ta Veritabanına Bağlan

1. PgAdmin4'ı aç (http://localhost/pgadmin4)
2. Sol panelde Servers → Render PostgreSQL (veya senin server adı)
3. Şifreni gir ve bağlan
4. Databases → inventory_management (veya database adı)

---

## ADIM 2: Eksik Kolonları Kontrol Et

### Seçenek A: GUI ile (Kolay)

1. Left panel'de: Schemas → public → Tables
2. Tıkla: `inventory_data` tablosuna sağ tıkla
3. "View Data" veya "Properties" seç
4. Kolonları gözle - eksik olanları not et

### Seçenek B: SQL Query ile (Hızlı)

1. Top menu: Tools → Query Tool
2. Aşağıdaki SQL'i yapıştır:

```sql
-- inventory_data'nın tüm kolonlarını gör
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'inventory_data' 
ORDER BY ordinal_position;
```

3. Execute (F5 veya ▶️ buton)
4. Sonucu gözle

---

## ADIM 3: Eksik Kolonları Ekle

### Seçenek A: GUI ile (Kolay ama yavaş)

1. Left panel: Schemas → public → Tables → inventory_data
2. Sağ tıkla: "Properties"
3. Columns tab'ına git
4. "+" butonuna tıkla
5. Her kolon için:
   - Name: `part_code`
   - Data Type: `character varying(255)`
   - NOT NULL: unchecked (optional)
   - Save

### Seçenek B: SQL Query ile (Hızlı) ✅ ÖNERİLEN

1. Tools → Query Tool
2. Aşağıdaki SQL'i yapıştır:

```sql
-- Eksik kolonları ekle
ALTER TABLE inventory_data
ADD COLUMN IF NOT EXISTS part_code VARCHAR(255);

ALTER TABLE inventory_data
ADD COLUMN IF NOT EXISTS part_name VARCHAR(255);

ALTER TABLE inventory_data
ADD COLUMN IF NOT EXISTS qr_id VARCHAR(255);

ALTER TABLE inventory_data
ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);
```

3. Execute (F5)
4. Tamamlandı mesajı göreceksin

---

## ADIM 4: Değişiklikleri Doğrula

Query Tool'da çalıştır:

```sql
-- inventory_data'nın tüm kolonlarını gör
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'inventory_data' 
ORDER BY ordinal_position;
```

**Beklenen sonuç:**
```
column_name          | data_type
─────────────────────┼───────────────
id                   | integer
part_code            | character varying
part_name            | character varying
qr_id                | character varying
session_id           | character varying
[diğer kolonlar]     | [diğer tipler]
```

---

## 🆘 SORUN GIDERME

### Error: "column already exists"
→ OK, kolon zaten var. Devam et.

### Error: "permission denied"
→ User'ın ALTER TABLE yetkisi yok
→ Admin hesapla giriş yap

### Error: "relation does not exist"
→ Tablo adı yanlış
→ `SELECT * FROM information_schema.tables WHERE table_schema = 'public'` ile tabloları listele

---

## ✅ HER ŞEY TAMAMLANDI MI?

Kontrol et:

```sql
-- inventory_data son kontrol
SELECT COUNT(*) as total_rows FROM inventory_data;
SELECT COUNT(DISTINCT part_code) as distinct_part_codes FROM inventory_data;

-- scanned_qr son kontrol  
SELECT COUNT(*) as total_scanned FROM scanned_qr;
SELECT * FROM scanned_qr LIMIT 5;
```

---

## 📝 NOT

Bu kolonlar eklendikten sonra:
- QR taraması çalışacak ✅
- Activity list yüklenecek ✅
- Veritabanı hataları gözükmeyecek ✅
- Frontend'de tüm veriler görülecek ✅

Yapıştır ve çalıştır! 🚀
