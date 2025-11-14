import logging
import os
from typing import Dict, List

import pytest


AUDIT_LOGGERS = ("audit", "audit.plan", "audit.wallet", "audit.telegram")


@pytest.fixture(autouse=True)
def allow_async_unsafe():
    """Permit sync ORM operations inside async tests and silence audit handlers."""

    previous = os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE")
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

    saved_handlers: Dict[str, List[logging.Handler]] = {}
    saved_propagate: Dict[str, bool] = {}
    for name in AUDIT_LOGGERS:
        logger = logging.getLogger(name)
        saved_handlers[name] = list(logger.handlers)
        saved_propagate[name] = logger.propagate
        logger.handlers = []
        logger.propagate = False

    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("DJANGO_ALLOW_ASYNC_UNSAFE", None)
        else:
            os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = previous

        for name, handlers in saved_handlers.items():
            logger = logging.getLogger(name)
            logger.handlers = handlers
            logger.propagate = saved_propagate.get(name, logger.propagate)
