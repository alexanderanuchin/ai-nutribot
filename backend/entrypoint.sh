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

exec /opt/venv/bin/gunicorn nutribot.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
