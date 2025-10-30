"""
SQLAlchemy ORM Modelleri - EnvanterQR Sistemi
Lokal ve Production ortamları destekler
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

db = SQLAlchemy()


class PartCode(db.Model):
    """Parça Kodları - Sabit, değişmez"""
    __tablename__ = 'part_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    part_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    part_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    qr_codes = db.relationship('QRCode', backref='part', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PartCode {self.part_code}>'


class QRCode(db.Model):
    """QR Kodlar - Blob Storage'da kalıcı, asla değişmez"""
    __tablename__ = 'qr_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    part_code_id = db.Column(db.Integer, db.ForeignKey('part_codes.id'), nullable=False)
    
    # Blob Storage bilgileri
    blob_url = db.Column(db.String(500))  # Permanent B2 URL
    blob_file_id = db.Column(db.String(100))  # B2 file ID
    
    # Kullanım izleyici
    is_used = db.Column(db.Boolean, default=False)
    used_count = db.Column(db.Integer, default=0)
    first_used_at = db.Column(db.DateTime)
    last_used_at = db.Column(db.DateTime)
    
    # Durumu
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Index
    __table_args__ = (
        db.Index('idx_qr_part', 'qr_id', 'part_code_id'),
    )
    
    def __repr__(self):
        return f'<QRCode {self.qr_id}>'


class CountSession(db.Model):
    """Sayım Oturumları"""
    __tablename__ = 'count_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='active')  # active, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)
    
    # İlişkiler
    scanned_items = db.relationship('ScannedQR', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CountSession {self.session_id}>'


class ScannedQR(db.Model):
    """Taranmış QR Kodlar - İşlem Kayıtları"""
    __tablename__ = 'scanned_qr'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), db.ForeignKey('count_sessions.session_id'), nullable=False)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_codes.id'), nullable=False)
    scanned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    qr_code = db.relationship('QRCode', backref='scans')
    user = db.relationship('User', backref='scans')
    
    def __repr__(self):
        return f'<ScannedQR {self.qr_code_id} at {self.scanned_at}>'


class User(db.Model):
    """
    Kullanıcılar - cermakservis PostgreSQL şemasıyla uyumlu
    Birinci uygulama ile aynı tablo, tüm alanlar support ediliyor
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Temel
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120))
    real_name = db.Column(db.String(120))
    email = db.Column(db.String(255))
    password_hash = db.Column(db.String(255))
    
    # Rol ve Yetki
    role = db.Column(db.String(20), default='user')  # admin, user
    job_title = db.Column(db.String(120))
    title = db.Column(db.String(120))
    work_position = db.Column(db.String(120))
    user_group = db.Column(db.String(120))
    user_role = db.Column(db.String(120))
    
    # Dosyalar
    signature_path = db.Column(db.String(500))
    profile_image_path = db.Column(db.String(500))
    
    # Status
    is_active_user = db.Column(db.Boolean, default=True)
    can_mark_used = db.Column(db.Boolean, default=False)
    
    # 2FA
    email_2fa_enabled = db.Column(db.Boolean, default=False)
    email_2fa_code = db.Column(db.String(6))
    email_2fa_expires = db.Column(db.DateTime)
    email_2fa_attempts = db.Column(db.Integer, default=0)
    email_2fa_locked_until = db.Column(db.DateTime)
    
    # Güvenlik
    tc_number = db.Column(db.String(20))
    last_password_change = db.Column(db.DateTime)
    force_password_change = db.Column(db.Boolean, default=False)
    force_tutorial = db.Column(db.Boolean, default=False)
    
    # Login
    first_login_completed = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    
    # Onaylar
    terms_accepted = db.Column(db.Boolean, default=False)
    
    # Zaman
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'


class CountPassword(db.Model):
    """Sayım Şifreleri"""
    __tablename__ = 'count_passwords'
    
    id = db.Column(db.Integer, primary_key=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def __repr__(self):
        return f'<CountPassword {self.id}>'
