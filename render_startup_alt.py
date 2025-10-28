#!/usr/bin/env python3
"""
Render.com Startup - With Runtime Dependency Check
"""
import os
import sys
import subprocess
import shutil

# Environment
os.environ.setdefault('RENDER', 'true')
os.environ.setdefault('FLASK_ENV', 'production')

# Create directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Verify Flask is available. If not, create a venv, install requirements into it, and re-exec under that venv.
try:
    import flask  # noqa: F401
except ImportError:
    print("⚠️ Flask not found in current interpreter:")
    print("  sys.executable:", sys.executable)
    print("  sys.prefix:", sys.prefix)

    venv_dir = os.path.join(os.getcwd(), '.venv')
    python_in_venv = None

    # Create venv if it doesn't exist
    if not os.path.isdir(venv_dir):
        print(f"Creating virtual environment at {venv_dir}...")
        subprocess.run([sys.executable, '-m', 'venv', venv_dir], check=True)

    # Determine the python executable inside the venv
    if os.name == 'nt':
        python_in_venv = os.path.join(venv_dir, 'Scripts', 'python.exe')
        pip_cmd = [python_in_venv, '-m', 'pip']
    else:
        python_in_venv = os.path.join(venv_dir, 'bin', 'python')
        pip_cmd = [python_in_venv, '-m', 'pip']

    if not os.path.isfile(python_in_venv):
        raise RuntimeError(f"Python executable not found in venv at {python_in_venv}")

    print(f"Installing requirements into venv using: {python_in_venv}")
    # Upgrade pip first for better wheel support
    subprocess.run(pip_cmd + ['install', '--upgrade', 'pip', '-q'], check=True)
    # Install requirements
    subprocess.run(pip_cmd + ['install', '-r', 'requirements.txt'], check=True)

    # Show a short list of installed packages for diagnostics
    try:
        out = subprocess.check_output(pip_cmd + ['freeze'], text=True)
        print('== Installed packages in venv (top 30 lines) ==')
        for i, line in enumerate(out.splitlines()):
            if i >= 30:
                print('...')
                break
            print(line)
    except Exception:
        pass

    # Re-exec this script under the venv python so imports use the venv site-packages
    print('Re-executing under venv python...')
    os.execv(python_in_venv, [python_in_venv] + sys.argv)

# Now import app
from app import app, socketio

port = int(os.environ.get('PORT', 10000))

print(f"🚀 Starting app on 0.0.0.0:{port}")

# Run with SocketIO (production-ready)
socketio.run(
    app,
    host='0.0.0.0',
    port=port,
    debug=False,
    use_reloader=False,
    allow_unsafe_werkzeug=True
)



