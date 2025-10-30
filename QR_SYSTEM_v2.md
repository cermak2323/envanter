# 🎉 YENİ SISTEM - QR KOD YÖNETIMI & SQLAlchemy

## ✨ HARITA

### 1. **Bağımsız Veritabanı Sistemi**
- 🏠 **Lokal**: SQLite (instance/envanter_local.db)
- ☁️ **Production**: PostgreSQL (Render.com)
- **Hiç bir sinkronizasyon YOK**

### 2. **QR Yönetim**
- **Lokal**: static/qrcodes/ (geçici PNG)
- **Production**: B2 Storage (kalıcı URL)

### 3. **Sayım Başlatma**
- **Lokal**: Sadece SQLite etkilenir
- **Production**: Sadece PostgreSQL etkilenir

---

## 🏠 LOKAL DEVELOPMENT

```
Veritabanı: SQLite
Path: instance/envanter_local.db
QR Depolama: static/qrcodes/
Başlatma: python app.py
Port: 5002
URL: http://localhost:5002
```

### Özellikler:
- ✅ Hızlı test ortamı
- ✅ Render.com etkilenmez
- ✅ Tüm özellikleri destekler
- ✅ QR kodları geçici (silme emniyeti)

---

## ☁️ PRODUCTION (Render.com)

```
Veritabanı: PostgreSQL
URL: DATABASE_URL env var
QR Depolama: B2 Storage (/qr-permanent/)
Başlatma: Otomatik
URL: https://cermakservis.onrender.com
```

### Özellikler:
- ✅ Kalıcı veri storage
- ✅ B2 backup
- ✅ Lokal SQLite etkilenmez
- ✅ QR URL'leri kalıcı

---

## 🔒 İZOLASYON TABLOSU

| İşlem | Lokal Sonuç | Render Sonuç | Etkileşim |
|-------|-----------|-------------|-----------|
| Sayım Başlat | ✓ SQLite | ✓ PostgreSQL | ✗ Yok |
| QR Tara | ✓ SQLite | ✓ PostgreSQL | ✗ Yok |
| Sayım Durdur | ✓ SQLite | ✓ PostgreSQL | ✗ Yok |
| CSV Import | ✓ SQLite | ✓ PostgreSQL | ✗ Yok |
| Admin Giriş | ✓ Lokal | ✓ Render | ✗ Yok |

---

## 🚀 BAŞLANGÇ

### Lokal Test:
```bash
set FLASK_ENV=development
python app.py
# Result: SQLite kullanır, Render etkilenmez
```

### Production (Render.com):
```bash
# Otomatik RENDER=1 set olur
# DATABASE_URL otomatik set olur
# PostgreSQL otomatik seçilir
```

---

## 📊 API ENDPOİNTLERİ

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| POST | `/admin/qr/generate` | Yeni QR oluştur |
| GET | `/admin/qr/list` | QR'ları listele |
| POST | `/admin/qr/import-csv` | CSV import |
| GET | `/admin/qr/export-pdf` | PDF export |
| GET | `/admin/qr/stats` | İstatistikler |

---

## ✅ KONTROL LİSTESİ

- ✓ SQLAlchemy ORM kurulu
- ✓ Lokal SQLite konfigürasyonu
- ✓ Production PostgreSQL konfigürasyonu
- ✓ Tamamen bağımsız sistemler
- ✓ QR yönetim paneli
- ✓ CSV import (koruyucu)
- ✓ PDF export
- ✓ Admin UI

---

## 📚 DOSYALAR

- `models.py` - SQLAlchemy modelleri
- `db_config.py` - Veritabanı konfigürasyonu
- `qr_admin.py` - QR yönetimi blueprint
- `ISOLATION_SYSTEM.md` - Detaylı izolasyon dokümantasyonu
- `templates/admin_qr_manage.html` - Admin panel UI
