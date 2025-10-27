#!/usr/bin/env python3
"""
Render.com Python startup script
"""
import os
import sys
import subprocess

def main():
    print("🚀 EnvanterQR Render.com Startup")
    
    # Create directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    os.makedirs("static/temp", exist_ok=True)
    
    # Environment check
    print(f"🐍 Python: {sys.version}")
    print(f"🌐 PORT: {os.environ.get('PORT', 'Not set')}")
    
    # Database test
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        print("✅ Database connection OK")
        conn.close()
    except Exception as e:
        print(f"⚠️ Database test failed: {e}")
    
    # Start gunicorn
    port = os.environ.get('PORT', '10000')
    cmd = [
        sys.executable, '-m', 'gunicorn',
        '--worker-class', 'eventlet',
        '-w', '1',
        '--bind', f'0.0.0.0:{port}',
        '--timeout', '120',
        'app:app'
    ]
    
    print(f"🚀 Starting: {' '.join(cmd)}")
    os.execvp(sys.executable, cmd)

if __name__ == "__main__":
    main()