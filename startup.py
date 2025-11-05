#!/usr/bin/env python3
"""
Render.com Python startup script with fallback options
"""
import os
import sys
import subprocess
import shutil

def find_python():
    """Find available Python executable"""
    python_candidates = [
        'python3',
        'python',
        sys.executable,
        '/usr/bin/python3',
        '/usr/bin/python',
        '/opt/render/project/src/.venv/bin/python'
    ]
    
    for candidate in python_candidates:
        if candidate and shutil.which(candidate):
            print(f"✅ Found Python: {candidate}")
            return candidate
    
    print("❌ No Python executable found!")
    return None

def main():
    print("🚀 EnvanterQR Render.com Startup")
    
    # Find Python executable
    python_exe = find_python()
    if not python_exe:
        print("Available executables:")
        for path in os.environ.get('PATH', '').split(':'):
            if os.path.isdir(path):
                try:
                    files = [f for f in os.listdir(path) if 'python' in f.lower()]
                    if files:
                        print(f"  {path}: {files}")
                except:
                    pass
        sys.exit(1)
    
    # Create directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    os.makedirs("static/temp", exist_ok=True)
    
    # Environment check
    print(f"🐍 Python version: {sys.version}")
    print(f"🌐 PORT: {os.environ.get('PORT', 'Not set')}")
    print(f"📁 Working dir: {os.getcwd()}")
    
    # Database test
    try:
        import psycopg2
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            conn = psycopg2.connect(database_url)
            print("✅ Database connection OK")
            conn.close()
        else:
            print("⚠️ DATABASE_URL not set")
    except Exception as e:
        print(f"⚠️ Database test failed: {e}")
    
    # Start application
    port = os.environ.get('PORT', '10000')
    
    # Check if gunicorn is available
    try:
        import gunicorn
        print("✅ Gunicorn available")
        
        cmd = [
            python_exe, '-m', 'gunicorn',
            '--worker-class', 'eventlet',
            '-w', '1',
            '--bind', f'0.0.0.0:{port}',
            '--timeout', '120',
            'app:app'
        ]
        
        print(f"🚀 Starting gunicorn: {' '.join(cmd)}")
        os.execvp(python_exe, cmd)
        
    except ImportError:
        print("⚠️ Gunicorn not available, starting Flask directly")
        
        # Direct Flask startup
        try:
            print("🔄 Starting Flask development server")
            os.environ['FLASK_ENV'] = 'production'
            
            # Import and run Flask app
            sys.path.insert(0, os.getcwd())
            from app import app
            
            print(f"🚀 Flask starting on 0.0.0.0:{port}")
            app.run(host='0.0.0.0', port=int(port), debug=False, threaded=True)
            
        except Exception as e2:
            print(f"❌ Flask direct start failed: {e2}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Gunicorn failed: {e}")
        
        # Fallback to direct Flask
        try:
            print("🔄 Fallback: Starting Flask directly")
            os.environ['FLASK_ENV'] = 'production'
            
            sys.path.insert(0, os.getcwd())
            from app import app
            
            print(f"🚀 Flask fallback starting on 0.0.0.0:{port}")
            app.run(host='0.0.0.0', port=int(port), debug=False, threaded=True)
            
        except Exception as e2:
            print(f"❌ Flask direct start failed: {e2}")
            sys.exit(1)

if __name__ == "__main__":
    main()