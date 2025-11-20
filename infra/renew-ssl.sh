#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[SSL] certbot renew (webroot) ..."
docker compose run --rm certbot certbot renew --webroot -w /var/www/certbot --quiet

echo "[SSL] reload gateway ..."
docker compose exec -T gateway nginx -t && docker compose exec -T gateway nginx -s reload || true

echo "[SSL] done."

# Опциональный cron (резерв к фоновому certbot/nginx-reloader):
# 17 3 * * * cd /path/to/project \
#   && docker compose run --rm certbot certbot renew --webroot -w /var/www/certbot --quiet \
#   && docker compose exec -T gateway nginx -s reload
