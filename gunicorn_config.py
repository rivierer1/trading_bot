# Gunicorn configuration file
import multiprocessing

# Server socket
bind = "unix:/tmp/gunicorn.sock"  # Unix socket for Nginx
# Alternatively, use TCP:
# bind = "127.0.0.1:8000"

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'eventlet'  # Use eventlet for WebSocket support
threads = 2
timeout = 120

# Logging
accesslog = '/var/log/gunicorn/access.log'
errorlog = '/var/log/gunicorn/error.log'
loglevel = 'info'

# Process naming
proc_name = 'trading_bot'

# SSL (if not using Nginx)
# keyfile = 'path/to/keyfile'
# certfile = 'path/to/certfile'

# Security
worker_tmp_dir = '/dev/shm'
