#!/bin/sh
set -euo

INTERVAL=${ACME_RENEW_INTERVAL:-43200}

if ! echo "$INTERVAL" | grep -Eq '^[0-9]+$'; then
  echo "[acme] ACME_RENEW_INTERVAL must be provided in seconds" >&2
  exit 1
fi

while true; do
  /opt/timeweb/certbot-renew.sh || true
  sleep "$INTERVAL" &
  wait $!
done
