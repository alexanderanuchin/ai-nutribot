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
exec gunicorn nutribot.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
