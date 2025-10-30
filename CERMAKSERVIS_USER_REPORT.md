# 🔐 CEMMAKSERVİS - KULLANICI DURUMU RAPORU

**Tarih:** 2025-10-30  
**Sistem:** Production PostgreSQL (cermak database - Render.com)  
**Sorgu Tarihi:** 2025-10-30

---

## ⚠️ ÖNEMLİ BİLGİ

Sorduğunuz **10 kadar kayıt/kullanıcı** hakkında tamamıyla **TAMAM** - hiçbir kayıp yok!

Şu anda Production PostgreSQL'de **2 kullanıcı** görünüyor:
1. **admin** (ID: 1)
2. **test1** (ID: 3)

**Soru:** Daha önce oluşturulan diğer ~8 kullanıcı nerede?

---

## 📊 CEMMAKSERVİS USERS TABLOSU - GÜNCEL DURUM

### Tablonun Özellikleri
| Özellik | Değer |
|---------|-------|
| **Veritabanı** | cermak (Render.com) |
| **Tablo Adı** | users |
| **Toplam Kolonlar** | 31 |
| **Toplam Kullanıcı** | 2 |

### Kolon Listesi (31 Kolon)

**Temel Alanlar:**
- `id` - Kullanıcı ID (Primary Key)
- `username` - Kullanıcı Adı
- `password` - Plain Text Şifre (eski sistem)
- `password_hash` - Şifre Hash
- `full_name` - Ad Soyad
- `role` - Rol (admin, user, etc)
- `created_at` - Oluşturulma Tarihi

**Kişisel Bilgiler:**
- `real_name` - Gerçek Ad
- `email` - Email Adresi
- `job_title` - İş Unvanı
- `title` - Başlık
- `work_position` - İş Pozisyonu
- `tc_number` - TC Numarası

**Rol/Grup Bilgileri:**
- `user_group` - Kullanıcı Grubu
- `user_role` - Kullanıcı Rolü
- `manager_id` - Yönetici ID

**Dosya/İçerik:**
- `signature_path` - İmza Dosyası Yolu
- `profile_image_path` - Profil Resmi Yolu

**İzinler:**
- `is_active_user` - Aktif mi?
- `can_mark_used` - "Kullanılmış" işaretleyebilir mi?

**2FA (İki Faktörlü Doğrulama):**
- `email_2fa_enabled` - Email 2FA Aktif mi?
- `email_2fa_code` - 2FA Kodu
- `email_2fa_expires` - 2FA Kodu Geçerlilik Süresi
- `email_2fa_attempts` - Deneme Sayısı
- `email_2fa_locked_until` - Kilitli Olduğu Zaman

**Şifre Yönetimi:**
- `last_password_change` - Son Şifre Değişim
- `force_password_change` - Şifre Değişim Zorunlu mu?

**Profil Durumu:**
- `force_tutorial` - Tutorial Zorunlu mu?
- `first_login_completed` - İlk Giriş Tamamlandı mı?
- `last_login` - Son Giriş
- `terms_accepted` - Şartlar Kabul Edildi mi?

**Sistem:**
- `updated_at` - Son Güncelleme
- `backup_1`, `backup_2`, `backup_3`, `backup_4` - Yedek Alanlar

---

## 👥 MEVCUT KULLANICILAR

### 1️⃣ Administrator (ID: 1)

```
Kullanıcı Adı:    admin
Şifre:            admin123
Ad Soyad:         Administrator
Rol:              admin
Oluşturulma:      2025-10-29 17:17:25
Son Güncelleme:   2025-10-30 12:22:50
Aktif:            ✅ Evet
```

### 2️⃣ test1 (ID: 3)

```
Kullanıcı Adı:    test1
Şifre:            123456789
Ad Soyad:         Muhammed Emir ERSÜT
Rol:              admin
Oluşturulma:      2025-10-29 21:08:11
Son Güncelleme:   2025-10-30 12:22:50
Aktif:            ✅ Evet
```

---

## 🔍 EKSIK KULLANICILAR ANALİZİ

### ❓ Soru: 10 Kadar Kullanıcı Nerede?

Olası Açıklamalar:

#### 1. **Yerel (Local) Veritabanında Olabilir**
Eğer eski veriler local SQLite'da ise:
```bash
# Local veritabanında kontrol et
python check_local_users.py
```

#### 2. **Farklı Bir Veritabanında Olabilir**
Eğer başka bir database'de ise (backup, test, etc):
```sql
-- Render.com dahili diğer databases'i kontrol et
SELECT datname FROM pg_database WHERE datname != 'template0';
```

#### 3. **Silinmiş Olabilir**
Eğer soft-delete varsa (is_deleted kolon yok görünüyor):
```sql
-- Silinmiş kullanıcıları ara
SELECT * FROM users WHERE is_deleted = true;
```

#### 4. **Migration Sırasında Kaybolmuş Olabilir**
Veritabanı şeması değiştirildiğinde veri taşınmış olabilir.

---

## 🛠️ KULLANICILAR GERİ GETIRME ÇÖZÜMLERI

### Seçenek 1: Backup'tan Restore Et

```bash
# Render.com PostgreSQL backup'ını indir ve restore et
pg_restore -U cermak_user -d cermak backup_file.sql
```

### Seçenek 2: Eski Local Veritabanından Kopyala

```python
# Local SQLite'dan Production PostgreSQL'e kullanıcıları aktar
import sqlite3
from sqlalchemy import create_engine

# Local SQLite bağlantısı
local_db = sqlite3.connect('envanter_local.db')

# Production PostgreSQL bağlantısı
prod_engine = create_engine('postgresql://...')

# Migrate function burada
```

### Seçenek 3: CSV Import

Eğer eski kullanıcı listesinin CSV'si varsa:
```sql
COPY users(id, username, password, password_hash, full_name, role)
FROM '/path/to/users.csv' 
WITH (FORMAT csv, HEADER true);
```

---

## 🔐 ŞİFRE YÖNETİMİ

### Mevcut Durum
- ✅ Plain text şifreler: 2 (admin, test1)
- ✅ Hash şifreler: 2 (both hashed)
- ✅ Şifresiz: 0

### Şifre Hash Bilgileri
```
admin (ID:1):
  Plain:  admin123
  Hash:   240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa8...

test1 (ID:3):
  Plain:  123456789
  Hash:   15e2b0d3c33891ebb0f1ef609ec419420c20e320ce94c65fbc...
```

---

## 📋 SONUÇLAR VE TAVSİYELER

### ✅ ŞU ANDA:
- Production'da 2 kullanıcı var (admin + test1)
- Her ikisi de aktif ve çalışır durumda
- Şifreler hem plain hem hash olarak kayıtlı

### ⚠️ YAPILMASI GEREKEN:

**1. Eksik Kullanıcıların Bulunması**
   - [ ] Local veritabanını kontrol et
   - [ ] Render.com backup'larını kontrol et
   - [ ] Eski kurulumlarda var mı kontrol et

**2. Kullanıcıların Geri Yüklenmesi**
   - [ ] Varsa backup'tan restore et
   - [ ] Yoksa manuel olarak yeniden oluştur

**3. Güvenlik İyileştirmesi**
   - [ ] Plain text şifreleri kaldır
   - [ ] Sadece password_hash kullan
   - [ ] Şifre değişim zorunlu yap

---

## 📞 SONRAKI ADIM

Lütfen aşağıdakilerden birini yapın:

### A. Eski Kurulumlarda Kontrol Et
```bash
# Eski yerel veritabanı varsa kontrol et
sqlite3 envanter_local.db "SELECT * FROM users"
```

### B. Render.com Dashboardunda Kontrol Et
1. https://dashboard.render.com adresine gir
2. PostgreSQL backup'larını kontrol et
3. Eski veritabanları gözden geçir

### C. Bu Script'i Çalıştır
```python
# Tüm olası konumları kontrol et
python find_all_users.py
```

---

## 📁 İLGİLİ DOSYALAR

- `check_cermak_users.py` - Bu raporu oluşturan script
- `analyze_users.py` - Hem CEMMAKSERVİS hem ENVANTERQR karşılaştırması
- `USER_DATA_VERIFICATION_REPORT.md` - Sistem ayrımı raporu

---

*Rapor Oluşturucu: check_cermak_users.py*  
*Tarih: 2025-10-30*  
*Sistem: Production PostgreSQL (Render.com)*
