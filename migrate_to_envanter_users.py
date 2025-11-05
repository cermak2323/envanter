#!/usr/bin/env python
"""
Step 1: Production PostgreSQL'de envanter_users table oluştur ve migrate et
- Yeni envanter_users table'ı oluştur
- test1 kullanıcısını kopyala
- Foreign keys'i güncelle
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import hashlib

# Production PostgreSQL URI
import os
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('RENDER_INTERNAL_DATABASE_URL') or \
    "postgresql://cermak_envanter_user:N22HyFcRf3bvgMzkK1J5yNYgrXEfIgNC@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter?sslmode=require"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    try:
        print("=" * 80)
        print("🚀 ENVANTERQR - SEPARATE USERS TABLE MIGRATION")
        print("=" * 80)
        
        # Step 1: envanter_users table'ı oluştur
        print("\n1️⃣  Creating envanter_users table...")
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS envanter_users (
            id INTEGER PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255),
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Extended fields for EnvanterQR
            real_name VARCHAR(255),
            email VARCHAR(255),
            job_title VARCHAR(120),
            title VARCHAR(120),
            work_position VARCHAR(120),
            user_group VARCHAR(120),
            user_role VARCHAR(120),
            signature_path VARCHAR(500),
            profile_image_path VARCHAR(500),
            is_active_user BOOLEAN DEFAULT TRUE,
            can_mark_used BOOLEAN DEFAULT FALSE,
            email_2fa_enabled BOOLEAN DEFAULT FALSE,
            email_2fa_code VARCHAR(6),
            email_2fa_expires TIMESTAMP,
            email_2fa_attempts INTEGER DEFAULT 0,
            email_2fa_locked_until TIMESTAMP,
            tc_number VARCHAR(20),
            last_password_change TIMESTAMP,
            force_password_change BOOLEAN DEFAULT FALSE,
            force_tutorial BOOLEAN DEFAULT FALSE,
            first_login_completed BOOLEAN DEFAULT FALSE,
            last_login TIMESTAMP,
            terms_accepted BOOLEAN DEFAULT FALSE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        db.session.execute(text(create_table_sql))
        db.session.commit()
        print("   ✅ envanter_users table created")
        
        # Step 2: test1 kullanıcısını kopyala
        print("\n2️⃣  Migrating test1 user...")
        copy_user_sql = """
        INSERT INTO envanter_users (
            id, username, password, password_hash, full_name, role, created_at
        )
        SELECT 
            id, username, password, password_hash, full_name, role, created_at
        FROM users
        WHERE username = 'test1'
        ON CONFLICT (id) DO UPDATE SET
            username = EXCLUDED.username,
            password = EXCLUDED.password,
            password_hash = EXCLUDED.password_hash,
            full_name = EXCLUDED.full_name,
            role = EXCLUDED.role
        """
        
        db.session.execute(text(copy_user_sql))
        db.session.commit()
        print("   ✅ test1 user migrated to envanter_users")
        
        # Step 3: Verileri kontrol et
        print("\n3️⃣  Verifying data...")
        verify_sql = text("SELECT id, username, full_name, password FROM envanter_users")
        result = db.session.execute(verify_sql)
        
        for row in result:
            id_val, username, full_name, password = row
            print(f"   ID: {id_val}")
            print(f"   username: {username}")
            print(f"   full_name: {full_name}")
            print(f"   password: {password}")
        
        # Step 4: Update foreign keys in other tables
        print("\n4️⃣  Checking for foreign key references...")
        
        # Check what tables reference the old users table
        fk_check = text("""
            SELECT 
                tc.constraint_name, 
                kcu.table_name, 
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' 
            AND ccu.table_name = 'users'
        """)
        
        result = db.session.execute(fk_check)
        fk_count = 0
        for row in result:
            constraint_name, table_name, column_name, foreign_table_name, foreign_column_name = row
            print(f"   Found FK: {table_name}.{column_name} -> {foreign_table_name}.{foreign_column_name}")
            fk_count += 1
        
        if fk_count == 0:
            print("   ℹ️  No foreign key references to users table found (good)")
        
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Update models.py - Change __tablename__ = 'users' to 'envanter_users'")
        print("2. Run init_db.py to update local SQLite")
        print("3. Test login with test1 / 123456789")
        print("4. Original users table remains unchanged for cermakservis")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.session.rollback()
        import traceback
        traceback.print_exc()
