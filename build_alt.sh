#!/bin/bash
set -e

echo "🔧 OPTIMIZED RENDER BUILD SCRIPT"
echo "=================================="

# Show environment
echo "🐍 Python: $(python3 --version)"
echo "📁 Working dir: $(pwd)"
echo "📦 Pip: $(pip --version)"

# Force upgrade pip first with cache cleanup
echo ""
echo "🔄 Upgrading pip..."
pip install --upgrade pip --no-cache-dir

# Clear pip cache to save space
echo "🧹 Clearing pip cache..."
pip cache purge

# Install requirements.txt with no-cache-dir flag
echo ""
echo "📦 Installing from requirements.txt (optimized)..."
pip install -r requirements.txt --no-cache-dir --no-build-isolation --prefer-binary

# Clear cache again after installation
echo "🧹 Clearing pip cache after install..."
pip cache purge

# Verify critical imports
echo ""
echo "🔍 Verifying installations..."
python3 -c "import flask; print(f'✅ Flask {flask.__version__}')" || echo "❌ Flask check failed"
python3 -c "import flask_socketio; print('✅ Flask-SocketIO')" || echo "❌ Flask-SocketIO check failed"
python3 -c "import psycopg2; print('✅ PostgreSQL')" || echo "❌ PostgreSQL check failed"

echo ""
echo "✅ Build complete!"