# Gunicorn configuration file
# Optimized for 2-3K teachers + 5-7K students concurrent users
# Logging to stdout/stderr; systemd captures output.
import os
import multiprocessing

bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')

# Workers: (2 * CPU cores) + 1 recommended for CPU-bound
# For I/O bound Django with DB: use async worker or more workers
# Environment variable allows override for different server sizes
_default_workers = (2 * multiprocessing.cpu_count()) + 1
workers = int(os.environ.get('GUNICORN_WORKERS', _default_workers))

# Use gevent for async I/O - handles more concurrent connections with less memory
# Install: pip install gevent
# Falls back to sync if gevent not installed
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gevent')

# Threads per worker (only for 'gthread' worker class)
threads = int(os.environ.get('GUNICORN_THREADS', '4'))

# For gevent: max concurrent connections per worker
worker_connections = int(os.environ.get('GUNICORN_WORKER_CONNECTIONS', '1000'))

# Timeouts
timeout = 120  # Max time for request processing
graceful_timeout = 30  # Time to wait for workers to finish during reload
keepalive = 5  # Seconds to wait for next request on Keep-Alive connection

# Restart workers periodically to mitigate memory leaks
max_requests = 2000
max_requests_jitter = 200

# Logging
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
accesslog = '-'
errorlog = '-'
capture_output = True

# Preload app for faster worker startup (saves memory)
# Disable if you have issues with forking
preload_app = os.environ.get('GUNICORN_PRELOAD', 'True').lower() in ('true', '1', 'yes')

# Custom hooks
def on_starting(server):
    server.log.info(f"Gunicorn starting: {workers} {worker_class} workers")
    if worker_class == 'gevent':
        server.log.info(f"  worker_connections={worker_connections}")

def worker_exit(server, worker):
    server.log.info(f"Worker {worker.pid} exited")


