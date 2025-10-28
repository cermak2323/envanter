# Gunicorn configuration for Render.com
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
backlog = 2048

# Worker processes
workers = 1
worker_class = "eventlet"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help control memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"

# Process naming
proc_name = "envanterqr"

# Server mechanics
preload_app = True
daemon = False
pidfile = None
tmp_upload_dir = None

# SSL (if needed in future)
keyfile = None
certfile = None

# Application
wsgi_module = "app:app"