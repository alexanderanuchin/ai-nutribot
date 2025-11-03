# Marketplace realtime events contract

## Endpoint

- **Method**: `GET`
- **Path**: `/api/v1/market/events/`
- **Transport**: Server-Sent Events (`text/event-stream`)
- **Authentication**: JWT access token passed as a `token` query parameter or `Authorization: Bearer` header.
- **Permissions**: Requests without a token receive `403 Forbidden` with the standard DRF payload.

### Query parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `token` | string | yes | JWT access token minted by SimpleJWT. |
| `resource` | `recipes \| products \| stores` | no | When provided, limits the stream to the matching `market.<resource>` group. |

### Response headers

The proxy keeps long-lived HTTP connections open and sets the SSE-specific headers:

- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no`

## Event payloads

Events are proxied from the feed broker. The SSE `event` field always starts with `market.` (or `market.keepalive` for ping messages). Payloads contain both incremental counters and serialized entities. Typical envelopes:

- `market.products`

  ```jsonc
  {
    "action": "published",
    "generated_at": "2025-11-03T10:05:00Z",
    "product": {
      "id": 4815,
      "title": "Органический тофу",
      "price": 279,
      "currency": "RUB",
      "store_name": "Vegan Lab",
      "store_slug": "vegan-lab",
      "inventory_available": 42,
      "tags": ["vegan", "protein"],
      "metadata": { "rid": "9c3e..." }
    },
    "meta": {
      "rid": "9c3e..."
    }
  }
  ```

- `market.recipes`

  ```jsonc
  {
    "action": "created",
    "recipe": {
      "id": 17,
      "title": "Шакшука с нутом",
      "calories": 540,
      "store_name": "Brunch Lab"
    },
    "highlight_ids": [17]
  }
  ```

- `market.stores`

  ```jsonc
  {
    "action": "verified",
    "store": {
      "id": 9,
      "name": "Северное сияние",
      "city": "Мурманск",
      "is_verified": true
    }
  }
  ```

Legacy aggregations may still send `fresh_count` counters; the hook normalises them alongside structured payloads.

The hook listens for both the named event (`market.recipes`, etc.) and the default `message` channel so downstream consumers receive updates even if upstream publishers omit the `event` field.

Keep-alive frames are remapped from `feed.keepalive` to `market.keepalive` so existing listeners continue to emit debug logs without extra branching.

## Client integration notes

- The frontend hook keeps the `EventSource` alive with exponential backoff (1s → 30s) and reconnects automatically.
- All listeners are disposed on unmount to prevent orphaned sockets.
- When `enabled` is `false` or no token is available the hook becomes a noop.

## Sanity load test

A lightweight stress loop performed 10 sequential handshakes against the local Django stack (`USE_SQLITE=1`). Results:

- Samples (ms): `27.75, 9.04, 12.41, 9.45, 7.96, 7.76, 7.81, 7.61, 9.50, 7.42`
- Average handshake: **10.67 ms**
- P95 handshake: **34.65 ms**

See the captured run for raw output.【8cf94e†L1-L13】
