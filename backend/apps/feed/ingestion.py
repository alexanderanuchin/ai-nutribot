from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import httpx
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from nutribot.middleware import get_request_id
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError

from .adapters import FeedAdapterError, parse_feed_response
from .alerts import notify_ingestion_failure
from .metrics import record_ingestion_metrics
from .models import NewsArticle

logger = logging.getLogger("feed.ingestion")


class FeedSourceConfig(BaseModel):
    """Runtime configuration for an external feed source."""

    name: str = Field(min_length=1)
    url: HttpUrl
    categories: list[str] = Field(default_factory=list)
    auth_key: str | None = Field(default=None, alias="authKey")
    timeout: float = Field(default=10.0, ge=0.1)
    enabled: bool = True
    params: dict[str, str] = Field(default_factory=dict)
    parser: dict[str, Any] = Field(default_factory=dict)

    @property
    def headers(self) -> dict[str, str]:
        key = self.auth_key or getattr(settings, "BOT_INTERNAL_KEY", "")
        if not key:
            return {}
        return {"X-Integration-Key": key}

    def build_query(self) -> dict[str, str]:
        params = dict(self.params)
        if self.categories:
            params.setdefault("categories", ",".join(sorted(self.categories)))
        return params

    @property
    def blueprint_name(self) -> str | None:
        blueprint = self.parser.get("blueprint") if isinstance(self.parser, dict) else None
        if isinstance(blueprint, str) and blueprint.strip():
            return blueprint.strip()
        return None


class FeedItemPayload(BaseModel):
    """Normalized payload received from feed source."""

    id: str = Field(alias="external_id")
    title: str
    summary: str = Field(alias="description")
    link: HttpUrl = Field(alias="url")
    published_at: datetime = Field(alias="publishedAt")
    source: str | None = Field(default=None, alias="sourceName")
    categories: list[str] = Field(default_factory=list)
    tonality: str | None = Field(default=None, alias="sentiment")
    preview_image_url: HttpUrl | None = Field(default=None, alias="imageUrl")
    toxicity_score: float | None = None
    clickbait_score: float | None = None

    model_config = ConfigDict(populate_by_name=True)


@dataclass(slots=True)
class IngestionResult:
    processed: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed_sources: list[str] | None = None

    def as_dict(self, *, rid: str) -> dict[str, Any]:
        return {
            "rid": rid,
            "processed": self.processed,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed_sources": self.failed_sources or [],
        }


def _load_configurations() -> list[FeedSourceConfig]:
    raw_sources: Any = getattr(settings, "FEED_INGESTION_SOURCES", [])
    if isinstance(raw_sources, str):
        try:
            raw_sources = json.loads(raw_sources)
        except json.JSONDecodeError as exc:  # pragma: no cover - config validation
            raise RuntimeError("Invalid FEED_INGESTION_SOURCES value") from exc
    if raw_sources is None:
        raw_sources = []
    if not isinstance(raw_sources, Iterable):  # pragma: no cover - defensive
        raise RuntimeError("FEED_INGESTION_SOURCES must be iterable")
    configs: list[FeedSourceConfig] = []
    for raw in raw_sources:
        try:
            config = FeedSourceConfig.model_validate(raw)
        except ValidationError as exc:
            logger.error(
                "invalid feed source configuration",
                extra={"rid": get_request_id(), "error": exc.errors(), "raw": raw},
            )
            continue
        if not config.enabled:
            logger.info(
                "feed source disabled, skipping",
                extra={"rid": get_request_id(), "source": config.name},
            )
            continue
        configs.append(config)
    return configs


def _normalise_decimal(value: float | int | None, precision: str = "0.0001") -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value)).quantize(Decimal(precision), rounding=ROUND_HALF_UP)


def _normalise_payload(payload: FeedItemPayload, *, source: FeedSourceConfig, rid: str) -> dict[str, Any]:
    published_at = payload.published_at
    if published_at.tzinfo is None:
        published_at = timezone.make_aware(published_at, timezone=dt_timezone.utc)
    else:
        published_at = published_at.astimezone(dt_timezone.utc)

    tonality = payload.tonality or NewsArticle.Tonality.NEUTRAL
    if tonality not in NewsArticle.Tonality.values:
        tonality = NewsArticle.Tonality.NEUTRAL

    source_categories = sorted({*(payload.categories or []), *source.categories})

    metadata = {
        "payload_categories": payload.categories,
        "source_categories": source.categories,
        "external_id": payload.id,
    }

    defaults = {
        "title": payload.title.strip(),
        "lead": payload.summary.strip(),
        "source_name": payload.source or source.name,
        "source_url": str(payload.link),
        "published_at": published_at,
        "preview_image_url": str(payload.preview_image_url) if payload.preview_image_url else "",
        "tonality": tonality,
        "source_categories": source_categories,
        "toxicity_score": _normalise_decimal(payload.toxicity_score),
        "clickbait_score": _normalise_decimal(payload.clickbait_score),
        "ingested_at": timezone.now(),
        "ingestion_source": source.name,
        "ingestion_rid": rid,
        "ingestion_metadata": metadata,
    }
    return defaults


def ingest_sources(*, rid: str | None = None, http_client: httpx.Client | None = None) -> dict[str, Any]:
    rid = rid or get_request_id()
    start_time = time.perf_counter()

    configs = _load_configurations()
    if not configs:
        logger.info("no feed sources configured", extra={"rid": rid})
        empty_result = IngestionResult().as_dict(rid=rid)
        record_ingestion_metrics(
            result=empty_result,
            duration_seconds=time.perf_counter() - start_time,
        )
        return empty_result

    result = IngestionResult(failed_sources=[])
    retry_attempts = int(getattr(settings, "FEED_INGESTION_RETRY_ATTEMPTS", 3))

    client = http_client
    close_client = False
    if client is None:
        client = httpx.Client(follow_redirects=True)
        close_client = True

    try:
        for config in configs:
            success = False
            for attempt in range(1, retry_attempts + 1):
                try:
                    response = client.get(
                        str(config.url),
                        headers=config.headers,
                        params=config.build_query(),
                        timeout=config.timeout,
                    )
                    response.raise_for_status()
                    payload = parse_feed_response(response, source=config, rid=rid)
                except (httpx.HTTPError, FeedAdapterError) as exc:
                    logger.warning(
                        "feed source request failed",
                        extra={
                            "rid": rid,
                            "source": config.name,
                            "attempt": attempt,
                            "error": str(exc),
                        },
                    )
                    if attempt == retry_attempts:
                        result.failed_sources.append(config.name)
                    continue
                success = True
                break
            if not success:
                continue

            items = payload.get("items") if isinstance(payload, dict) else None
            if not items:
                logger.info(
                    "feed source returned no items",
                    extra={"rid": rid, "source": config.name},
                )
                continue

            for raw_item in items:
                result.processed += 1
                try:
                    item = FeedItemPayload.model_validate(raw_item)
                except ValidationError as exc:
                    result.skipped += 1
                    logger.warning(
                        "invalid feed payload",
                        extra={
                            "rid": rid,
                            "source": config.name,
                            "errors": exc.errors(),
                            "raw": raw_item,
                        },
                    )
                    continue

                defaults = _normalise_payload(item, source=config, rid=rid)
                source_id = f"{config.name}:{item.id}"
                with transaction.atomic():
                    obj, created = NewsArticle.objects.update_or_create(
                        source_id=source_id,
                        defaults=defaults,
                    )
                if created:
                    result.created += 1
                    logger.info(
                        "news article ingested",
                        extra={
                            "rid": rid,
                            "source": config.name,
                            "article_id": obj.id,
                            "source_id": source_id,
                        },
                    )
                else:
                    result.updated += 1
                    logger.info(
                        "news article refreshed",
                        extra={
                            "rid": rid,
                            "source": config.name,
                            "article_id": obj.id,
                            "source_id": source_id,
                        },
                    )
    except Exception as exc:
        logger.exception(
            "feed ingestion execution failed",
            extra={"rid": rid, "request_id": rid},
        )
        summary = result.as_dict(rid=rid)
        duration = time.perf_counter() - start_time
        record_ingestion_metrics(result=summary, duration_seconds=duration)
        notify_ingestion_failure(
            rid=rid,
            failed_sources=summary["failed_sources"] or ["pipeline"],
            error=str(exc),
        )
        raise
    finally:
        if close_client:
            client.close()

    duration = time.perf_counter() - start_time
    summary = result.as_dict(rid=rid)
    record_ingestion_metrics(result=summary, duration_seconds=duration)

    base_extra = {
        "rid": rid,
        "request_id": rid,
        "ingestion_processed": summary["processed"],
        "ingestion_created": summary["created"],
        "ingestion_updated": summary["updated"],
        "ingestion_skipped": summary["skipped"],
    }

    if summary["failed_sources"]:
        logger.error(
            "feed ingestion finished with failed sources",
            extra={
                **base_extra,
                "ingestion_failed_sources": summary["failed_sources"],
            },
        )
        notify_ingestion_failure(rid=rid, failed_sources=summary["failed_sources"])
    else:
        logger.info(
            "feed ingestion finished without failures",
            extra={**base_extra, "ingestion_failed_sources": []},
        )

    return summary
