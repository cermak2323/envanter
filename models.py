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
    Kullanıcılar - Production PostgreSQL şemasıyla tam uyum
    
    Production (cermakservis + EnvanterQR):
    - Core: id, username, password, password_hash, full_name, role, created_at
    - Extended: email, real_name, job_title, title, work_position, user_group, user_role
    - Files: signature_path, profile_image_path
    - Status: is_active_user, can_mark_used
    - 2FA: email_2fa_enabled, email_2fa_code, email_2fa_expires, email_2fa_attempts, email_2fa_locked_until
    - Security: tc_number, last_password_change, force_password_change, force_tutorial
    - Login: first_login_completed, last_login
    - Approvals: terms_accepted
    - Timestamps: updated_at
    
    Toplam: 31 kolon
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Core (her zaman var)
    username = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255))  # Backward compat
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')  # admin, user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Extended (cermakservis compatibility)
    real_name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    job_title = db.Column(db.String(120))
    title = db.Column(db.String(120))
    work_position = db.Column(db.String(120))
    user_group = db.Column(db.String(120))
    user_role = db.Column(db.String(120))
    
    # Files
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
    
    # Security
    tc_number = db.Column(db.String(20))
    last_password_change = db.Column(db.DateTime)
    force_password_change = db.Column(db.Boolean, default=False)
    force_tutorial = db.Column(db.Boolean, default=False)
    
    # Login
    first_login_completed = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    
    # Approvals
    terms_accepted = db.Column(db.Boolean, default=False)
    
    # Timestamps
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
