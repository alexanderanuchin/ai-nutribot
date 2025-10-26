from __future__ import annotations

import logging
from typing import Iterable

from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.db import ProgrammingError, transaction
from django.db.utils import OperationalError
from nutribot.middleware import get_request_id

logger = logging.getLogger("market.roles")

VENDOR_GROUP_NAME = "market_vendor"
MODERATOR_GROUP_NAME = "market_moderator"


def _get_market_permissions() -> Iterable[Permission]:
    app_config = apps.get_app_config("market")
    model_names = [model._meta.model_name for model in app_config.get_models()]
    if not model_names:
        return []
    return Permission.objects.filter(
        content_type__app_label=app_config.label,
        content_type__model__in=model_names,
    )


def ensure_market_roles() -> None:
    try:
        permissions = list(_get_market_permissions())
    except (LookupError, OperationalError, ProgrammingError):  # pragma: no cover - migrations in progress
        return

    if not permissions:
        return

    vendor_permissions = [
        perm
        for perm in permissions
        if perm.codename.startswith("add_")
        or perm.codename.startswith("change_")
        or perm.codename.startswith("delete_")
        or perm.codename.startswith("view_")
        or "manage" in perm.codename
    ]
    moderator_permissions = list(permissions)

    with transaction.atomic():
        vendor_group, _ = Group.objects.get_or_create(name=VENDOR_GROUP_NAME)
        vendor_group.permissions.set(vendor_permissions)
        moderator_group, _ = Group.objects.get_or_create(name=MODERATOR_GROUP_NAME)
        moderator_group.permissions.set(moderator_permissions)

    rid = get_request_id()
    logger.debug(
        "Ensured market roles",
        extra={"rid": rid, "vendor_perms": len(vendor_permissions), "moderator_perms": len(moderator_permissions)},
    )