#!/usr/bin/env python3
"""
Render.com Launcher - Simple & Clean
Sadece Flask app'ı başlat, bitmesi kadar çalış
"""

import os
import sys

# Ortam ayarla
os.environ['RENDER'] = 'true'
os.environ['FLASK_ENV'] = 'production'

print("=" * 60)
print("🚀 RENDER APP LAUNCHER")
print("=" * 60)
print()

# Import app
print("📦 Importing Flask app...")
try:
    from app import app, socketio
    print("✅ App imported successfully")
except Exception as e:
    print(f"❌ IMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Get port
port = int(os.environ.get('PORT', 10000))
print(f"📍 Port: {port}")
print(f"🌐 Host: 0.0.0.0")
print()

# Start app
print("🔄 Starting app...")
print("=" * 60)

try:
    # Run with socketio
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
        log_output=True
    )
except KeyboardInterrupt:
    print("\n⏹️  App stopped")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
