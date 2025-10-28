#!/bin/bash
set -e

echo "🔧 RENDER.COM BUILD SCRIPT"
echo "================================"

# Show Python info
echo "🐍 Python: $(python3 --version)"
echo "📁 Working dir: $(pwd)"
echo "📦 Pip: $(pip --version)"

# List files to verify requirements.txt exists
echo ""
echo "📋 Files in directory:"
ls -la

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found!"
    exit 1
fi

echo ""
echo "📄 Requirements.txt content:"
cat requirements.txt

# Install with pip directly (NOT poetry)
echo ""
echo "📦 Installing requirements..."
pip install --upgrade pip

# Install requirements with verbose output
echo "🔄 Installing from requirements.txt..."
pip install -r requirements.txt --verbose

# Verify key packages are installed
echo ""
echo "🔍 Verifying installation..."
python3 -c "import flask; print(f'✅ Flask {flask.__version__}')" || echo "❌ Flask not installed"
python3 -c "import psycopg2; print('✅ psycopg2 installed')" || echo "❌ psycopg2 not installed"
python3 -c "import flask_socketio; print('✅ flask-socketio installed')" || echo "❌ flask-socketio not installed"

echo ""
echo "✅ Build complete!"
echo "Ready for deployment..."