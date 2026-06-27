import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get('WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn_worker.UvicornWorker"

timeout = int(os.environ.get('GUNICORN_TIMEOUT', 30))
graceful_timeout = int(os.environ.get('GRACEFUL_TIMEOUT', 10))
keepalive = int(os.environ.get('KEEPALIVE', 5))

max_requests = int(os.environ.get('MAX_REQUESTS', 2000))
max_requests_jitter = int(os.environ.get('MAX_REQUESTS_JITTER', 200))

preload_app = True

accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('LOG_LEVEL', 'info')
proc_name = 'ws-terremoto-api'
