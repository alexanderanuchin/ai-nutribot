#!/bin/sh
set -euo

COMMAND=${1:-cron}
shift || true

case "$COMMAND" in
  issue)
    exec /opt/timeweb/certbot-issue.sh "$@"
    ;;
  renew)
    exec /opt/timeweb/certbot-renew.sh "$@"
    ;;
  cron)
    exec /opt/timeweb/renew-cron.sh "$@"
    ;;
  *)
    exec "$COMMAND" "$@"
    ;;
esac
