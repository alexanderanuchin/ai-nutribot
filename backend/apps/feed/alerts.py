from __future__ import annotations

import logging
from typing import Sequence

import httpx
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("feed.ingestion.alerts")


def notify_ingestion_failure(*, rid: str, failed_sources: Sequence[str], error: str | None = None) -> None:
    """Send notifications when the ingestion pipeline finishes with failures."""

    sources = list(failed_sources) or ["unknown"]
    subject = "Feed ingestion failures detected"
    lines = [
        "Feed ingestion finished with errors.",
        f"RID: {rid}",
        f"Failed sources: {', '.join(sorted(sources))}",
    ]
    if error:
        lines.append(f"Error: {error}")
    body = "\n".join(lines)

    log_extra = {
        "rid": rid,
        "request_id": rid,
        "failed_sources": sources,
    }
    if error:
        log_extra["error"] = error
    logger.warning("triggering ingestion failure alert", extra=log_extra)

    recipients = getattr(settings, "FEED_INGESTION_ALERT_EMAILS", ())
    if recipients:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            list(recipients),
            fail_silently=True,
        )

    webhook = getattr(settings, "FEED_INGESTION_ALERT_WEBHOOK", "")
    if webhook:
        payload = {
            "text": subject,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Feed ingestion failures*\n```\n{body}\n```",
                    },
                }
            ],
        }
        try:
            with httpx.Client(timeout=5) as client:
                client.post(webhook, json=payload)
        except httpx.HTTPError:
            logger.exception(
                "failed to deliver ingestion failure webhook",
                extra={"rid": rid, "request_id": rid, "webhook": "feed"},
            )


__all__ = ["notify_ingestion_failure"]