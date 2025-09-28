"""Celery tasks for nutrition workflows."""
from __future__ import annotations
from typing import Any, Mapping

from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model

from apps.nutrition.services.menu_plan_service import (
    MenuPlanEngineError,
    MenuPlanService,
    MenuPlanValidationError,
)

logger = get_task_logger(__name__)
User = get_user_model()
_service = MenuPlanService()


def _should_retry(exc: MenuPlanEngineError) -> bool:
    message = str(exc).lower()
    return "empty plan" in message or "engine" in message


@shared_task(bind=True, max_retries=5, retry_backoff=True, retry_backoff_max=3600, retry_jitter=True)
def generate_menu_task(self, user_id: int, params: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    """Generate a menu plan asynchronously and return its summary."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist as exc:  # pragma: no cover - defensive
        logger.error("engine_error", extra={"user_id": user_id, "error": "user_missing"})
        raise exc

    try:
        plan, summary = _service.generate_and_save(user=user, params=params, context=context)
    except MenuPlanValidationError as exc:
        logger.error("engine_error", extra={"user_id": user.id, "error": str(exc)})
        raise
    except MenuPlanEngineError as exc:
        logger.warning("engine_error", extra={"user_id": user.id, "error": str(exc)})
        if _should_retry(exc) and self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise

    return {"plan_id": plan.id, "status": plan.status, "summary": summary}