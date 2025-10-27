#!/bin/bash

# Render.com Startup Script for EnvanterQR
echo "🚀 Starting EnvanterQR deployment on Render.com..."

# Environment check
echo "📋 Environment Variables Check:"
echo "DATABASE_URL: ${DATABASE_URL:0:20}..."
echo "SESSION_SECRET: ${SESSION_SECRET:0:10}..."
echo "B2_APPLICATION_KEY_ID: ${B2_APPLICATION_KEY_ID:0:10}..."

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p reports
mkdir -p static/temp

# Set permissions
echo "🔒 Setting permissions..."
chmod 755 logs
chmod 755 reports
chmod 755 static/temp

# Database check and setup
echo "🗄️ Database setup..."
python -c "
try:
    import psycopg2
    import os
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

# Start the application
echo "🌐 Starting application..."
exec gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT --timeout 120 --keep-alive 2 --max-requests 1000 --max-requests-jitter 50 app:app