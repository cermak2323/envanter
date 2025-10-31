# 📋 RENDER ENVIRONMENT VARIABLES - COPY/PASTE GUIDE

## 🎯 Hedef: Render Dashboard → Environment Variables

### 📍 Adımlar:
1. https://dashboard.render.com → Your Service
2. **Environment** tab'ine tıkla
3. **Add Environment Variable** butonu
4. Aşağıdaki 6 variable'ı tek tek ekle

---

## 🔐 VARIABLE #1: DATABASE_URL
```
Key: DATABASE_URL
Value: postgresql://cermak_envanter_user:N22HyFcRf3bvgMzkK1J5yNYgrXEfIgNC@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter?sslmode=require
Scope: ⚠️ SECRET
```

## 🔑 VARIABLE #2: B2_APPLICATION_KEY_ID
```
Key: B2_APPLICATION_KEY_ID
Value: 00313590dd2fde60000000004
Scope: Environment Variable
```

## 🔐 VARIABLE #3: B2_APPLICATION_KEY
```
Key: B2_APPLICATION_KEY
Value: K003NeFyCuFJzM/1Qo1xYXu+f/M87WU
Scope: ⚠️ SECRET
```

## 📦 VARIABLE #4: B2_BUCKET_NAME
```
Key: B2_BUCKET_NAME
Value: envanter-qr-bucket
Scope: Environment Variable
```

## 🔐 VARIABLE #5: ADMIN_COUNT_PASSWORD
```
Key: ADMIN_COUNT_PASSWORD
Value: @R9t$L7e!xP2w#Mn8Zq^Y4v&Bc6*Hd3J
Scope: ⚠️ SECRET
```

## 🔐 VARIABLE #6: SESSION_SECRET
```
Key: SESSION_SECRET
Value: bd1a6b5747198b642e34974c4c8a277040ae6095a97a24e8076d2e1c68573fd2
Scope: ⚠️ SECRET
```

---

## ✅ Kontrol Listesi

Her variable ekledikten sonra:
- [ ] Key doğru yazıldı
- [ ] Value tamamen kopyalandı (eksik karakter yok)
- [ ] Scope doğru seçildi (Secret vs Environment Variable)

## 🚀 Final Step

Tüm 6 variable eklendikten sonra:
1. **Manual Deploy** butonuna tıkla
2. Build logs'u takip et
3. "Application running" mesajını bekle
4. Health check: `https://your-app.onrender.com/health`

## 🎯 Beklenen Sonuç

Health check response:
```json
{
  "status": "healthy",
  "environment": {
    "mode": "production",
    "database_type": "PostgreSQL",
    "storage_type": "B2 Cloud",
    "database_url_set": true
  }
}
```

---
**📝 Not: SECRET scope'lu variable'lar Render'da maskeli görünür (normal durum)**