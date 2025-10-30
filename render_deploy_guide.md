# 📱 RENDER.COM DEPLOY REHBERİ

## 🎯 Hazırlık Kontrol Listesi
- ✅ PostgreSQL veritabanı hazır (dpg-d2m6l5ripnbc738v4b0g-a.oregon-postgres.render.com)
- ✅ Uygulama yerel olarak çalışıyor
- ✅ QR kod tarama test edildi
- ✅ Admin paneli çalışıyor

## 🚀 Deploy Adımları

### 1. GitHub Repository Hazırlama
```bash
# Repository'yi güncelleyin
git add .
git commit -m "QR kod tarama sistemi hazır - production deploy"
git push origin main
```

### 2. Render.com'da Web Service Oluşturma
1. https://render.com → Dashboard
2. "New" → "Web Service"
3. GitHub repository'nizi seçin: `cermak2323/envanter`
4. Branch: `main`

### 3. Deploy Ayarları
```
Name: envanter-qr-system
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: python app.py
```

### 4. Environment Variables Ekleme
```
DATABASE_URL = postgresql://cermak_user:XPNP4Yt8dsWdKaaxNlQOzIiRJjWoTrfC@dpg-d2m6l5ripnbc738v4b0g-a.oregon-postgres.render.com:5432/cermak?sslmode=require

RENDER = true

ADMIN_PASSWORD = admin123

ADMIN_COUNT_PASSWORD = admin123
```

### 5. Deploy Başlatma
- "Create Web Service" butonuna tıklayın
- Deploy işlemi 5-10 dakika sürer
- URL örneği: https://envanter-qr-system.onrender.com

## 📱 Mobil Test
Deploy sonrası bu URL'ler çalışacak:
- **Ana sayfa:** https://envanter-qr-system.onrender.com
- **Admin panel:** https://envanter-qr-system.onrender.com/admin
- **QR tarama:** https://envanter-qr-system.onrender.com/count

## 🔧 Deploy Sorunları
1. **Build hatası:** requirements.txt kontrol edin
2. **Database bağlantı hatası:** Environment variables kontrol edin
3. **Port hatası:** app.py'de production port ayarı kontrol edin

## 📞 Deploy Sonrası
- Mobile browser'da test edin
- Camera permission verin
- QR kod tarama test edin
- Admin panel test edin