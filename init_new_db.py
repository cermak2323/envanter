#!/usr/bin/env python
"""
Yeni cermak_envanter veritabanında gerekli tabloları oluştur
Bu script sadece bir kez çalıştırılmalıdır.
"""

import os
import psycopg2
import hashlib
from datetime import datetime

# Yeni veritabanı bağlantısı
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('RENDER_INTERNAL_DATABASE_URL') or \
    "postgresql://cermak_envanter_user:N22HyFcRf3bvgMzkK1J5yNYgrXEfIgNC@dpg-d41mgsje5dus73df6o40-a.oregon-postgres.render.com:5432/cermak_envanter?sslmode=require"

def create_database_schema():
    """Yeni veritabanında tüm tabloları oluştur"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("\n" + "=" * 80)
        print("🚀 YENİ VERİTABANI SCHEMA OLUŞTURULUYOR")
        print("=" * 80)
        
        # 1. USERS TABLOSU (CermakServis için)
        print("\n1️⃣  USERS tablosu oluşturuluyor...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255),
                password_hash VARCHAR(255),
                full_name VARCHAR(100),
                email VARCHAR(100),
                role VARCHAR(20) DEFAULT 'user',
                is_active BOOLEAN DEFAULT true,
                is_active_user BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                
                -- Permission columns
                can_view_reports BOOLEAN DEFAULT false,
                can_create_count BOOLEAN DEFAULT false,
                can_manage_users BOOLEAN DEFAULT false,
                can_export_data BOOLEAN DEFAULT false,
                can_delete_data BOOLEAN DEFAULT false,
                can_view_admin BOOLEAN DEFAULT false,
                can_edit_inventory BOOLEAN DEFAULT false,
                can_view_inventory BOOLEAN DEFAULT true,
                can_scan_qr BOOLEAN DEFAULT true,
                can_generate_qr BOOLEAN DEFAULT false,
                can_upload_parts BOOLEAN DEFAULT false,
                can_download_reports BOOLEAN DEFAULT false,
                can_manage_sessions BOOLEAN DEFAULT false,
                can_view_analytics BOOLEAN DEFAULT false,
                can_backup_data BOOLEAN DEFAULT false,
                can_restore_data BOOLEAN DEFAULT false,
                can_manage_permissions BOOLEAN DEFAULT false,
                can_view_logs BOOLEAN DEFAULT false,
                can_system_config BOOLEAN DEFAULT false,
                can_api_access BOOLEAN DEFAULT false,
                can_bulk_operations BOOLEAN DEFAULT false
            )
        """)
        print("   ✅ USERS tablosu oluşturuldu")
        
        # 2. ENVANTER_USERS TABLOSU (EnvanterQR için)
        print("\n2️⃣  ENVANTER_USERS tablosu oluşturuluyor...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS envanter_users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255),
                password_hash VARCHAR(255),
                full_name VARCHAR(100),
                email VARCHAR(100),
                role VARCHAR(20) DEFAULT 'user',
                is_active BOOLEAN DEFAULT true,
                is_active_user BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                
                -- Permission columns
                can_view_reports BOOLEAN DEFAULT false,
                can_create_count BOOLEAN DEFAULT false,
                can_manage_users BOOLEAN DEFAULT false,
                can_export_data BOOLEAN DEFAULT false,
                can_delete_data BOOLEAN DEFAULT false,
                can_view_admin BOOLEAN DEFAULT false,
                can_edit_inventory BOOLEAN DEFAULT false,
                can_view_inventory BOOLEAN DEFAULT true,
                can_scan_qr BOOLEAN DEFAULT true,
                can_generate_qr BOOLEAN DEFAULT false,
                can_upload_parts BOOLEAN DEFAULT false,
                can_download_reports BOOLEAN DEFAULT false,
                can_manage_sessions BOOLEAN DEFAULT false,
                can_view_analytics BOOLEAN DEFAULT false,
                can_backup_data BOOLEAN DEFAULT false,
                can_restore_data BOOLEAN DEFAULT false,
                can_manage_permissions BOOLEAN DEFAULT false,
                can_view_logs BOOLEAN DEFAULT false,
                can_system_config BOOLEAN DEFAULT false,
                can_api_access BOOLEAN DEFAULT false,
                can_bulk_operations BOOLEAN DEFAULT false
            )
        """)
        print("   ✅ ENVANTER_USERS tablosu oluşturuldu")
        
        # 3. PARTS TABLOSU
        print("\n3️⃣  PARTS tablosu oluşturuluyor...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parts (
                id SERIAL PRIMARY KEY,
                part_code VARCHAR(100) UNIQUE NOT NULL,
                part_name VARCHAR(255) NOT NULL,
                quantity INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ PARTS tablosu oluşturuldu")
        
        # 4. QR_CODES TABLOSU
        print("\n4️⃣  QR_CODES tablosu oluşturuluyor...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS qr_codes (
                id SERIAL PRIMARY KEY,
                qr_id VARCHAR(255) UNIQUE NOT NULL,
                part_code VARCHAR(100) NOT NULL,
                part_name VARCHAR(255),
                is_used BOOLEAN DEFAULT false,
                is_downloaded BOOLEAN DEFAULT false,
                used_at TIMESTAMP,
                downloaded_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (part_code) REFERENCES parts(part_code) ON DELETE CASCADE
            )
        """)
        print("   ✅ QR_CODES tablosu oluşturuldu")
        
        # 5. COUNT_SESSIONS TABLOSU
        print("\n5️⃣  COUNT_SESSIONS tablosu oluşturuluyor...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS count_sessions (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) UNIQUE NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES envanter_users(id) ON DELETE SET NULL
            )
        """)
        print("   ✅ COUNT_SESSIONS tablosu oluşturuldu")
        
        # 6. COUNT_PASSWORDS TABLOSU
        print("\n6️⃣  COUNT_PASSWORDS tablosu oluşturuluyor...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS count_passwords (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                password VARCHAR(50) NOT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES count_sessions(session_id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES envanter_users(id) ON DELETE SET NULL
            )
        """)
        print("   ✅ COUNT_PASSWORDS tablosu oluşturuldu")
        
        # 7. SCANNED_QR TABLOSU
        print("\n7️⃣  SCANNED_QR tablosu oluşturuluyor...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scanned_qr (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                qr_id VARCHAR(255) NOT NULL,
                part_code VARCHAR(100),
                scanned_by INTEGER,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES count_sessions(session_id) ON DELETE CASCADE,
                FOREIGN KEY (scanned_by) REFERENCES envanter_users(id) ON DELETE SET NULL
            )
        """)
        print("   ✅ SCANNED_QR tablosu oluşturuldu")
        
        # 8. COUNT_REPORTS TABLOSU
        print("\n8️⃣  COUNT_REPORTS tablosu oluşturuluyor...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS count_reports (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                report_filename VARCHAR(255),
                report_title VARCHAR(255),
                total_expected INTEGER DEFAULT 0,
                total_scanned INTEGER DEFAULT 0,
                accuracy_rate DECIMAL(5,2) DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES count_sessions(session_id) ON DELETE CASCADE
            )
        """)
        print("   ✅ COUNT_REPORTS tablosu oluşturuldu")
        
        # 9. INVENTORY_DATA TABLOSU
        print("\n9️⃣  INVENTORY_DATA tablosu oluşturuluyor...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_data (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                part_code VARCHAR(100) NOT NULL,
                part_name VARCHAR(255),
                expected_quantity INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES count_sessions(session_id) ON DELETE CASCADE
            )
        """)
        print("   ✅ INVENTORY_DATA tablosu oluşturuldu")
        
        # 10. DEFAULT ADMIN KULLANICILARI OLUŞTUR
        print("\n🔐 Default admin kullanıcıları oluşturuluyor...")
        
        # USERS tablosuna admin
        admin_password = "admin123"
        admin_hash = hashlib.sha256(admin_password.encode()).hexdigest()
        cursor.execute("""
            INSERT INTO users (username, password, password_hash, full_name, role, 
                             can_view_reports, can_create_count, can_manage_users, can_export_data,
                             can_delete_data, can_view_admin, can_edit_inventory, can_generate_qr,
                             can_upload_parts, can_download_reports, can_manage_sessions,
                             can_view_analytics, can_backup_data, can_restore_data,
                             can_manage_permissions, can_view_logs, can_system_config,
                             can_api_access, can_bulk_operations)
            VALUES (%s, %s, %s, %s, %s, 
                    true, true, true, true, true, true, true, true, true, true,
                    true, true, true, true, true, true, true, true, true)
            ON CONFLICT (username) DO NOTHING
        """, ('admin', admin_password, admin_hash, 'System Administrator', 'admin'))
        
        # ENVANTER_USERS tablosuna admin
        cursor.execute("""
            INSERT INTO envanter_users (username, password, password_hash, full_name, role,
                                      can_view_reports, can_create_count, can_manage_users, can_export_data,
                                      can_delete_data, can_view_admin, can_edit_inventory, can_generate_qr,
                                      can_upload_parts, can_download_reports, can_manage_sessions,
                                      can_view_analytics, can_backup_data, can_restore_data,
                                      can_manage_permissions, can_view_logs, can_system_config,
                                      can_api_access, can_bulk_operations)
            VALUES (%s, %s, %s, %s, %s,
                    true, true, true, true, true, true, true, true, true, true,
                    true, true, true, true, true, true, true, true, true)
            ON CONFLICT (username) DO NOTHING
        """, ('admin', admin_password, admin_hash, 'EnvanterQR Administrator', 'admin'))
        
        print("   ✅ Admin kullanıcıları oluşturuldu (admin/admin123)")
        
        # 11. İNDEXLER OLUŞTUR
        print("\n📊 Performans indexleri oluşturuluyor...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_envanter_users_username ON envanter_users(username);", 
            "CREATE INDEX IF NOT EXISTS idx_envanter_users_active ON envanter_users(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_qr_codes_qr_id ON qr_codes(qr_id);",
            "CREATE INDEX IF NOT EXISTS idx_qr_codes_part_code ON qr_codes(part_code);",
            "CREATE INDEX IF NOT EXISTS idx_qr_codes_used ON qr_codes(is_used);",
            "CREATE INDEX IF NOT EXISTS idx_count_sessions_status ON count_sessions(status);",
            "CREATE INDEX IF NOT EXISTS idx_scanned_qr_session ON scanned_qr(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_scanned_qr_datetime ON scanned_qr(scanned_at);",
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        print("   ✅ Performans indexleri oluşturuldu")
        
        # Commit ve bağlantıyı kapat
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print("✅ YENİ VERİTABANI BAŞARIYLA OLUŞTURULDU!")
        print("=" * 80)
        print("📋 Oluşturulan tablolar:")
        print("   • users (CermakServis kullanıcıları)")
        print("   • envanter_users (EnvanterQR kullanıcıları)")
        print("   • parts (Parça kodları)")
        print("   • qr_codes (QR kodları)")
        print("   • count_sessions (Sayım oturumları)")
        print("   • count_passwords (Sayım şifreleri)")
        print("   • scanned_qr (Taranan QR kodları)")
        print("   • count_reports (Sayım raporları)")
        print("   • inventory_data (Envanter verileri)")
        print("\n🔐 Default kullanıcılar:")
        print("   • admin/admin123 (USERS - CermakServis)")
        print("   • admin/admin123 (ENVANTER_USERS - EnvanterQR)")
        print("\n🚀 Sistem artık yeni veritabanına geçti!")
        print("=" * 80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ HATA: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    create_database_schema()