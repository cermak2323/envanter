# 🔧 Environment Variables Checker for Render.com

Bu dosya Render Dashboard'da **Environment** sekmesinde şu değerlerin set edilmiş olduğunu kontrol edin:

## 🚨 ZORUNLU Değişkenler (Render Dashboard'da SECRET olarak set edin):

```
DATABASE_URL
Değer: postgresql://[username]:[password]@[host]/[database]?sslmode=require

SESSION_SECRET  
Değer: [64-karakter-random-string]

B2_APPLICATION_KEY_ID
Değer: [your-backblaze-key-id]

B2_APPLICATION_KEY
Değer: [your-backblaze-key]

ADMIN_COUNT_PASSWORD
Değer: [your-admin-password]
```

## ✅ OTOMATIK Değişkenlar (render.yaml'dan gelir):

```
B2_BUCKET_NAME = envanter-qr-bucket
PYTHON_VERSION = 3.11.6 (build scope)
```

## 🔍 Kontrol Listesi:

- [ ] DATABASE_URL → **Scope: Secret** olarak set edilmiş
- [ ] SESSION_SECRET → **Scope: Secret** olarak set edilmiş  
- [ ] B2_APPLICATION_KEY_ID → **Scope: Secret** olarak set edilmiş
- [ ] B2_APPLICATION_KEY → **Scope: Secret** olarak set edilmiş
- [ ] ADMIN_COUNT_PASSWORD → **Scope: Secret** olarak set edilmiş

## 🚀 Deploy Sonrası Test:

1. `https://[your-app].onrender.com/health` → Status: OK
2. Ana sayfa yüklenmeli
3. Socket.IO bağlantısı kurulmalı
4. Dashboard sayıları görünmeli

## ⚠️ Eğer 502 Hatası Alıyorsanız:

1. **Render Dashboard → Logs** sekmesini kontrol edin
2. Environment variables'ların hepsinin set edildiğini doğrulayın
3. Database URL'nin doğru olduğunu test edin
4. Bu dosyadaki kontrol listesini gözden geçirin