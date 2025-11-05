#!/bin/bash

echo "🚀 EnvanterQR Alternative Startup Script"

# Find Python executable
PYTHON=""
for cmd in python3 python /usr/bin/python3 /usr/bin/python /opt/render/project/src/.venv/bin/python; do
    if command -v "$cmd" &> /dev/null; then
        PYTHON="$cmd"
        echo "✅ Found Python: $PYTHON"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ No Python executable found!"
    echo "Available executables in PATH:"
    echo $PATH | tr ':' '\n' | while read dir; do
        if [ -d "$dir" ]; then
            ls -la "$dir" | grep python || true
        fi
    done
    exit 1
fi

# Show Python version
echo "🐍 Python version: $($PYTHON --version)"

# Get port
PORT=${PORT:-10000}
echo "🌐 PORT: $PORT"

# Create directories
mkdir -p uploads reports static/temp

# Try to start with gunicorn
echo "🚀 Attempting to start with gunicorn..."
if $PYTHON -m gunicorn --version &> /dev/null; then
    echo "✅ Gunicorn found, starting application..."
    exec $PYTHON -m gunicorn --worker-class eventlet -w 1 --bind "0.0.0.0:$PORT" --timeout 120 app:app
else
    echo "❌ Gunicorn not found, starting Flask directly..."
    exec $PYTHON app.py
fi