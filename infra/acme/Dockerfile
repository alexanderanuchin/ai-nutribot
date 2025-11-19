FROM certbot/certbot:v2.11.0

WORKDIR /opt/timeweb

COPY entrypoint.sh certbot-issue.sh certbot-renew.sh renew-cron.sh timeweb_dns_hook.py ./

RUN chmod +x entrypoint.sh certbot-issue.sh certbot-renew.sh renew-cron.sh timeweb_dns_hook.py

ENV TIMEWEB_PROPAGATION_SECONDS=90 \
    TIMEWEB_TTL=600 \
    ACME_RENEW_INTERVAL=43200

ENTRYPOINT ["/opt/timeweb/entrypoint.sh"]
CMD ["cron"]
