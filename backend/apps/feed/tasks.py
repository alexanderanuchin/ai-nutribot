from __future__ import annotations

import logging

from celery import shared_task

from nutribot.middleware import get_request_id

from .ingestion import ingest_sources

logger = logging.getLogger("feed.ingestion")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def ingest_feed_sources_task(self):
    rid = get_request_id()
    logger.info("starting feed ingestion task", extra={"rid": rid})
    result = ingest_sources(rid=rid)
    logger.info("feed ingestion task finished", extra={"rid": rid, **result})
    return result