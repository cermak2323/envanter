-- EnvanterQR Database Schema for Render.com PostgreSQL
-- Bu dosya Render.com deploy sonrası manuel olarak çalıştırılacak
-- Render PostgreSQL Dashboard'da çalıştırın

-- RENDER.COM DEPLOY NOTES:
-- 1. Render.com'da PostgreSQL database oluşturun
-- 2. Database connection string'i uygulama environment variables'a ekleyin
-- 3. Bu SQL script'i Render database dashboard'da çalıştırın

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS count_passwords CASCADE;
DROP TABLE IF EXISTS count_reports CASCADE;
DROP TABLE IF EXISTS scanned_qr CASCADE;
DROP TABLE IF EXISTS inventory_data CASCADE;
DROP TABLE IF EXISTS count_sessions CASCADE;
DROP TABLE IF EXISTS qr_codes CASCADE;
DROP TABLE IF EXISTS parts CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Create Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Parts table
CREATE TABLE parts (
    id SERIAL PRIMARY KEY,
    part_code VARCHAR(255) NOT NULL,
    part_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create QR Codes table
CREATE TABLE qr_codes (
    id SERIAL PRIMARY KEY,
    qr_id VARCHAR(255) UNIQUE NOT NULL,
    part_code VARCHAR(255) NOT NULL,
    part_name VARCHAR(255) NOT NULL,
    location VARCHAR(255) DEFAULT 'Belirtilmemiş',
    is_used INTEGER DEFAULT 0,
    is_downloaded INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP,
    downloaded_at TIMESTAMP
);

-- Create Count Sessions table
CREATE TABLE count_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);

-- Create Inventory Data table
CREATE TABLE inventory_data (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    part_code VARCHAR(255) NOT NULL,
    part_name VARCHAR(255) NOT NULL,
    expected_quantity INTEGER NOT NULL,
    CONSTRAINT fk_inventory_session
        FOREIGN KEY (session_id) REFERENCES count_sessions(session_id)
);

-- Create Scanned QR table
CREATE TABLE scanned_qr (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    qr_id VARCHAR(255) NOT NULL,
    part_code VARCHAR(255) NOT NULL,
    scanned_by INTEGER,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_scanned_session
        FOREIGN KEY (session_id) REFERENCES count_sessions(session_id),
    CONSTRAINT fk_scanned_qr
        FOREIGN KEY (qr_id) REFERENCES qr_codes(qr_id)
);

-- Create Count Reports table
CREATE TABLE count_reports (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    report_filename VARCHAR(255) NOT NULL,
    report_title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_expected INTEGER DEFAULT 0,
    total_scanned INTEGER DEFAULT 0,
    accuracy_rate DECIMAL(5,2) DEFAULT 0.00,
    CONSTRAINT fk_report_session
        FOREIGN KEY (session_id) REFERENCES count_sessions(session_id)
);

-- Create Count Passwords table
CREATE TABLE count_passwords (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(8) NOT NULL,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_used INTEGER DEFAULT 0,
    CONSTRAINT fk_password_session
        FOREIGN KEY (session_id) REFERENCES count_sessions(session_id),
    CONSTRAINT fk_password_created_by
        FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Create indexes for better performance
CREATE INDEX idx_qr_codes_qr_id ON qr_codes(qr_id);
CREATE INDEX idx_qr_codes_part_code ON qr_codes(part_code);
CREATE INDEX idx_count_sessions_status ON count_sessions(status);
CREATE INDEX idx_scanned_qr_session ON scanned_qr(session_id);
CREATE INDEX idx_users_username ON users(username);

-- Insert default admin user
INSERT INTO users (username, password, password_hash, full_name, role) 
VALUES ('admin', 'admin123', 'f7c3bc1d808e04732adf679965ccc34ca7ae3441b', 'Administrator', 'admin');

-- Grant permissions (if needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO neondb_owner;