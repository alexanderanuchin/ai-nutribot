# Let's Encrypt automation (Timeweb DNS-01)

This project keeps a self-hosted Let's Encrypt certificate (apex + wildcard)
ready for the CaloIQ domains even though Nginx still terminates HTTP only via
Cloudpub. Certificates are issued with the DNS-01 challenge through the
Timeweb Cloud API and stored inside the shared `letsencrypt` Docker volume so
we can switch to our own HTTPS endpoint at any time.

## Environment variables

Configure the following secrets inside `infra/.env` before issuing a
certificate:

| Variable | Required | Description |
| --- | --- | --- |
| `LETSENCRYPT_DOMAIN` | ✅ | Apex domain (e.g. `caloiq.ru`). |
| `LETSENCRYPT_EMAIL` | ✅ | Contact email for Let's Encrypt. |
| `TIMEWEB_ZONE` | ✅ | DNS zone name managed in Timeweb. |
| `TIMEWEB_ZONE_ID` | optional | Numeric zone identifier if the API requires an ID instead of the zone name. |
| `TIMEWEB_API_KEY` | ✅ | Timeweb Cloud API token (`Bearer ...`). |
| `LETSENCRYPT_EXTRA_DOMAINS` | optional | Comma/space separated SANs. |
| `TIMEWEB_PROPAGATION_SECONDS` | optional | Wait time before certbot continues (default `90`). |
| `TIMEWEB_TTL` | optional | TTL for `_acme-challenge` TXT records (default `120`). |
| `ACME_RENEW_INTERVAL` | optional | Seconds between automated renew attempts when the `acme` service runs in cron mode (default `43200`, i.e. 12h). |

> ⚠️ Never commit `TIMEWEB_API_KEY` (or the populated `.env`) to Git.

## Issuing certificates

1. Copy `infra/.env.example` to `infra/.env` and fill the variables above.
2. Build the ACME helper once:

   ```bash
   cd infra
   docker compose --profile acme build acme
   ```

3. Issue the first certificate (apex + wildcard by default):

   ```bash
   ./scripts/letsencrypt/issue.sh
   ```

   Certbot stores material in the shared `letsencrypt` volume. The TXT
   challenges are created/removed automatically through the Timeweb API.

## Renewals

- Trigger a manual renewal at any time:

  ```bash
  ./scripts/letsencrypt/renew.sh
  ```

- Keep the helper running in the background to retry `certbot renew` every
  12h (configurable via `ACME_RENEW_INTERVAL`). This mode just needs a single
  profile-aware compose up:

  ```bash
  cd infra
  docker compose --profile acme up -d acme
  ```

The `gateway` container mounts the `letsencrypt` volume read-only at
`/etc/letsencrypt`. Once we are ready to terminate TLS ourselves, point the
Nginx server block to the issued `live/<cert-name>` chain/private key.
