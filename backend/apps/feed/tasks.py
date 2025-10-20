from __future__ import annotations

import logging

from celery import shared_task

from nutribot.middleware import get_request_id

from .ingestion import ingest_sources

logger = logging.getLogger("feed.ingestion")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def ingest_feed_sources_task(self):
    rid = get_request_id()
    logger.info("starting feed ingestion task", extra={"rid": rid, "request_id": rid})
    try:
        result = ingest_sources(rid=rid)
    except Exception:
        logger.exception(
            "feed ingestion task crashed",
            extra={"rid": rid, "request_id": rid},
        )
        raise

    status = "failure" if result.get("failed_sources") else "success"
    logger.info(
        "feed ingestion task finished",
        extra={
            "rid": rid,
            "request_id": rid,
            "ingestion_status": status,
            "ingestion_failed_sources": result.get("failed_sources", []),
            "ingestion_processed": result.get("processed", 0),
            "ingestion_created": result.get("created", 0),
            "ingestion_updated": result.get("updated", 0),
            "ingestion_skipped": result.get("skipped", 0),
        },
    )
    return result