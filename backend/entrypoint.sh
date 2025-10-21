#!/usr/bin/env bash
set -e
# гарантируем пакеты миграций
for a in users catalog nutrition orders; do
  mkdir -p apps/$a/migrations
  [ -f apps/$a/migrations/__init__.py ] || touch apps/$a/migrations/__init__.py
done
# ВАЖНО: сначала users, потом остальные
python manage.py makemigrations users --noinput || true
python manage.py makemigrations --noinput || true
python manage.py migrate --noinput

if [ "${FEED_INGESTION_BOOTSTRAP:-1}" != "0" ]; then
  BOOTSTRAP_LIMIT=${FEED_INGESTION_BOOTSTRAP_LIMIT:-5}
  echo "Bootstrapping feed ingestion (limit per source: ${BOOTSTRAP_LIMIT})"
  if ! python manage.py ingest_feed_sources --limit-per-source="${BOOTSTRAP_LIMIT}"; then
    echo "Feed ingestion bootstrap failed; continuing without initial data" >&2
  fi
fi

exec gunicorn nutribot.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
