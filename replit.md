# Envanter Sayım Sistemi

## Proje Açıklaması
Python Flask ile geliştirilmiş QR kod tabanlı envanter sayım sistemi. Excel dosyalarından parça bilgilerini yükleyerek benzersiz QR kodları oluşturur, çoklu kullanıcılarla eş zamanlı sayım yapılmasını sağlar ve detaylı Excel raporları üretir.

## Ana Özellikler
1. **QR Kod Oluşturma**: Excel dosyasından (part_code, part_name, quantity) parça bilgilerini yükleyerek her parça birimi için benzersiz QR kod oluşturur
2. **QR Kod Yönetimi**: Oluşturulan QR kodları ekranda görüntülenir ve ZIP dosyası olarak toplu indirilebilir
3. **Sayım Başlatma**: Envanter Excel dosyası (part_code, quantity) yüklenerek sayım oturumu başlatılır
4. **Çoklu Kullanıcı Desteği**: WebSocket (SocketIO) kullanarak birden fazla kullanıcı aynı anda QR kod okutabilir
5. **QR Okutma**: Mobil uyumlu kamera entegrasyonu ile QR kodlar okunur ve işaretlenir
6. **Tek Kullanımlık QR**: Her QR kod sadece bir kez kullanılabilir
7. **Sistem Kilitleme**: Aktif sayım sırasında sadece QR okutma yapılabilir
8. **Excel Rapor**: Sayım bittiğinde parça kodu, adı, sayım adeti, envanter adeti ve fark içeren rapor oluşturulur

## Teknoloji Stack
- **Backend**: Python 3.11, Flask, Flask-SocketIO
- **Veritabanı**: SQLite
- **Excel İşleme**: pandas, openpyxl
- **QR Kod**: qrcode, Pillow
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **QR Okuma**: html5-qrcode
- **Gerçek Zamanlı İletişim**: Socket.IO

## Proje Yapısı
```
/
├── app.py                 # Ana Flask uygulaması
├── templates/
│   └── index.html        # Ana arayüz
├── static/               # Statik dosyalar (opsiyonel)
├── inventory.db          # SQLite veritabanı (otomatik oluşturulur)
└── sayim_raporu_*.xlsx   # Oluşturulan raporlar
```

## Veritabanı Şeması
- **parts**: Yüklenen parça bilgileri
- **qr_codes**: Oluşturulan QR kodlar ve kullanım durumları
- **count_sessions**: Sayım oturumları
- **inventory_data**: Sayım için beklenen envanter verileri
- **scanned_qr**: Okutulan QR kodların kaydı

## Kullanım Akışı
1. Parça listesi Excel dosyasını yükle (part_code, part_name, quantity sütunları)
2. Sistem her parça birimi için benzersiz QR kod oluşturur
3. QR kodları görüntüle ve ZIP olarak indir
4. QR kodları fiziksel parçalara yapıştır
5. Sayım başlat - envanter Excel dosyasını yükle (part_code, quantity sütunları)
6. Sistem kilitleme moduna geçer
7. Çoklu kullanıcılar mobil cihazlarla QR kodları okutmaya başlar
8. Sayımı bitir butonuna bas
9. Excel raporu otomatik indirilir

## Son Değişiklikler
- 2025-10-20: İlk versiyon oluşturuldu
- Flask backend ve SQLite veritabanı kuruldu
- WebSocket desteği eklendi
- Mobil uyumlu QR okuma arayüzü geliştirildi
- Excel yükleme ve rapor çıktı sistemi oluşturuldu

## Çalıştırma
```bash
python app.py
```
Sunucu http://0.0.0.0:5000 adresinde çalışacaktır.
