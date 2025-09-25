"""Celery tasks for catalogue synchronisation."""
from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from apps.catalog.etl.usda import USDAFoodImporter

logger = logging.getLogger(__name__)


@shared_task(name="catalog.sync_usda_catalog")
def sync_usda_catalog_task(limit: int | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Trigger the USDA importer asynchronously.

    Parameters
    ----------
    limit: Optional amount of items to process.
    dry_run: When true we only fetch and transform the data without touching the DB.
    """

    importer = USDAFoodImporter()
    result = importer.run(limit=limit, dry_run=dry_run)
    logger.info("Celery USDA sync finished: %s", result)
    return result