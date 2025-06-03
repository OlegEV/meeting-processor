# Gunicorn configuration для Meeting Processor
import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', 8000)}"
backlog = 2048

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
workers = 1
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 300))  # 5 минут для обработки файлов
keepalive = 2

# Restart workers
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', 1000))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', 50))
preload_app = True

# Logging
loglevel = os.environ.get('LOG_LEVEL', 'info')
accesslog = '-'  # stdout
errorlog = '-'   # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'meeting_processor_web'

# Server mechanics
daemon = False
pidfile = '/tmp/gunicorn.pid'
user = None
group = None
tmp_upload_dir = None

# SSL (для HTTPS)
keyfile = os.environ.get('SSL_KEYFILE')
certfile = os.environ.get('SSL_CERTFILE')

# Worker tuning
worker_tmp_dir = '/dev/shm'  # Использовать RAM для temporary files

def when_ready(server):
    server.log.info("🚀 Meeting Processor Server готов к работе")

def worker_int(worker):
    worker.log.info("💀 Worker получил SIGINT")

def pre_fork(server, worker):
    server.log.info(f"👶 Worker {worker.pid} создается")

def post_fork(server, worker):
    server.log.info(f"✅ Worker {worker.pid} запущен")

def pre_exec(server):
    server.log.info("🔄 Перезапуск сервера")

def on_exit(server):
    server.log.info("👋 Meeting Processor Server остановлен")