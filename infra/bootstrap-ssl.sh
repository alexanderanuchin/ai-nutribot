#!/usr/bin/env bash
set -euo pipefail

EMAIL="${LETSENCRYPT_EMAIL:-florabox58@gmail.com}"   # можно переопределить через LETSENCRYPT_EMAIL в env
DOMAIN="${LETSENCRYPT_DOMAIN:-caloiq.ru}"

cd "$(dirname "$0")/.."

echo "[SSL] Проверяю, что gateway поднят и ACME-локация доступна..."
docker compose ps gateway
docker compose exec -T gateway nginx -t

echo "[SSL] Выпускаю сертификат для ${DOMAIN} (webroot, HTTP-01)..."
docker compose run --rm certbot certbot certonly --webroot \
  -w /var/www/certbot \
  -d "${DOMAIN}" \
  --email "${EMAIL}" --agree-tos --no-eff-email --rsa-key-size 4096

echo "[SSL] Проверяю наличие цепочки/ключа..."
docker compose exec -T gateway ls -la /etc/letsencrypt/live/${DOMAIN}

echo "[SSL] Запускаю фоновые контейнеры автообновления и HUP..."
docker compose up -d certbot nginx-reloader

echo "[SSL] Этап 1 завершён. Файлы: /etc/letsencrypt/live/${DOMAIN}/(fullchain.pem|privkey.pem)"
