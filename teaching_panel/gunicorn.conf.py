# Gunicorn configuration file (optional alternative to CLI flags)
# Logging to stdout/stderr; systemd captures output.

bind = "0.0.0.0:8000"
workers = 3
worker_class = "sync"
# Timeouts
timeout = 120
graceful_timeout = 120
# Restart workers periodically to mitigate memory leaks
max_requests = 1000
max_requests_jitter = 100
# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
capture_output = True
# Disable keepalive issues for slow clients
keepalive = 2
# Recommended for Python 3.11+ where fork safety is good
preload_app = False

# Custom hooks (can extend later)
def on_starting(server):
    server.log.info("Gunicorn starting with sync workers (stdout logging)")

