from __future__ import annotations
import re
from django.core.management.base import BaseCommand

from apps.feed.models import NewsArticle
from django.conf import settings

from nutribot.middleware import get_request_id

from apps.feed.services.ingest_pipeline import normalize_and_translate_article
from apps.feed.services.translation import (
    TranslationServiceError,
    get_translation_service,
)

_CYR = re.compile(r"[А-Яа-яЁё]")


def _needs_ru(value: str | None) -> bool:
    return bool(value) and not _CYR.search(value)


class Command(BaseCommand):
    help = "Translate missing RU titles/leads of news and normalize published_at to MSK (in serializer)."

    def handle(self, *args, **options):
        translate_enabled = bool(getattr(settings, "FEED_TRANSLATE_RU_ENABLED", False))
        if not translate_enabled:
            self.stdout.write(
                self.style.WARNING("Translation disabled by configuration. Nothing to do."),
            )
            return

        queryset = NewsArticle.objects.all()
        updated = 0
        translation_service = get_translation_service()
        if translation_service is None or not translation_service.is_available:
            self.stderr.write(
                self.style.ERROR("Translation service is not configured. Aborting."),
            )
            return

        for article in queryset.iterator():
            title, lead, body = article.title, article.lead, article.body
            if any(map(_needs_ru, [title, lead])):
                rid = get_request_id()
                try:
                    result = normalize_and_translate_article(
                        {"title": title, "lead": lead, "body": body},
                        rid=rid,
                        translation_service=translation_service,
                    )
                except TranslationServiceError as exc:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Failed to translate article {article.id}: {exc}"
                        )
                    )
                    continue
                new_title = result.get("title")
                new_lead = result.get("lead")
                new_body = result.get("body")
                update_fields: list[str] = []
                if new_title and new_title != title:
                    article.title = new_title
                    update_fields.append("title")
                if new_lead and new_lead != lead:
                    article.lead = new_lead
                    update_fields.append("lead")
                if hasattr(article, "body") and new_body and new_body != body:
                    article.body = new_body
                    update_fields.append("body")
                if update_fields:
                    article.save(update_fields=update_fields)
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated: {updated}"))