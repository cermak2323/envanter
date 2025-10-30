#!/usr/bin/env python
"""
Production PostgreSQL'de users tablosuna eksik kolonları ekle
cermakservis uygulamasının ihtiyacı olan alanlara uyumlu

⚠️  SADECE eksik koloanları ekle, mevcut olanları değiştirme!
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect

# Production PostgreSQL URI
import os
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('RENDER_INTERNAL_DATABASE_URL') or \
    "postgresql://cermak_envanter_user:N22HyFcRf3bvgMzkK1J5yNYgrXEfIgNC@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter?sslmode=require"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# cermakservis uygulamasının bekleyebileceği kolonlar
# (EnvanterQR tarafından eklenmesi gerekebilecekler)
OPTIONAL_COLUMNS = [
    ('real_name', 'VARCHAR(255)'),
    ('email', 'VARCHAR(255)'),
    ('job_title', 'VARCHAR(120)'),
    ('title', 'VARCHAR(120)'),
    ('work_position', 'VARCHAR(120)'),
    ('user_group', 'VARCHAR(120)'),
    ('user_role', 'VARCHAR(120)'),
    ('signature_path', 'VARCHAR(500)'),
    ('profile_image_path', 'VARCHAR(500)'),
    ('is_active_user', 'BOOLEAN DEFAULT TRUE'),
    ('can_mark_used', 'BOOLEAN DEFAULT FALSE'),
    ('email_2fa_enabled', 'BOOLEAN DEFAULT FALSE'),
    ('email_2fa_code', 'VARCHAR(6)'),
    ('email_2fa_expires', 'TIMESTAMP'),
    ('email_2fa_attempts', 'INTEGER DEFAULT 0'),
    ('email_2fa_locked_until', 'TIMESTAMP'),
    ('tc_number', 'VARCHAR(20)'),
    ('last_password_change', 'TIMESTAMP'),
    ('force_password_change', 'BOOLEAN DEFAULT FALSE'),
    ('force_tutorial', 'BOOLEAN DEFAULT FALSE'),
    ('first_login_completed', 'BOOLEAN DEFAULT FALSE'),
    ('last_login', 'TIMESTAMP'),
    ('terms_accepted', 'BOOLEAN DEFAULT FALSE'),
    ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
]

def add_missing_columns():
    """Eksik kolonları ekle"""
    with app.app_context():
        try:
            # Mevcut kolonları kontrol et
            inspector = inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('users')]
            
            print("📋 Mevcut users kolonları:", existing_columns)
            print()
            
            added_count = 0
            for col_name, col_type in OPTIONAL_COLUMNS:
                if col_name not in existing_columns:
                    print(f"➕ Adding column: {col_name} ({col_type})")
                    try:
                        sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                        db.session.execute(text(sql))
                        db.session.commit()
                        print(f"   ✅ Success")
                        added_count += 1
                    except Exception as e:
                        db.session.rollback()
                        print(f"   ❌ Error: {str(e)}")
                else:
                    print(f"✅ Already exists: {col_name}")
            
            print()
            print(f"📊 Added {added_count} columns")
            
            # Son schema'yı göster
            print("\n🗄️  UPDATED users SCHEMA:")
            print("=" * 70)
            inspector = inspect(db.engine)
            columns = inspector.get_columns('users')
            for i, col in enumerate(columns, 1):
                col_type = str(col['type'])
                nullable = 'NULL' if col['nullable'] else 'NOT NULL'
                print(f'{i:2d}. {col["name"]:<30} {col_type:<20} {nullable}')
            
            print(f'\n📊 Toplam kolon: {len(columns)}')
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    add_missing_columns()
