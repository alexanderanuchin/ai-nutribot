#!/bin/sh
set -euo

: "${LETSENCRYPT_DOMAIN:?Set LETSENCRYPT_DOMAIN in the environment}"
: "${LETSENCRYPT_EMAIL:?Set LETSENCRYPT_EMAIL in the environment}"
: "${TIMEWEB_ZONE:?Set TIMEWEB_ZONE in the environment}"
: "${TIMEWEB_API_KEY:?Set TIMEWEB_API_KEY in the environment}"

AUTH_HOOK="/opt/timeweb/timeweb_dns_hook.py auth"
CLEANUP_HOOK="/opt/timeweb/timeweb_dns_hook.py cleanup"

if [ ! -d /etc/letsencrypt/live ]; then
  echo "[acme] /etc/letsencrypt/live is empty, run 'issue' first" >&2
  exit 0
fi

set -x
certbot renew \
  --manual \
  --manual-auth-hook "$AUTH_HOOK" \
  --manual-cleanup-hook "$CLEANUP_HOOK" \
  --preferred-challenges dns \
  --manual-public-ip-logging-ok \
  --no-eff-email \
  --non-interactive
