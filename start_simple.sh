#!/bin/bash
# Simple Render.com startup script

echo "🚀 Starting EnvanterQR on Render.com..."

# Create directories
mkdir -p logs reports static/temp
chmod -R 755 logs reports static/temp

# Check Python environment
echo "🐍 Python: $(python --version 2>&1 || python3 --version 2>&1)"

# Database connectivity test
echo "🗄️ Testing database connection..."
python -c "
import os
try:
    import psycopg2
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    print('✅ Database connection OK')
    conn.close()
except Exception as e:
    print(f'⚠️ Database test: {e}')
" 2>/dev/null || python3 -c "
import os
try:
    import psycopg2
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    print('✅ Database connection OK')
    conn.close()
except Exception as e:
    print(f'⚠️ Database test: {e}')
" 2>/dev/null || echo "⚠️ Skipping DB test"

# Start application
echo "🚀 Starting gunicorn..."
exec gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT --timeout 120 app:app