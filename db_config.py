"""
Veritabanı Konfigürasyonu - Lokal SQLite vs Production PostgreSQL
TAMAMEN BAĞIMSIZ - Aralarında sinkronizasyon YOK
"""

import os
from pathlib import Path

# Ortamı belirle
ENVIRONMENT = os.environ.get('FLASK_ENV', 'development')  # development, production
IS_PRODUCTION = ENVIRONMENT == 'production' or bool(os.environ.get('RENDER'))
IS_LOCAL = not IS_PRODUCTION

# Proje kök dizini
BASE_DIR = Path(__file__).parent

print(f"🔧 Environment: {ENVIRONMENT}")
print(f"📍 Production (Render.com): {IS_PRODUCTION}")
print(f"🏠 Lokal (Development): {IS_LOCAL}")
print()


def get_database_uri():
    """
    Veritabanı URI'sini ortama göre döndür
    UYARI: Lokal ve Production tamamen bağımsız!
    """
    
    if IS_PRODUCTION:
        # PRODUCTION: Render.com PostgreSQL
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set for production!")
        
        # PostgreSQL sslmode fix
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        print(f"☁️ Production PostgreSQL: {database_url[:50]}...")
        print(f"⚠️  Render.com'un kendi PostgreSQL veritabanı kullanılıyor")
        return database_url
    else:
        # DEVELOPMENT: Lokal SQLite (BAĞIMSIZ)
        db_path = BASE_DIR / 'instance' / 'envanter_local.db'
        db_path.parent.mkdir(exist_ok=True)
        
        sqlite_uri = f'sqlite:///{db_path}'
        print(f"🏠 Lokal SQLite: {db_path}")
        print(f"⚠️  Tamamen bağımsız veritabanı - Render.com etkilenmez")
        return sqlite_uri


class Config:
    """Temel Konfigürasyon"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
    }


class DevelopmentConfig(Config):
    """
    Geliştirme Ortamı - SQLite (BAĞIMSIZ)
    
    ✅ Lokal makina üzerinde çalışır
    ✅ Render.com'dan tamamen izole
    ✅ Test ve geliştirme için ideal
    ✅ Sayım başlatma - sadece lokal verileri etkiler
    """
    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_ECHO = True  # SQL sorguları konsola yazılır
    
    # Session
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 saat


class ProductionConfig(Config):
    """
    Üretim Ortamı - PostgreSQL (BAĞIMSIZ)
    
    ✅ Render.com PostgreSQL
    ✅ Lokal'dan tamamen izole
    ✅ Üretim verisi korumalı
    ✅ Sayım başlatma - sadece üretim verileri etkiler
    """
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_ECHO = False
    
    # Session
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 86400
    
    # Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    """Test Ortamı"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Aktif konfigürasyonu seç
if IS_PRODUCTION:
    config = ProductionConfig()
    config_name = 'production'
    db_type = 'PostgreSQL (Render.com)'
else:
    config = DevelopmentConfig()
    config_name = 'development'
    db_type = 'SQLite (Lokal)'

print(f"📋 Active Config: {config_name}")
print(f"💾 Database Type: {db_type}")
print(f"🔐 Veritabanlar TAMAMEN BAĞIMSIZ - Hiçbir sinkronizasyon YOK")
print(f"="*60)
