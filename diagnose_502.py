#!/usr/bin/env python3
"""
Render 502 Error Diagnostic Tool
Checks what's causing the crash
"""

import os
import sys

print("=" * 60)
print("🔍 RENDER 502 ERROR DIAGNOSTIC")
print("=" * 60)

# Check 1: Environment variables
print("\n✅ CHECKING ENVIRONMENT VARIABLES...")
print("-" * 60)

env_vars = ['RENDER', 'FLASK_ENV', 'RENDER_DB_URL', 'DATABASE_URL', 'PORT']
for var in env_vars:
    value = os.environ.get(var, 'NOT SET')
    if value != 'NOT SET':
        # Mask sensitive data
        if 'password' in value.lower() or 'url' in value.lower():
            value = value[:20] + '***' if len(value) > 20 else '***'
    print(f"  {var:20} = {value}")

# Check 2: Python imports
print("\n✅ CHECKING PYTHON IMPORTS...")
print("-" * 60)

imports_to_check = [
    'flask',
    'flask_socketio',
    'psycopg2',
    'sqlalchemy',
    'dotenv',
    'werkzeug',
]

for module in imports_to_check:
    try:
        __import__(module)
        print(f"  ✅ {module:20} - OK")
    except ImportError as e:
        print(f"  ❌ {module:20} - MISSING: {e}")

# Check 3: Try importing app
print("\n✅ CHECKING APP IMPORTS...")
print("-" * 60)

try:
    from app import app, socketio
    print("  ✅ app import      - OK")
    print("  ✅ socketio import - OK")
except Exception as e:
    print(f"  ❌ App import FAILED:")
    print(f"     {type(e).__name__}: {e}")
    sys.exit(1)

# Check 4: Database connection
print("\n✅ CHECKING DATABASE CONNECTION...")
print("-" * 60)

try:
    with app.app_context():
        from flask_sqlalchemy import SQLAlchemy
        # Try a simple query
        from models import db
        result = db.session.execute('SELECT 1')
        print("  ✅ Database connection - OK")
except Exception as e:
    print(f"  ❌ Database connection FAILED:")
    print(f"     {type(e).__name__}: {e}")
    print(f"\n     🔍 Possible causes:")
    if 'could not connect' in str(e):
        print(f"        - PostgreSQL service not running")
        print(f"        - Wrong hostname/port")
        print(f"        - Network unreachable")
    elif 'password authentication' in str(e):
        print(f"        - Wrong password in connection string")
    elif 'does not exist' in str(e):
        print(f"        - Database doesn't exist")
        print(f"        - Wrong database name")
    else:
        print(f"        - {str(e)}")

# Check 5: Routes available
print("\n✅ CHECKING ROUTES...")
print("-" * 60)

try:
    routes = [
        ('/', 'GET'),
        ('/count', 'GET'),
        ('/admin', 'GET'),
        ('/reports', 'GET'),
        ('/api/dashboard_stats', 'GET'),
    ]
    
    route_list = []
    for rule in app.url_map.iter_rules():
        route_list.append(str(rule))
    
    found = 0
    for path, method in routes:
        route_str = f"{method} {path}"
        if any(path in r for r in route_list):
            print(f"  ✅ {route_str:30} - Found")
            found += 1
        else:
            print(f"  ⚠️  {route_str:30} - Not found")
    
    print(f"\n  Total routes registered: {len(route_list)}")
    
except Exception as e:
    print(f"  ❌ Error checking routes: {e}")

# Check 6: Port
print("\n✅ CHECKING PORT CONFIGURATION...")
print("-" * 60)

port = os.environ.get('PORT', 5001)
try:
    port_int = int(port)
    print(f"  ✅ PORT = {port_int} - OK")
except Exception as e:
    print(f"  ❌ PORT invalid: {port} - {e}")

# Final summary
print("\n" + "=" * 60)
print("📊 DIAGNOSTIC SUMMARY")
print("=" * 60)

print("""
If you see errors above:

1. ❌ Missing environment variables
   → Add them to Render dashboard

2. ❌ Missing Python packages  
   → Check requirements.txt is correct
   → Run: pip install -r requirements.txt

3. ❌ Database connection failed
   → Check PostgreSQL is running
   → Verify connection string
   → Check credentials

4. ❌ App import failed
   → Check for syntax errors
   → Check all imports available

If all checks pass (all ✅):
→ Redeploy on Render
→ Wait 5 minutes for cold start
→ Check again
""")

print("=" * 60)
print("✅ DIAGNOSTIC COMPLETE")
print("=" * 60)
