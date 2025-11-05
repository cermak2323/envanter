# 🚨 RENDER 502 ERROR - TROUBLESHOOTING GUIDE

## Symptoms
```
[GET]502 /count
[GET]502 /admin
[GET]502 /reports
[GET]502 /
```

All requests returning 502 Bad Gateway

---

## 🔴 Root Cause: PostgreSQL Connection Failed

When app starts on Render:
1. Flask app tries to connect to PostgreSQL
2. Connection string missing or invalid
3. App crashes before handling requests
4. Nginx returns 502 Gateway Error

---

## ✅ FIX 1: Check Render Environment Variables

**Go to Render Dashboard → Settings → Environment**

Verify these are set:
- [ ] `RENDER` = `true`
- [ ] `FLASK_ENV` = `production`
- [ ] `RENDER_DB_URL` = `postgresql://user:pass@host:5432/dbname`
- [ ] `DATABASE_URL` = `postgresql://user:pass@host:5432/dbname` (alternative)

**If missing:**
1. Get PostgreSQL connection string from Render dashboard
2. Add it to environment variables
3. Redeploy

---

## ✅ FIX 2: Check PostgreSQL Service

**On Render Dashboard:**
1. Go to Services
2. Find PostgreSQL instance
3. Verify it's "Running" (not "Suspended" or "Failed")

**If PostgreSQL is down:**
- Restart it (right-click → Restart)
- Wait 30 seconds for it to come back online
- Redeploy Flask app

---

## ✅ FIX 3: Force Redeploy

Even with correct env variables, sometimes need explicit redeploy:

```bash
# Option A: Manual redeploy
1. Go to Render dashboard
2. Find Flask service
3. Click "Redeploy"
4. Wait 2-5 minutes for deployment

# Option B: Git push (auto-deploy if enabled)
git push  # if auto-deploy is on

# Option C: Use Render CLI
render redeploy <service_id>
```

---

## ✅ FIX 4: Check Logs

**Real error message in Render logs:**

1. Render Dashboard → Logs
2. Look for error messages like:
   - "psycopg2.OperationalError: could not connect to server"
   - "ImportError: No module named..."
   - "Syntax error in..."

**Common errors:**
```
# Missing PostgreSQL env var
psycopg2.OperationalError: could not connect to server: 
  Name or service not known

# Wrong password
psycopg2.OperationalError: FATAL: password authentication failed

# Database doesn't exist
psycopg2.OperationalError: FATAL: database "xxx" does not exist
```

---

## ✅ FIX 5: Database Schema Missing

If PostgreSQL is running but tables don't exist:

```python
# Run this in Render console or locally:
from app import app, db
with app.app_context():
    db.create_all()
```

---

## 🔍 Local Test (to confirm code works)

```bash
cd EnvanterQR

# Test import
python -c "from app import app, socketio; print('✅ Imports OK')"

# Test database
python -c "import app; print('✅ Database OK')"

# Run locally
python app.py
```

If local works but Render fails → **it's an environment/database issue**

---

## 📋 Checklist

- [ ] PostgreSQL service is "Running" on Render
- [ ] `RENDER_DB_URL` environment variable is set and valid
- [ ] Connection string format: `postgresql://user:password@hostname:5432/database_name`
- [ ] No typos in connection string
- [ ] Database user has permission to connect
- [ ] Flask app imports successfully locally
- [ ] Requirements.txt has all dependencies
- [ ] Procfile points to correct startup script

---

## 🚀 If Still Failing

**Step 1: Get exact error from Render logs**
- Screenshot the error message
- Copy full error traceback

**Step 2: Test locally with same env vars**
```bash
# Export Render env vars locally
export RENDER=true
export RENDER_DB_URL="<your_connection_string>"
export FLASK_ENV=production

# Test
python app.py
```

**Step 3: Check each component**
```bash
# Test imports
python -c "from models import db; print('✅ Models')"
python -c "from app import app; print('✅ App')"
python -c "from flask_socketio import SocketIO; print('✅ SocketIO')"
```

---

## 💡 Quick Actions

**Fastest fix (usually works):**
1. Check PostgreSQL is running ✓
2. Check env vars are set ✓
3. Click "Redeploy" on Render dashboard ✓
4. Wait 5 minutes ✓

**Expected result:** Pages load, no more 502 ✅

---

## 📞 Support

If error persists:
1. Share exact error from Render logs
2. Verify database exists: `SELECT 1;` in database CLI
3. Test connection string locally
4. Check if database user has correct permissions
