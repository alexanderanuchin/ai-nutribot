from __future__ import annotations

import logging
from typing import Iterable, TYPE_CHECKING

from django.apps import AppConfig
from django.db.models.signals import post_migrate

from nutribot.middleware import get_request_id

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger("feed.admin.roles")


class FeedConfig(AppConfig):
    name = "apps.feed"
    verbose_name = "Feed"

    def ready(self) -> None:  # pragma: no cover - import side effects
        from . import signals  # noqa: F401

        post_migrate.connect(self._ensure_default_groups, sender=self)

    @staticmethod
    def _ensure_default_groups(**kwargs) -> None:
        from django.contrib.auth.models import Group, Permission
        from django.contrib.contenttypes.models import ContentType

        from .models import NewsArticle

        rid = get_request_id()
        try:
            content_type = ContentType.objects.get_for_model(NewsArticle)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "cannot resolve content type for NewsArticle",
                extra={"rid": rid, "error": str(exc)},
            )
            return

        def _resolve_perms(codenames: Iterable[str]) -> list[Permission]:
            permissions = list(
                Permission.objects.filter(content_type=content_type, codename__in=list(codenames))
            )
            missing = set(codenames) - {perm.codename for perm in permissions}
            if missing:
                logger.warning(
                    "missing permissions for feed groups",
                    extra={"rid": rid, "missing": sorted(missing)},
                )
            return permissions

        editor_perms = _resolve_perms(
            [
                "view_newsarticle",
                "add_newsarticle",
                "change_newsarticle",
            ]
        )
        moderator_perms = _resolve_perms(
            [
                "view_newsarticle",
                "add_newsarticle",
                "change_newsarticle",
                "delete_newsarticle",
                "can_moderate_news",
                "can_translate_news",
            ]
        )

        editors, _ = Group.objects.get_or_create(name="Feed editors")
        moderators, _ = Group.objects.get_or_create(name="Feed moderators")

        editors.permissions.set(editor_perms)
        moderators.permissions.set(moderator_perms)

        logger.info(
            "feed groups ensured",
            extra={
                "rid": rid,
                "editors_permissions": sorted(perm.codename for perm in editor_perms),
                "moderators_permissions": sorted(perm.codename for perm in moderator_perms),
            },
        )
