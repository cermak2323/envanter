"""
Veritabanı Konfigürasyonu - Lokal SQLite vs Production PostgreSQL
"""

import os
from pathlib import Path

# Ortamı belirle
ENVIRONMENT = os.environ.get('FLASK_ENV', 'development')  # development, production
IS_PRODUCTION = ENVIRONMENT == 'production' or bool(os.environ.get('RENDER'))

# Proje kök dizini
BASE_DIR = Path(__file__).parent

print(f"🔧 Environment: {ENVIRONMENT}")
print(f"📍 Production: {IS_PRODUCTION}")


def get_database_uri():
    """Veritabanı URI'sini ortama göre döndür"""
    
    if IS_PRODUCTION:
        # PRODUCTION: Render.com PostgreSQL
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set for production!")
        
        # PostgreSQL sslmode fix
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        print(f"✅ Production PostgreSQL: {database_url[:50]}...")
        return database_url
    else:
        # DEVELOPMENT: Lokal SQLite
        db_path = BASE_DIR / 'instance' / 'envanter_local.db'
        db_path.parent.mkdir(exist_ok=True)
        
        sqlite_uri = f'sqlite:///{db_path}'
        print(f"✅ Development SQLite: {db_path}")
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
    """Geliştirme Ortamı - SQLite"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_ECHO = True  # SQL sorguları konsola yazılır
    
    # Session
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 saat


class ProductionConfig(Config):
    """Üretim Ortamı - PostgreSQL"""
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
else:
    config = DevelopmentConfig()
    config_name = 'development'

print(f"📋 Active Config: {config_name}")
