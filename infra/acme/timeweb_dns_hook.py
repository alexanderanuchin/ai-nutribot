#!/usr/bin/env python3
"""Manual DNS hook for Timeweb Cloud DNS."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = os.environ.get("TIMEWEB_API_BASE", "https://api.timeweb.cloud/api/v1").rstrip("/")
TIMEWEB_ZONE = os.environ.get("TIMEWEB_ZONE", "").rstrip(".")
TIMEWEB_ZONE_ID = os.environ.get("TIMEWEB_ZONE_ID")
TIMEWEB_TOKEN = os.environ.get("TIMEWEB_API_KEY")
TTL = int(os.environ.get("TIMEWEB_TTL", "600"))
PROPAGATION_WAIT = int(os.environ.get("TIMEWEB_PROPAGATION_SECONDS", "90"))


class HookError(Exception):
    """Raised when the Timeweb hook cannot complete."""


def log(message: str) -> None:
    sys.stderr.write(f"[timeweb-dns] {message}\n")


def ensure_env(value: str | None, name: str) -> str:
    if not value:
        raise HookError(f"{name} must be set for the Timeweb DNS hook")
    return value


def build_zone_path() -> str:
    zone_ref = TIMEWEB_ZONE_ID or ensure_env(TIMEWEB_ZONE, "TIMEWEB_ZONE")
    return urllib.parse.quote(zone_ref, safe="")


def relative_label(domain: str) -> str:
    zone = ensure_env(TIMEWEB_ZONE, "TIMEWEB_ZONE")
    domain = domain.rstrip(".")
    zone = zone.rstrip(".")
    if domain == zone:
        return ""
    suffix = f".{zone}"
    if domain.endswith(suffix):
        return domain[: -len(suffix) - 1]
    raise HookError(f"Domain {domain} is outside of the configured zone {zone}")


def api_request(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {ensure_env(TIMEWEB_TOKEN, 'TIMEWEB_API_KEY')}",
        "Accept": "application/json",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        log(f"HTTP {exc.code} calling {method} {path}: {body}")
        raise HookError(f"Timeweb API request failed: {exc.code}") from exc
    except urllib.error.URLError as exc:
        log(f"Network error calling {method} {path}: {exc}")
        raise HookError("Timeweb API network error") from exc


def extract_record_id(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""
    if "id" in payload:
        return str(payload["id"])
    for key in ("record", "dns_record", "data", "result"):
        nested = payload.get(key)
        if isinstance(nested, dict) and "id" in nested:
            return str(nested["id"])
    return ""


def create_record(domain: str, validation: str) -> str:
    label_suffix = relative_label(domain)
    record_label = "_acme-challenge"
    if label_suffix:
        record_label = f"{record_label}.{label_suffix}"

    payload = {
        "type": "TXT",
        "subdomain": record_label,
        "value": validation,
        "ttl": TTL,
    }

    zone_path = build_zone_path()
    log(f"Creating TXT record {record_label} in zone {zone_path}")
    response = api_request("POST", f"/domains/{zone_path}/dns-records", payload)
    record_id = extract_record_id(response)
    if not record_id:
        raise HookError("Could not determine the created DNS record id")

    log(f"Sleeping {PROPAGATION_WAIT}s for DNS propagation")
    time.sleep(max(PROPAGATION_WAIT, 0))

    return record_id


def cleanup_record(record_id: str) -> None:
    if not record_id:
        log("No record id passed to cleanup; skipping")
        return
    zone_path = build_zone_path()
    log(f"Deleting TXT record id {record_id} from zone {zone_path}")
    api_request("DELETE", f"/domains/{zone_path}/dns-records/{record_id}")


def parse_auth_output() -> str:
    raw = os.environ.get("CERTBOT_AUTH_OUTPUT", "").strip()
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            candidate = data.get("record_id") or data.get("id")
            if candidate:
                return str(candidate)
    except json.JSONDecodeError:
        pass
    return raw


def main() -> None:
    if len(sys.argv) < 2:
        raise HookError("Specify 'auth' or 'cleanup' action")

    action = sys.argv[1]

    if action == "auth":
        domain = ensure_env(os.environ.get("CERTBOT_DOMAIN"), "CERTBOT_DOMAIN")
        validation = ensure_env(os.environ.get("CERTBOT_VALIDATION"), "CERTBOT_VALIDATION")
        record_id = create_record(domain, validation)
        output = json.dumps({"record_id": record_id})
        print(output)
    elif action == "cleanup":
        record_id = parse_auth_output()
        cleanup_record(record_id)
    else:
        raise HookError(f"Unknown action '{action}'")


def run() -> None:
    try:
        main()
    except HookError as exc:
        log(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    run()
