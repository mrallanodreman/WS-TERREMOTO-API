#!/bin/sh
# Arranca el proceso según ROLE. Una sola imagen sirve para los 3 servicios
# (en Dokploy: 3 apps que comparten Dockerfile y solo cambian ROLE).
set -e

ROLE="${ROLE:-web}"

case "$ROLE" in
  web)
    exec gunicorn app.main:app -c gunicorn.conf.py
    ;;
  fast)
    # Features I/O-bound (menú, búsquedas): muchos mensajes en paralelo por core.
    exec celery -A app.core.celery_app worker \
      --pool=gevent \
      --concurrency="${FAST_CONCURRENCY:-200}" \
      --queues=fast \
      --prefetch-multiplier=1 \
      --max-tasks-per-child=500 \
      --loglevel="${LOG_LEVEL:-info}"
    ;;
  heavy)
    # Features CPU-bound: procesos reales, ~1 tarea por core reservado.
    exec celery -A app.core.celery_app worker \
      --pool=prefork \
      --concurrency="${HEAVY_CONCURRENCY:-2}" \
      --queues=heavy \
      --prefetch-multiplier=1 \
      --max-tasks-per-child=100 \
      --loglevel="${LOG_LEVEL:-info}"
    ;;
  *)
    echo "ROLE desconocido: $ROLE (usa web|fast|heavy)" >&2
    exit 1
    ;;
esac
