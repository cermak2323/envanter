# EnvanterQR - Render.com Deployment Guide

## 🚀 Render.com'a Deploy Etme Kılavuzu (Mevcut PostgreSQL + B2 ile)

Bu kılavuz EnvanterQR sisteminin Render.com'a deploy edilmesi için gerekli adımları açıklar.
**Not**: Mevcut PostgreSQL ve Backblaze B2 altyapınızı kullanacağız.

### 📋 Ön Gereksinimler

1. **GitHub Repository**: Kodunuz GitHub'da olmalı
2. **Render.com Account**: Ücretsiz hesap yeterli
3. ✅ **PostgreSQL Database**: Zaten mevcut (Neon/PostgreSQL)
4. ✅ **Backblaze B2**: Zaten konfigüre edilmiş

### 🔧 1. Render.com'da Yeni Web Service Oluşturma

1. [Render.com](https://render.com) hesabınıza giriş yapın
2. **"New +"** → **"Web Service"** seçin
3. GitHub repository'nizi bağlayın
4. Aşağıdaki ayarları yapın:

```
Name: envanterqr-app
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: python startup.py
```

**Alternative Start Commands** (eğer yukarıdaki çalışmazsa):
```
Option 1: python -m gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
Option 2: gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
Option 3: python app.py
```

### 🗄️ 2. Mevcut Database Connection

**Render.com'da yeni PostgreSQL oluşturmayın!** Mevcut database'inizi kullanın:

1. Mevcut PostgreSQL connection string'inizi hazırlayın
2. Format: `postgresql://username:password@hostname:port/database`
3. Bu string'i environment variables'da kullanacağız

### 🔐 3. Environment Variables Kurulumu

Web Service ayarlarında **Environment** sekmesine gidin ve aşağıdaki değişkenleri ekleyin:

#### Gerekli Değişkenler:
```
DATABASE_URL = postgresql://username:password@hostname:port/database?sslmode=require&channel_binding=require
SESSION_SECRET = your-session-secret-key-here
```

#### Mevcut Backblaze B2 Ayarları:
```
B2_APPLICATION_KEY_ID = 00313590dd2fde60000000004
B2_APPLICATION_KEY = K003NeFyCuFJzM/1Qo1xYXu+f/M87WU
B2_BUCKET_NAME = envanter-qr-bucket
```

#### Diğer Ayarlar:
```
PYTHON_VERSION = 3.11.6
ADMIN_COUNT_PASSWORD = @R9t$L7e!xP2w#Mn8Zq^Y4v&Bc6*Hd3J
```

### 📊 4. Database Schema Kontrolü

Mevcut database'inizde tablolar zaten var ise bu adımı atlayın.
Eğer yeni tablolar gerekli ise:

1. Mevcut PostgreSQL'e bağlanın
2. `database_schema.sql` dosyasındaki yeni tabloları kontrol edin
3. Sadece eksik tabloları oluşturun

```bash
# Sadece gerekli ise çalıştırın
psql "your_existing_database_connection_string" -f database_schema.sql
```

### 🚀 5. Deploy İşlemi

1. **"Deploy Latest Commit"** butonuna tıklayın
2. Deploy loglarını takip edin
3. Başarılı deploy sonrası URL'niz aktif olacak

### ✅ 6. Deploy Sonrası Kontroller

#### Health Check:
```
https://your-app-url.onrender.com/health
```

#### Admin Giriş:
```
URL: https://your-app-url.onrender.com
Username: admin
Password: admin123
```

#### Metrics:
```
https://your-app-url.onrender.com/metrics
```

### 🔧 Sorun Giderme

#### Deploy Hataları:
1. Render logs'ları kontrol edin
2. Environment variables'ların doğru set edildiğini kontrol edin
3. Database connection string'in doğru olduğunu kontrol edin

#### Database Bağlantı Sorunları:
1. Mevcut PostgreSQL service'in aktif olduğunu kontrol edin
2. Connection string'in güncel olduğunu kontrol edin
3. Database'de gerekli tablolar var mı kontrol edin
4. Network access/firewall ayarları kontrol edin

#### B2 Storage Sorunları:
1. Mevcut B2 credentials'ların doğru olduğunu kontrol edin
2. Bucket permissions'ları kontrol edin
3. Logs'ta B2 connection hatalarını kontrol edin
4. B2 API key'lerin aktif olduğunu kontrol edin

### 📈 Performans Optimizasyonları

#### Render.com Specific:
- **Plan Upgrade**: Starter plan yerine paid plan kullanın
- **Persistent Disk**: Büyük dosyalar için persistent disk ekleyin
- **CDN**: Static files için CDN aktifleştirin

#### Application Level:
- Cache sistemi aktif (Redis için upgrade gerekli)
- Database indexler optimize edildi
- Static file compression aktif

### 🔒 Güvenlik

#### Production Ayarları:
- `DEBUG=false` set edildi
- Security headers aktif
- Rate limiting aktif
- HTTPS zorunlu (Render otomatik)

#### Recommended:
- Strong session secret kullanın
- Database credentials'ları güvenli tutun
- Regular backup alın

### 📞 Destek

Deploy sorunları için:
1. Render.com documentation'ını kontrol edin
2. Render community forum'unu kullanın
3. GitHub issues'da sorun bildirin

### 🔄 Updates

Code update için:
1. GitHub'a push yapın
2. Render otomatik olarak deploy eder
3. Manual deploy için "Deploy Latest Commit" kullanın

---

## 🎉 Başarılı Deploy Sonrası

EnvanterQR sisteminiz artık cloud'da çalışıyor!

**Live URL**: https://your-app-name.onrender.com
**Admin Panel**: /admin
**Health Check**: /health

Sisteminizi kullanmaya başlayabilirsiniz! 🚀