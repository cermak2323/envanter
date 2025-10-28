"""
Otomatik Veritabanı Backup Sistemi
Bu script düzenli aralıklarla PostgreSQL veritabanının yedeğini alır.
"""

import os
import subprocess
import datetime
import logging
from dotenv import load_dotenv
import schedule
import time

load_dotenv()

# Backup ayarları
BACKUP_DIR = "backups"
DATABASE_URL = os.getenv('DATABASE_URL')
MAX_BACKUPS = 7  # Son 7 backup'ı sakla

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backup.log'),
        logging.StreamHandler()
    ]
)

def create_backup():
    """PostgreSQL veritabanı backup'ı oluştur"""
    try:
        # Backup klasörü oluştur
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        # Backup dosya adı (tarih-saat)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"envanter_backup_{timestamp}.sql"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        
        # pg_dump komutu (Windows için)
        cmd = f'pg_dump "{DATABASE_URL}" > "{backup_path}"'
        
        logging.info(f"Backup başlatılıyor: {backup_filename}")
        
        # Backup oluştur
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info(f"✅ Backup başarıyla oluşturuldu: {backup_path}")
            
            # Eski backup'ları temizle
            cleanup_old_backups()
            
            return True
        else:
            logging.error(f"❌ Backup hatası: {result.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Backup işleminde hata: {e}")
        return False

def cleanup_old_backups():
    """Eski backup dosyalarını temizle"""
    try:
        if not os.path.exists(BACKUP_DIR):
            return
        
        # Backup dosyalarını listele ve tarihe göre sırala
        backup_files = []
        for filename in os.listdir(BACKUP_DIR):
            if filename.startswith("envanter_backup_") and filename.endswith(".sql"):
                filepath = os.path.join(BACKUP_DIR, filename)
                backup_files.append((filepath, os.path.getmtime(filepath)))
        
        # Tarihe göre sırala (eski önce)
        backup_files.sort(key=lambda x: x[1])
        
        # Fazla backup'ları sil
        while len(backup_files) > MAX_BACKUPS:
            old_backup = backup_files.pop(0)
            os.remove(old_backup[0])
            logging.info(f"🗑️ Eski backup silindi: {os.path.basename(old_backup[0])}")
            
    except Exception as e:
        logging.error(f"❌ Backup temizleme hatası: {e}")

def create_b2_backup():
    """Backblaze B2'ye backup yükle"""
    try:
        from b2_storage import get_b2_service
        
        # En son backup dosyasını bul
        backup_files = []
        for filename in os.listdir(BACKUP_DIR):
            if filename.startswith("envanter_backup_") and filename.endswith(".sql"):
                filepath = os.path.join(BACKUP_DIR, filename)
                backup_files.append((filepath, os.path.getmtime(filepath)))
        
        if not backup_files:
            logging.warning("Yüklenecek backup dosyası bulunamadı")
            return False
        
        # En son backup'ı al
        latest_backup = max(backup_files, key=lambda x: x[1])[0]
        
        # B2'ye yükle
        b2_service = get_b2_service()
        
        with open(latest_backup, 'rb') as f:
            backup_data = f.read()
        
        b2_path = f"backups/{os.path.basename(latest_backup)}"
        result = b2_service.upload_file(b2_path, backup_data, 'application/sql')
        
        if result['success']:
            logging.info(f"✅ Backup B2'ye yüklendi: {b2_path}")
            return True
        else:
            logging.error(f"❌ B2 backup hatası: {result.get('error')}")
            return False
            
    except Exception as e:
        logging.error(f"❌ B2 backup yükleme hatası: {e}")
        return False

def full_backup():
    """Tam backup işlemi (lokal + B2)"""
    logging.info("🔄 Otomatik backup başlatılıyor...")
    
    # Lokal backup
    if create_backup():
        # B2 backup
        create_b2_backup()
    
    logging.info("✅ Backup işlemi tamamlandı")

if __name__ == "__main__":
    print("📅 Otomatik Backup Sistemi Başlatılıyor...")
    print("⏰ Günlük backup saati: 03:00")
    print("💾 Backup klasörü:", os.path.abspath(BACKUP_DIR))
    print("📊 Maksimum backup sayısı:", MAX_BACKUPS)
    print()
    
    # İlk backup'ı hemen al
    print("🚀 İlk backup oluşturuluyor...")
    full_backup()
    
    # Günlük 03:00'da backup al
    schedule.every().day.at("03:00").do(full_backup)
    
    print("✅ Backup sistemi aktif. CTRL+C ile durdurun.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Her dakika kontrol et
    except KeyboardInterrupt:
        print("\n⏹️ Backup sistemi durduruldu.")