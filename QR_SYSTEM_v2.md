# 🎉 YENİ SISTEM - QR KOD YÖNETIMI & SQLAlchemy

## ✨ NEYİ DEĞİŞTİRDİK?

### 1. **SQLAlchemy ORM** (`models.py`)
- ✅ **SQLite (Lokal)** - Geliştirim ortamında
- ✅ **PostgreSQL (Production)** - Render.com'da
- ✅ Otomatik ortam algılama

#### Model Yapısı:
```
PartCode (Parça Kodları - SABİT)
  ├── part_code: Benzersiz
  ├── part_name
  └── qr_codes (ilişki)

QRCode (QR Kodlar - KALICI)
  ├── qr_id: Benzersiz
  ├── blob_url: B2 Storage (kalıcı)
  ├── blob_file_id: B2 File ID
  ├── is_used: Kullanıldı mı?
  └── used_count: Kaç kez kullanıldı?

CountSession & ScannedQR
  └── İşlem kayıtları
```

### 2. **Veritabanı Konfigürasyonu** (`db_config.py`)
```python
# Lokal (Development)
DATABASE: SQLite 
PATH: instance/envanter_local.db
MODIFIYE: Evet, test edebilirsiniz

# Production (Render.com)
DATABASE: PostgreSQL
URL: DATABASE_URL env var
MODIFIYE: Hayır, oradan yapınca aynı kalır
```

### 3. **QR Yönetim Paneli** (`qr_admin.py`)

#### A. Yeni QR Oluştur
```
POST /admin/qr/generate
Body: { "part_code": "17013-11030", "part_name": "Motor Başlığı" }
Response: QR kod + B2 URL (kalıcı link)
```

#### B. CSV Import (Mevcut QR'ları KORUR)
```
POST /admin/qr/import-csv
- Mevcut part code'ları atlar
- Sadece YENİ parçalar eklenir
- QR kodları asla silinmez ❌❌❌
```

#### C. QR Listele
```
GET /admin/qr/list?page=1&per_page=50
- Sayfalı sonuçlar
- Kullanım durumu
- B2 URL'leri
```

#### D. PDF Export
```
GET /admin/qr/export-pdf
- Tüm QR kodları bir PDF'te
- Parça kodları ve isimleri dahil
```

#### E. İstatistikler
```
GET /admin/qr/stats
- Toplam QR sayısı
- Kullanılan QR sayısı
- Bekleyen QR sayısı
- Kullanım yüzdesi
```

### 4. **Admin Panel UI** (`admin_qr_manage.html`)
- 🎨 Modern, responsive tasarım
- 📊 Canlı istatistikler
- ✨ Smooth animasyonlar
- 📱 Mobil uyumlu

---

## 🚀 NASIL KULLANILIR?

### Lokal Geliştirmede:
```bash
# 1. Bağımlılıkları yükle
pip install -r requirements.txt

# 2. Development modunda çalıştır
set FLASK_ENV=development
python app.py

# 3. Admin paneline git
http://localhost:5002/admin/qr
```

### Production (Render.com):
```bash
# DATABASE_URL zaten set
# SQLAlchemy otomatik PostgreSQL'i seçer
python app.py
```

---

## 💾 VERİTABANI MİGRASYONU

### Lokal SQLite'den Production PostgreSQL'e:

```bash
# 1. Lokal verileri dışa aktar
python -c "
from models import db, QRCode, PartCode
# Mevcut veriyi kontrol et
codes = QRCode.query.all()
print(f'Toplam QR: {len(codes)}')
"

# 2. Production'da tabil oluştur
python -c "
from app import app
with app.app_context():
    db.create_all()
    print('Tablolar oluşturuldu')
"

# 3. Verileri migrate et (manual veya script ile)
```

---

## 📌 ÖNEMLİ KURALLAR

### ✅ YAPILACAKLAR:
- ✅ Yeni part code'lar için yeni QR oluştur
- ✅ Mevcut QR'ları kalıcı tut
- ✅ B2 Storage'da backup tut
- ✅ CSV import yap, mevcut veriler açılmasın

### ❌ YAPILMAYACAKLAR:
- ❌ QR kodları SİLME
- ❌ İlişkili QR'ları DEĞIŞTIRME
- ❌ Mevcut part_code'u SİLME
- ❌ CSV import sırasında eski verileri TEMIZLEME

---

## 🔗 API ENDPOINTS

| Method | Endpoint | Açıklama |
|--------|----------|-----------|
| POST | `/admin/qr/generate` | Yeni QR oluştur |
| GET | `/admin/qr/list` | QR'ları listele |
| POST | `/admin/qr/import-csv` | CSV import (koruyucu) |
| GET | `/admin/qr/export-pdf` | PDF export |
| GET | `/admin/qr/stats` | İstatistikler |

---

## 🎯 ÖRNEKLERİ

### Örnek 1: Yeni QR Oluştur
```curl
curl -X POST http://localhost:5002/admin/qr/generate \
  -H "Content-Type: application/json" \
  -d '{"part_code":"12345-67890", "part_name":"Vites Kutusu"}'

Response:
{
  "success": true,
  "qr_id": "12345-67890-a1b2c3d4",
  "blob_url": "https://b2.cermakservis.com/qr-permanent/12345-67890-a1b2c3d4.png"
}
```

### Örnek 2: CSV Import
```csv
part_code,part_name
17013-11030,Motor Başlığı
15151-02112,Vites Kutusu
03960-16200,Motor Yağı Filtresi
```

---

## 📊 VERITABANI DIYAGRAMI

```
┌──────────────────┐
│   Part Codes     │
│  (SABİT & KALICI)│
├──────────────────┤
│ id (PK)          │
│ part_code (UK)   │
│ part_name        │
│ created_at       │
└────────┬─────────┘
         │
         │ 1:N
         │
┌────────▼──────────────────┐
│    QR Codes               │
│  (B2'DE KALICI & SORGU)  │
├──────────────────────────┤
│ id (PK)                  │
│ qr_id (UK)               │
│ part_code_id (FK)        │
│ blob_url (B2)            │
│ blob_file_id (B2)        │
│ is_used                  │
│ used_count               │
│ created_at               │
└────────┬──────────────────┘
         │
         │ 1:N
         │
┌────────▼─────────────────┐
│  Scanned QR              │
│  (İşlem Kayıtları)       │
├──────────────────────────┤
│ id (PK)                  │
│ session_id (FK)          │
│ qr_code_id (FK)          │
│ scanned_by (FK)          │
│ scanned_at               │
└──────────────────────────┘
```

---

## ⚠️ MİGRASYON NOTLARI

1. **Lokal Test**: SQLite kullanın, işlem yok
2. **Production Deploy**: PostgreSQL otomatik seçilir
3. **Veri Kaybı Riski**: YOKTUR (her şey kalıcı)
4. **Blob Storage**: B2 URL'leri sadece okuma-only

---

## 🐛 TROUBLESHOOTING

### Sorun: "database connection failed"
```
Çözüm: DATABASE_URL'yi kontrol et
- Lokal: instance/envanter_local.db dosyası var mı?
- Production: Render.com env var set mi?
```

### Sorun: "table does not exist"
```
Çözüm: 
python -c "from app import app; from models import db; db.create_all()"
```

### Sorun: "QR kod B2'ye upload edilmedi"
```
Çözüm: B2 kredentiyalları kontrol et
- B2_KEY_ID
- B2_APP_KEY
```

---

## 📞 DESTEK

Sorular varsa: Admin paneli → QR Yönetimi → Help bölümünü kontrol et

Version: 2.0 (SQLAlchemy + B2 Storage)
Last Updated: October 30, 2025
