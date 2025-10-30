#!/usr/bin/env python
"""PostgreSQL'deki users tablosunun schema'sını kontrol et"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect

# Production PostgreSQL URI (hardcoded from app.py)
import os
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('RENDER_INTERNAL_DATABASE_URL') or \
    "postgresql://cermak_envanter_user:N22HyFcRf3bvgMzkK1J5yNYgrXEfIgNC@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter?sslmode=require"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    try:
        # PostgreSQL'deki users tablosunun yapısını göster
        inspector = inspect(db.engine)
        columns = inspector.get_columns('users')
        
        print('🗄️  PRODUCTION PostgreSQL users SCHEMA:')
        print('=' * 70)
        for i, col in enumerate(columns, 1):
            col_type = str(col['type'])
            nullable = 'NULL' if col['nullable'] else 'NOT NULL'
            print(f'{i:2d}. {col["name"]:<30} {col_type:<20} {nullable}')
        
        print('\n📊 Toplam kolon sayısı:', len(columns))
        print('\n📝 Kolonların sadece isimleri (models.py\'ye kopyalamak için):')
        col_names = [f"'{col['name']}'" for col in columns]
        print('[' + ', '.join(col_names) + ']')
        
    except Exception as e:
        print(f'❌ Hata: {e}')
        import traceback
        traceback.print_exc()
