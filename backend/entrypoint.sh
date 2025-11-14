#!/bin/sh
set -e

# Ensure venv binaries are preferred
export PATH="/opt/venv/bin:${PATH}"

# гарантируем пакеты миграций
for a in users catalog nutrition orders; do
  mkdir -p "apps/$a/migrations"
  [ -f "apps/$a/migrations/__init__.py" ] || touch "apps/$a/migrations/__init__.py"
done
# ВАЖНО: сначала users, потом остальные
/opt/venv/bin/python manage.py makemigrations users --noinput || true
/opt/venv/bin/python manage.py makemigrations --noinput || true
/opt/venv/bin/python manage.py migrate --noinput

if [ "${FEED_INGESTION_BOOTSTRAP:-1}" != "0" ]; then
  BOOTSTRAP_LIMIT=${FEED_INGESTION_BOOTSTRAP_LIMIT:-5}
  echo "Bootstrapping feed ingestion (limit per source: ${BOOTSTRAP_LIMIT})"
  if ! /opt/venv/bin/python manage.py ingest_feed_sources --limit-per-source="${BOOTSTRAP_LIMIT}"; then
    echo "Feed ingestion bootstrap failed; continuing without initial data" >&2
  fi
fi

WEB_WORKERS=${WEB_WORKERS:-2}
WEB_THREADS=${WEB_THREADS:-1}
WEB_MAX_REQUESTS=${WEB_MAX_REQUESTS:-1000}
WEB_MAX_REQUESTS_JITTER=${WEB_MAX_REQUESTS_JITTER:-100}
WEB_GRACEFUL_TIMEOUT=${WEB_GRACEFUL_TIMEOUT:-60}
WEB_KEEPALIVE=${WEB_KEEPALIVE:-5}

exec /opt/venv/bin/gunicorn nutribot.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 \
  --workers "${WEB_WORKERS}" \
  --threads "${WEB_THREADS}" \
  --max-requests "${WEB_MAX_REQUESTS}" \
  --max-requests-jitter "${WEB_MAX_REQUESTS_JITTER}" \
  --graceful-timeout "${WEB_GRACEFUL_TIMEOUT}" \
  --keep-alive "${WEB_KEEPALIVE}"
