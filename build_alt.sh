#!/bin/bash
set -e

echo "🔧 ALTERNATIVE RENDER BUILD SCRIPT"
echo "=================================="

# Show environment
echo "🐍 Python: $(python3 --version)"
echo "📁 Working dir: $(pwd)"
echo "📦 Pip: $(pip --version)"

# Force upgrade pip first
echo ""
echo "🔄 Upgrading pip..."
python3 -m pip install --upgrade pip

# Install packages one by one to avoid conflicts
echo ""
echo "📦 Installing packages individually..."

packages=(
    "flask>=3.1.0"
    "flask-socketio>=5.5.0"
    "psycopg2-binary>=2.9.0"
    "eventlet>=0.35.0"
    "python-dotenv>=1.0.0"
    "gunicorn>=21.0.0"
    "openpyxl>=3.1.0"
    "pandas>=2.2.0"
    "pillow>=10.0.0"
    "python-socketio>=5.14.0"
    "qrcode>=7.4.0"
    "b2sdk>=2.0.0"
)

for package in "${packages[@]}"; do
    echo "Installing $package..."
    pip install "$package"
done

# Verify critical imports
echo ""
echo "🔍 Verifying installations..."
python3 -c "import flask; print(f'✅ Flask {flask.__version__}')"
python3 -c "import flask_socketio; print('✅ Flask-SocketIO')"
python3 -c "import psycopg2; print('✅ PostgreSQL')"
python3 -c "import eventlet; print('✅ Eventlet')"

echo ""
echo "✅ Alternative build complete!"