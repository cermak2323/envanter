#!/usr/bin/env python3
"""
Render.com Build and Install Script
Force installs dependencies and starts application
"""
import os
import sys
import subprocess
import time

def run_command(cmd, description, timeout=300):
    """Run command with error handling"""
    print(f"🔧 {description}")
    print(f"📝 Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout:
                print(f"📄 Output: {result.stdout[:500]}")  # First 500 chars
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"📄 Error: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT ({timeout}s)")
        return False
    except Exception as e:
        print(f"💥 {description} - EXCEPTION: {e}")
        return False

def main():
    print("🚀 RENDER.COM FORCE BUILD & INSTALL")
    print("=" * 60)
    
    # Environment info
    print(f"🐍 Python: {sys.executable}")
    print(f"📁 Working Dir: {os.getcwd()}")
    print(f"🌐 Port: {os.environ.get('PORT', '10000')}")
    
    # Upgrade pip first
    print(f"\n📦 STEP 1: Upgrade pip")
    run_command([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                "Upgrading pip", 120)
    
    # Install requirements
    print(f"\n📦 STEP 2: Install requirements")
    if os.path.exists('requirements.txt'):
        success = run_command([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                            "Installing requirements.txt", 300)
        
        if not success:
            print("🔄 Trying with --no-cache-dir")
            run_command([sys.executable, '-m', 'pip', 'install', '--no-cache-dir', '-r', 'requirements.txt'], 
                       "Installing requirements (no cache)", 300)
    else:
        print("❌ requirements.txt not found!")
        return False
    
    # Verify critical packages
    print(f"\n✅ STEP 3: Verify installations")
    critical_packages = ['flask', 'psycopg2', 'eventlet']
    
    all_installed = True
    for package in critical_packages:
        try:
            __import__(package)
            print(f"✅ {package} - OK")
        except ImportError:
            print(f"❌ {package} - MISSING, attempting individual install")
            
            # Try individual install
            pkg_name = package
            if package == 'psycopg2':
                pkg_name = 'psycopg2-binary'
                
            success = run_command([sys.executable, '-m', 'pip', 'install', pkg_name], 
                                f"Installing {pkg_name}", 120)
            
            if not success:
                all_installed = False
    
    if not all_installed:
        print("❌ Some packages failed to install")
        return False
    
    # Create directories
    print(f"\n📁 STEP 4: Create directories")
    directories = ['uploads', 'reports', 'static/temp', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    # Start application
    print(f"\n🚀 STEP 5: Start application")
    port = int(os.environ.get('PORT', 10000))
    
    # Force production environment
    os.environ['RENDER'] = 'true'
    os.environ['FLASK_ENV'] = 'production'
    
    try:
        print("🔄 Importing application...")
        from app import app, socketio
        print("✅ Application imported successfully")
        
        print(f"🌐 Starting on 0.0.0.0:{port}")
        socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
        
    except Exception as e:
        print(f"❌ Application start failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()