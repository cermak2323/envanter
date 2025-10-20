# Cermak Envanter Sistemi

## Proje Açıklaması
Python Flask ile geliştirilmiş güvenli, kullanıcı yönetimli QR kod tabanlı envanter sayım sistemi. Excel dosyalarından parça bilgilerini yükleyerek benzersiz QR kodları oluşturur, çoklu kullanıcılarla eş zamanlı sayım yapılmasını sağlar ve detaylı Excel raporları üretir. Kırmızı-beyaz tema ve Cermak branding'i ile özelleştirilmiştir.

## Ana Özellikler

### Kullanıcı Yönetimi
1. **Login Sistemi**: Güvenli session tabanlı kimlik doğrulama
2. **Kullanıcı Rolleri**: Admin ve kullanıcı rolleri
3. **Admin Paneli**: Kullanıcı ekleme, silme ve yönetim
4. **Varsayılan Admin**: Kullanıcı adı: `admin`, Şifre: `admin123`

### QR Kod Yönetimi
5. **QR Kod Oluşturma**: Excel dosyasından (part_code, part_name, quantity) parça bilgilerini yükleyerek her parça birimi için benzersiz QR kod oluşturur
6. **Arama Özelliği**: Parça kodu veya adı ile QR kodları filtreleme
7. **Modal Görüntüleme**: QR kodlara tıklayınca büyük ekranda görüntüleme
8. **Tekli İndirme**: Her QR kodu ayrı ayrı indirme ve işaretleme
9. **Toplu İndirme**: Tüm QR kodları ZIP dosyası olarak indirme
10. **İndirme Takibi**: İndirilen QR kodlar otomatik işaretlenir

### Sayım Özellikleri
11. **Sayım Başlatma**: Envanter Excel dosyası (part_code, quantity) yüklenerek sayım oturumu başlatılır
12. **Çoklu Kullanıcı**: WebSocket ile birden fazla kullanıcı aynı anda QR okutabilir
13. **Mobil QR Okutma**: Mobil uyumlu kamera entegrasyonu
14. **Tek Kullanımlık QR**: Her QR kod sadece bir kez kullanılabilir
15. **Sistem Kilitleme**: Aktif sayım sırasında sadece QR okutma yapılabilir
16. **Excel Rapor**: Detaylı sayım raporu (Parça Kodu, Adı, Envanter, Sayım, Fark)

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
- **users**: Kullanıcı bilgileri (username, password hash, full_name, role)
- **parts**: Yüklenen parça bilgileri
- **qr_codes**: Oluşturulan QR kodlar, kullanım ve indirme durumları
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
- 2025-10-20: 
  - İlk versiyon oluşturuldu
  - Flask backend ve SQLite veritabanı kuruldu
  - WebSocket desteği eklendi
  - Mobil uyumlu QR okuma arayüzü geliştirildi
  - Excel yükleme ve rapor çıktı sistemi oluşturuldu
  - Kullanıcı yönetimi ve authentication sistemi eklendi
  - Cermak branding ve kırmızı-beyaz tema uygulandı
  - QR kod arama, modal görüntüleme ve indirme özellikleri eklendi
  - Admin paneli eklendi
  - Tüm endpoint'ler güvenlik için korundu
  - Path traversal güvenlik açığı kapatıldı

## Çalıştırma
```bash
python app.py
```
Sunucu http://0.0.0.0:5000 adresinde çalışacaktır.
