#!/usr/bin/env python3
"""
Render.com Diagnostic Script - Environment and Dependencies Check
"""
import os
import sys
import subprocess

def main():
    print("🔍 RENDER.COM ENVIRONMENT DIAGNOSTIC")
    print("=" * 50)
    
    # Basic environment info
    print(f"🐍 Python Executable: {sys.executable}")
    print(f"🐍 Python Version: {sys.version}")
    print(f"📁 Working Directory: {os.getcwd()}")
    print(f"🌐 PORT: {os.environ.get('PORT', 'Not set')}")
    print(f"🏗️ RENDER: {os.environ.get('RENDER', 'Not set')}")
    
    # Check PATH
    print(f"\n📍 PATH Environment:")
    for path in os.environ.get('PATH', '').split(':')[:10]:  # First 10 paths
        print(f"  - {path}")
    
    # Check if requirements.txt exists
    print(f"\n📦 Requirements File:")
    if os.path.exists('requirements.txt'):
        print("✅ requirements.txt exists")
        with open('requirements.txt', 'r') as f:
            lines = f.readlines()[:10]  # First 10 lines
            for line in lines:
                print(f"  - {line.strip()}")
    else:
        print("❌ requirements.txt NOT FOUND")
    
    # Check installed packages
    print(f"\n📚 Installed Packages Check:")
    required_modules = ['flask', 'psycopg2', 'gunicorn', 'eventlet']
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} - INSTALLED")
        except ImportError:
            print(f"❌ {module} - NOT INSTALLED")
    
    # Check pip
    print(f"\n🔧 Pip Information:")
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                              capture_output=True, text=True, timeout=10)
        print(f"✅ Pip version: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Pip check failed: {e}")
    
    # Try to list installed packages
    print(f"\n📋 Installed Packages (pip list):")
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                              capture_output=True, text=True, timeout=15)
        lines = result.stdout.split('\n')[:15]  # First 15 packages
        for line in lines:
            if line.strip():
                print(f"  {line}")
    except Exception as e:
        print(f"❌ Package list failed: {e}")
    
    # Manual install attempt
    print(f"\n🚀 ATTEMPTING MANUAL INSTALL:")
    try:
        print("Installing Flask...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'flask'], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("✅ Flask installation successful")
            # Try to import
            import flask
            print(f"✅ Flask import successful: {flask.__version__}")
        else:
            print(f"❌ Flask installation failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Manual Flask install failed: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 DIAGNOSTIC COMPLETE")

if __name__ == "__main__":
    main()