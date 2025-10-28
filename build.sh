#!/bin/bash
set -e

echo "🔧 RENDER.COM BUILD SCRIPT"
echo "================================"

# Show Python info
echo "🐍 Python: $(python3 --version)"
echo "📁 Working dir: $(pwd)"

# Install with pip directly (NOT poetry)
echo ""
echo "📦 Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Build complete!"
echo "Ready for deployment..."