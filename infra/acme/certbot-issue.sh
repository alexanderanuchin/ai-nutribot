#!/bin/sh
set -euo

: "${LETSENCRYPT_DOMAIN:?Set LETSENCRYPT_DOMAIN in the environment}"
: "${LETSENCRYPT_EMAIL:?Set LETSENCRYPT_EMAIL in the environment}"
: "${TIMEWEB_ZONE:?Set TIMEWEB_ZONE in the environment}"
: "${TIMEWEB_API_KEY:?Set TIMEWEB_API_KEY in the environment}"

CERT_NAME=${ACME_CERT_NAME:-$LETSENCRYPT_DOMAIN}

build_domain_flags() {
  domains=""

  if [ "${LETSENCRYPT_INCLUDE_APEX:-1}" != "0" ]; then
    domains="$domains -d ${LETSENCRYPT_DOMAIN}"
  fi

  if [ "${LETSENCRYPT_INCLUDE_WILDCARD:-1}" != "0" ]; then
    domains="$domains -d *.${LETSENCRYPT_DOMAIN}"
  fi

  if [ -n "${LETSENCRYPT_EXTRA_DOMAINS:-}" ]; then
    OLD_IFS=$IFS
    IFS=' '
    set -f
    for domain in $(printf '%s' "${LETSENCRYPT_EXTRA_DOMAINS}" | tr ',;\n' '   '); do
      trimmed=$(echo "$domain" | xargs)
      if [ -n "$trimmed" ]; then
        domains="$domains -d $trimmed"
      fi
    done
    set +f
    IFS=$OLD_IFS
  fi

  printf '%s' "$domains"
}

DOMAIN_FLAGS=$(build_domain_flags)

if [ -z "$(printf '%s' "$DOMAIN_FLAGS" | xargs)" ]; then
  echo "[acme] No domain names were configured for issuance" >&2
  exit 1
fi

AUTH_HOOK="/opt/timeweb/timeweb_dns_hook.py auth"
CLEANUP_HOOK="/opt/timeweb/timeweb_dns_hook.py cleanup"

set -x
certbot certonly \
  --manual \
  --manual-auth-hook "$AUTH_HOOK" \
  --manual-cleanup-hook "$CLEANUP_HOOK" \
  --preferred-challenges dns \
  --manual-public-ip-logging-ok \
  --agree-tos \
  --no-eff-email \
  --non-interactive \
  --email "$LETSENCRYPT_EMAIL" \
  --cert-name "$CERT_NAME" \
  $DOMAIN_FLAGS
