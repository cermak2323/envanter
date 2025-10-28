#!/usr/bin/env python3
"""
Alternative Render.com Startup - Force Install & Run
"""
import os
import sys
import subprocess

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                      check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print("🚀 ALTERNATIVE RENDER STARTUP")
    print(f"🐍 Python: {sys.version}")
    print(f"📁 Working dir: {os.getcwd()}")
    
    # Force production environment
    os.environ['RENDER'] = 'true'
    os.environ['FLASK_ENV'] = 'production'
    
    # Create directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    
    # Essential packages to install
    essential_packages = [
        'flask>=3.1.0',
        'flask-socketio>=5.5.0',
        'psycopg2-binary>=2.9.0',
        'eventlet>=0.35.0',
        'python-dotenv>=1.0.0',
        'gunicorn>=21.0.0'
    ]
    
    print("📦 Installing essential packages...")
    for package in essential_packages:
        print(f"  Installing {package}...")
        if install_package(package):
            print(f"  ✅ {package}")
        else:
            print(f"  ❌ {package}")
    
    # Try importing Flask
    try:
        import flask
        print(f"✅ Flask {flask.__version__} ready")
    except ImportError:
        print("❌ Flask still not available")
        sys.exit(1)
    
    # Import and run app
    try:
        print("🔄 Importing application...")
        from app import app, socketio
        
        port = int(os.environ.get('PORT', 10000))
        print(f"🚀 Starting on 0.0.0.0:{port}")
        
        socketio.run(app, host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()