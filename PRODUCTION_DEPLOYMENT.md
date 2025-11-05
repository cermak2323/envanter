# 🚀 EnvanterQR Production Deployment Rehberi

## Gerekli Hazırlıklar

### 1. Sistem Gereksinimleri
- Python 3.8+ 
- PostgreSQL (Neon.tech) 
- Backblaze B2 Account
- SSL Sertifikası (Let's Encrypt önerilen)

### 2. Environment Variables
Production için `.env` dosyasını güncelle:

```env
# Production PostgreSQL (Neon)
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require

# Güçlü Session Secret (değiştir!)
SESSION_SECRET=your-super-strong-secret-key-here

# Admin Şifresi (değiştir!)
ADMIN_COUNT_PASSWORD=your-super-strong-admin-password

# Backblaze B2
B2_KEY_ID=your-key-id
B2_APPLICATION_KEY=your-app-key
B2_KEY_NAME=your-key-name
B2_BUCKET_NAME=your-bucket-name
```

### 3. Güvenlik Ayarları

#### A. Firewall Kuralları
```bash
# Sadece HTTP/HTTPS portlarını aç
ufw allow 80
ufw allow 443
ufw allow 22  # SSH için
ufw enable
```

#### B. SSL/TLS Sertifikası (Nginx ile)
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Production Deployment

#### A. Gunicorn ile Çalıştırma
```bash
# Gerekli paketleri yükle
pip install gunicorn eventlet

# Gunicorn ile başlat
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5001 app:app
```

#### B. Systemd Service (Otomatik Başlatma)
`/etc/systemd/system/envanter-qr.service`:

```ini
[Unit]
Description=EnvanterQR Inventory System
After=network.target

[Service]
Type=simple
User=envanter
WorkingDirectory=/home/envanter/EnvanterQR
Environment=PATH=/home/envanter/EnvanterQR/venv/bin
ExecStart=/home/envanter/EnvanterQR/venv/bin/gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5001 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Servisi aktive et:
```bash
sudo systemctl daemon-reload
sudo systemctl enable envanter-qr
sudo systemctl start envanter-qr
```

### 5. Monitoring ve Bakım

#### A. Log Monitoring
```bash
# Uygulama logları
tail -f /path/to/EnvanterQR/logs/app.log

# Security logları
tail -f /path/to/EnvanterQR/logs/security.log

# Backup logları  
tail -f /path/to/EnvanterQR/logs/backup.log
```

#### B. Otomatik Backup Sistemi
```bash
# Backup sistemini systemd service olarak çalıştır
# /etc/systemd/system/envanter-backup.service

[Unit]
Description=EnvanterQR Backup System
After=network.target

[Service]
Type=simple
User=envanter
WorkingDirectory=/home/envanter/EnvanterQR
Environment=PATH=/home/envanter/EnvanterQR/venv/bin
ExecStart=/home/envanter/EnvanterQR/venv/bin/python backup_system.py
Restart=always

[Install]
WantedBy=multi-user.target
```

#### C. Health Check Monitoring
Sistem sağlığını kontrol eden script:

```bash
#!/bin/bash
# health_monitor.sh

HEALTH_URL="https://yourdomain.com/health"
WEBHOOK_URL="your-slack-or-discord-webhook"

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE != "200" ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 EnvanterQR System DOWN! HTTP Status: '$RESPONSE'"}' \
        $WEBHOOK_URL
fi
```

Cron ile çalıştır:
```bash
# Her 5 dakikada kontrol et
*/5 * * * * /path/to/health_monitor.sh
```

### 6. Performance Optimizasyonu

#### A. Database Connection Pool
```python
# app.py içinde zaten optimize edildi
minconn=2, maxconn=15
```

#### B. Redis Cache (Opsiyonel)
```bash
# Redis yükle
sudo apt install redis-server

# Python paketi
pip install redis flask-caching
```

#### C. Static File Serving
```nginx
# Nginx ile static dosyaları serve et
location /static/ {
    alias /path/to/EnvanterQR/static/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 7. Security Checklist

✅ **SSL/TLS aktif**  
✅ **Güçlü session secret**  
✅ **Admin şifresi değiştirildi**  
✅ **Rate limiting aktif**  
✅ **Security headers**  
✅ **Firewall kuralları**  
✅ **Güncel paketler**  
✅ **Log monitoring**  
✅ **Backup sistemi**  

### 8. Maintenance

#### A. Güncellemeler
```bash
# Git ile güncelle
git pull origin main

# Paketleri güncelle  
pip install -r requirements.txt --upgrade

# Servisi yeniden başlat
sudo systemctl restart envanter-qr
```

#### B. Database Maintenance
```sql
-- İstatistik güncelle
ANALYZE;

-- Vakum işlemi
VACUUM;

-- Eski logları temizle (3 aydan eski)
DELETE FROM system_logs WHERE created_at < NOW() - INTERVAL '3 months';
```

### 9. Troubleshooting

#### A. Yaygın Sorunlar
- **B2 Connection Error**: API keylerini kontrol et
- **Database Connection**: CONNECTION_STRING doğrula
- **High Memory Usage**: Connection pool ayarlarını kontrol et
- **Slow Response**: Database indexlerini kontrol et

#### B. Debug Komutları
```bash
# Sistem durumu
systemctl status envanter-qr

# Logları incele
journalctl -u envanter-qr -f

# Health check
curl https://yourdomain.com/health | jq

# Metrics  
curl https://yourdomain.com/metrics | jq
```

### 10. Support ve İletişim

Sistem hakkında sorularınız için:
- 📧 Email: support@yourcompany.com
- 📱 Phone: +90 XXX XXX XX XX
- 🌐 Documentation: https://docs.yourcompany.com

---

**Son Güncelleme**: {{ datetime.now().strftime("%d/%m/%Y") }}  
**Version**: 2.0.0  
**Status**: Production Ready ✅