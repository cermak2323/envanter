# 📚 QR Kodlarının B2'ye Kalıcı Olarak Kaydedilmesi

## 🎯 Durum

✅ **Kod hazır:** QR kod generation ve download işlevleri B2'ye destek etmek üzere yazılmış
✅ **Dual-Mode:** Lokal development ve production ortamları arasında otomatik geçiş
❌ **B2 Credentials:** Test credentials ile çalışmıyor (gerçek B2 hesabı gerekiyor)

## 🔧 Mevcut Kodda B2 Desteği

### 1. QR Generation Endpoint (`/generate_qr_image/<qr_id>`)
```python
# Lokasyon: app.py satır 1213
# İşlevsellik:
# - QR kod oluşturur
# - USE_B2_STORAGE=True ise → B2'ye async yükler
# - USE_B2_STORAGE=False ise → Lokal static klasöre kaydeder
```

### 2. QR Download Endpoint (`/download_single_qr/<qr_id>`)
```python
# Lokasyon: app.py satır 1299
# İşlevsellik:
# - USE_B2_STORAGE=True ise → B2'den indirir
# - USE_B2_STORAGE=False ise → Lokal depolama'dan indirir
# - Fallback: QR bulunamazsa yeniden oluşturur
```

### 3. B2 Storage Service (`b2_storage.py`)
```python
# İşlevler:
# - B2 bağlantısı ve yetkilendirme
# - Dosya yükleme (upload_file)
# - Dosya indirme (download_file)
# - Dosya silme (delete_file)
# - Dosya listeleme (list_files)
```

## 🚀 Aktivasyon Adımları

### Step 1: B2 Hesabı Oluşturun
```
1. https://www.backblaze.com/b2/cloud-storage.html
2. "Sign Up" butonuna tıklayın
3. E-mail ve şifre ile kayıt olun
4. Doğrulama e-mailini tıklayın
```

### Step 2: B2 Application Key Oluşturun
```
1. https://secure.backblaze.com/b2_api_chooser.htm adresine giriş yapın
2. "Create Application Key" tıklayın
3. Settings:
   - Key Type: "Master Application Key"
   - Valid Duration: "None (never expires)"
4. "Create New Key" tıklayın
5. Application Key ID ve Application Key'i kopyalayın
```

### Step 3: B2 Bucket Oluşturun
```
1. B2 Console'da "Buckets" seçin
2. "Create a Bucket" tıklayın
3. Bucket Name: envanter-qr-codes
4. Type: Private
5. Oluştur
```

### Step 4: .env Dosyasını Güncelleyin
```bash
# .env dosyasını açın ve şu satırları ekleyin:
B2_APPLICATION_KEY_ID=xxxxxxxxxxxxxxxxxxxxxxxx
B2_APPLICATION_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
B2_BUCKET_NAME=envanter-qr-codes

# Lokal development'da B2'yi force et (opsiyonel):
FORCE_B2_LOCAL=true
```

### Step 5: App'i B2 ile Başlatın
```bash
# Lokal testing için (B2 credentials gerekli)
FORCE_B2_LOCAL=true python app.py

# Production (Render.com)
# .env Render Dashboard'da set edin
# App otomatik olarak B2'yi kullanacak
```

## 📊 QR Kodları B2'ye Yükleme

### Mevcut QR'ları B2'ye Yüklemek İçin:
```bash
# 1. B2 credentials'ını .env'e ekleyin
# 2. Test script'ini çalıştırın:
python test_b2_upload.py

# Output:
# ✅ 5 QR kod bulundu
# ✓ QR_001.png (2.3 KB)
# ... ve 4 dosya daha
# ✅ Upload Sonuç: Başarılı: 5, Başarısız: 0
```

### Yeni QR'lar Otomatik Olarak B2'ye Kaydedilir:
- QR generation endpoint'i çağrıldığında
- USE_B2_STORAGE=True ise background thread'de async yükler
- İşlem 5-10 saniye içinde tamamlanır

## 🔍 Lokal Testing (B2 Credentials olmadan)

### Dual-Mode Çalışma:
```python
# Code zaten şunu yapıyor:
if USE_B2_STORAGE and get_b2_service:
    # B2'ye yükle (production)
    b2_service.upload_file(...)
else:
    # Lokal storage'a kaydet (development)
    with open(local_path, 'wb') as f:
        f.write(img_data)
```

### Geçerli Durumu Kontrol Edin:
```bash
python -c "
import os
os.environ['FORCE_B2_LOCAL'] = 'true'
from app import USE_B2_STORAGE
print('USE_B2_STORAGE:', USE_B2_STORAGE)
"
```

## 📈 B2 Depolama Maliyeti

| Depolama | Fiyat | Bant Genişliği |
|----------|-------|----------------|
| İlk 10 GB | Ücretsiz | İlk 1 GB/gün ücretsiz |
| 10-100 GB | $0.006/GB | $0.003/GB |
| Tipik QR (2KB) | ~$0.00001 | Çok düşük |

**Örnek:** 10,000 QR (20 MB) = ~$0.12/ay

## 🐛 Debug & Troubleshooting

### B2 Bağlantısı Kontrol:
```bash
python check_b2_setup.py
```

### QR Upload Test:
```bash
python test_b2_upload.py
```

### App Loglarında B2 Status:
```
🔽 QR download request for: QR_001
☁️ Trying B2 download for: QR_001
✅ B2 file downloaded successfully: qr_codes/QR_001.png
```

## ✅ Checklist

- [ ] B2 hesabı oluşturun
- [ ] Application Key oluşturun
- [ ] Bucket oluşturun
- [ ] .env dosyasını güncelleyin
- [ ] `check_b2_setup.py` ile test edin
- [ ] Uygulamayı restart edin
- [ ] QR generation test edin
- [ ] QR download test edin
- [ ] B2 Console'da dosyaları kontrol edin

## 📞 Support

Sorun yaşarsanız:
1. `check_b2_setup.py` çıktısını kontrol edin
2. B2 credentials'ı double-check edin
3. B2 Console'da bucket'ı kontrol edin
4. App loglarında error message'ları arayın

---

**Notlar:**
- QR kodları B2'ye upload edildiğinde lokal storage'dan silinmez (fallback için tutulur)
- B2'deki dosyalar 30 gün sonra otomatik olarak silineceğini istiyorsanız, B2 Console'da lifecycle rules yapılandırın
- Production'da DATABASE_URL set edilmişse otomatik olarak B2 kullanılır
