#!/usr/bin/env python
"""Check local SQLite after migration"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from app import app
with app.app_context():
    from models import User, db
    from sqlalchemy import inspect
    
    # Check if envanter_users table exists
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    print('📋 Tables in local SQLite:')
    for t in sorted(tables):
        print(f'  - {t}')
    
    if 'envanter_users' in tables:
        print('\n✅ envanter_users table exists')
        cols = inspector.get_columns('envanter_users')
        print(f'   Total columns: {len(cols)}')
        for i, col in enumerate(cols[:7], 1):
            col_name = col['name']
            col_type = str(col['type'])
            print(f'   {i}. {col_name}: {col_type}')
        if len(cols) > 7:
            print(f'   ... (+{len(cols)-7} more columns)')
    else:
        print('\n❌ envanter_users table NOT found')
        print('   Available tables:', tables)
