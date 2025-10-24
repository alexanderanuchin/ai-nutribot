from __future__ import annotations
from django.core.management.base import BaseCommand
import os
import re
from apps.feed.models import NewsArticle
from apps.feed.services.translate import translate_news_fields

_CYR = re.compile(r"[А-Яа-яЁё]")


def _needs_ru(value: str | None) -> bool:
    return bool(value) and not _CYR.search(value)


class Command(BaseCommand):
    help = "Translate missing RU titles/leads of news and normalize published_at to MSK (in serializer)."

    def handle(self, *args, **options):
        translate_enabled = os.environ.get("FEED_TRANSLATE_RU_ENABLED", "0") == "1"
        target_lang = os.environ.get("TRANSLATE_TARGET_LANG", "ru")

        queryset = NewsArticle.objects.all()
        updated = 0
        for article in queryset.iterator():
            title, lead, body = article.title, article.lead, article.body
            if any(map(_needs_ru, [title, lead])):
                new_title, new_lead, new_body = translate_news_fields(
                    title=title,
                    lead=lead,
                    content=body,
                    target_lang=target_lang,
                    enabled=translate_enabled,
                )
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