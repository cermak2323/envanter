#!/usr/bin/env python
"""Migrate test1 user to local SQLite"""

from app import app
with app.app_context():
    from models import User, db
    import hashlib
    
    # Check if test1 exists
    existing = User.query.filter_by(username='test1').first()
    if existing:
        print('✅ test1 already in local database')
        print(f'   ID: {existing.id}')
        print(f'   full_name: {existing.full_name}')
        print(f'   password: {existing.password}')
        exit(0)
    
    # Create test1 user
    print('Creating test1 user in local SQLite...')
    user = User(
        id=3,  # Same ID as production
        username='test1',
        full_name='Muhammed Emir ERSÜT',
        password='123456789',
        password_hash=hashlib.sha256('123456789'.encode()).hexdigest(),
        role='admin'
    )
    db.session.add(user)
    db.session.commit()
    
    print('\n✅ test1 user created')
    print(f'   ID: {user.id}')
    print(f'   username: {user.username}')
    print(f'   full_name: {user.full_name}')
    print(f'   password: {user.password}')
    print(f'   role: {user.role}')
    
    # Test login
    print('\n🔐 Testing login...')
    test_user = User.query.filter_by(username='test1').first()
    if test_user:
        print(f'✅ User found: {test_user.username}')
        if test_user.password == '123456789':
            print('✅ Password matches!')
        else:
            print('❌ Password does NOT match')
    else:
        print('❌ User not found')
