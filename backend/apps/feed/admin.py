from __future__ import annotations

import json
import logging
from datetime import datetime, time, timedelta
from typing import Any

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import DateFieldListFilter
from django.db.models import QuerySet
from django.db.utils import OperationalError, ProgrammingError
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from nutribot.middleware import get_request_id

from .models import DealOffer, FeedTag, NewsArticle, Recipe, RecipePurchase, RecipeReaction, RecipeStep
from .services.ingest_pipeline import normalize_and_translate_article
from .services.translation import (
    TranslationServiceError,
    get_translation_service,
)

logger = logging.getLogger("feed.admin")
translate_logger = logging.getLogger("feed.translate.yandex")


@admin.register(FeedTag)
class FeedTagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "kind", "created_at", "updated_at")
    list_filter = ("kind", "created_at")
    search_fields = ("name", "slug")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


class RecipeStepInline(admin.TabularInline):
    model = RecipeStep
    extra = 0
    fields = ("order", "text", "media_url")
    show_change_link = True


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "status",
        "author",
        "is_premium",
        "price",
        "currency",
        "rating",
        "rating_count",
        "updated_at",
    )
    list_filter = (
        "status",
        "is_premium",
        "difficulty",
        "tags",
        "created_at",
    )
    search_fields = ("title", "short_description", "author__username", "author__email")
    ordering = ("-created_at",)
    filter_horizontal = ("tags",)
    inlines = [RecipeStepInline]
    readonly_fields = (
        "created_at",
        "updated_at",
        "rating",
        "rating_count",
        "purchases_count",
    )


@admin.register(RecipeReaction)
class RecipeReactionAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "user", "kind", "created_at")
    list_filter = ("kind", "created_at")
    search_fields = ("recipe__title", "user__username", "user__email")
    ordering = ("-created_at",)
    autocomplete_fields = ("recipe", "user")
    readonly_fields = ("created_at", "updated_at")


@admin.register(RecipePurchase)
class RecipePurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "user", "status", "amount", "currency", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("recipe__title", "user__username", "user__email")
    ordering = ("-created_at",)
    autocomplete_fields = ("recipe", "user")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DealOffer)
class DealOfferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "product_name",
        "network",
        "city",
        "price_after",
        "discount_percent",
        "valid_until",
        "is_online",
    )
    list_filter = (
        "network",
        "city",
        "is_online",
        ("valid_until", DateFieldListFilter),
        "tags",
    )
    search_fields = ("title", "product_name", "network", "city")
    ordering = ("-valid_until",)
    filter_horizontal = ("tags",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "source_name",
        "source_link",
        "published_at",
        "is_published",
        "is_flagged",
        "tonality",
        "toxicity_score",
        "clickbait_score",
        "lang",
        "translation_provider",
        "translated",
        "updated_at",
    )
    list_filter = (
        "is_published",
        "is_flagged",
        "lang",
        "translation_provider",
        "translated",
        "tonality",
        ("published_at", DateFieldListFilter),
        ("created_at", DateFieldListFilter),
        ("updated_at", DateFieldListFilter),
        "tags",
    )
    search_fields = (
        "title",
        "lead",
        "title_orig",
        "lead_orig",
        "source_name",
    )
    ordering = ("-published_at", "-id")
    date_hierarchy = "published_at"
    filter_horizontal = ("tags",)
    readonly_fields = (
        "id",
        "source_id",
        "translation_provider",
        "toxicity_score",
        "clickbait_score",
        "ingested_at",
        "ingestion_source",
        "ingestion_rid",
        "ingestion_metadata_pretty",
        "created_at",
        "updated_at",
        "preview_image_tag",
        "source_link",
    )
    fieldsets = (
        (
            "Контент",
            {
                "fields": (
                    "title",
                    "lead",
                    "body",
                    "preview_image_url",
                    "preview_image_tag",
                    "tags",
                )
            },
        ),
        (
            "Источник",
            {
                "fields": (
                    "source_name",
                    "source_url",
                    "source_link",
                )
            },
        ),
        (
            "Модерация",
            {
                "fields": (
                    "is_published",
                    "is_flagged",
                    "tonality",
                    "toxicity_score",
                    "clickbait_score",
                )
            },
        ),
        (
            "Локализация",
            {
                "fields": (
                    "lang",
                    "translated",
                    "translation_provider",
                    "title_orig",
                    "lead_orig",
                    "body_orig",
                )
            },
        ),
        (
            "Служебное",
            {
                "classes": ("collapse",),
                "fields": (
                    "id",
                    "source_id",
                    "published_at",
                    "ingested_at",
                    "ingestion_source",
                    "ingestion_rid",
                    "ingestion_metadata_pretty",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    actions = (
        "mark_as_published",
        "mark_as_unpublished",
        "mark_as_flagged",
        "mark_as_clean",
        "set_tonality_positive",
        "set_tonality_negative",
        "set_tonality_neutral",
        "translate_to_russian",
    )

    @admin.display(description="Источник", ordering="source_url")
    def source_link(self, obj: NewsArticle) -> str:
        if not obj.source_url:
            return "—"
        return format_html(
            '<a href="{url}" target="_blank" rel="noopener">Открыть источник</a>',
            url=obj.source_url,
        )

    @admin.display(description="Превью", boolean=False)
    def preview_image_tag(self, obj: NewsArticle) -> str:
        if not obj.preview_image_url:
            placeholder = (
                "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0nMTIwJyBoZWlnaHQ9JzcwJyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnPiA8cmVjdCB3aWR0aD0nMTIwJyBoZWlnaHQ9JzcwJyBmaWxsPScjZWVlJy8+IDx0ZXh0IHg9JzYwJyB5PSczNScgZG9taW5hbnQtbWFpbnRvcj0nY2VudGVyJyBmb250LXNpemU9JzEyJyBmaWxsPScjY2NjJz7QnNC40YLQtdGA8L3RleHQ+IDwvc3ZnPg=="
            )
            return format_html(
                '<img src="{}" alt="no preview" style="max-height: 80px; border: 1px solid #ddd;" />',
                placeholder,
            )
        return format_html(
            '<img src="{}" alt="preview" style="max-height: 80px; border: 1px solid #ddd;" '
            "onerror=\"this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0nMTIwJyBoZWlnaHQ9JzcwJyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnPiA8cmVjdCB3aWR0aD0nMTIwJyBoZWlnaHQ9JzcwJyBmaWxsPScjZWVlJy8+IDx0ZXh0IHg9JzYwJyB5PSczNScgZG9taW5hbnQtbWFpbnRvcj0nY2VudGVyJyBmb250LXNpemU9JzEyJyBmaWxsPScjY2NjJz7QnNC40YLQtdGA8L3RleHQ+IDwvc3ZnPg==\';\"/>",
            obj.preview_image_url,
        )

    @admin.display(description="Метаданные", ordering="ingestion_metadata")
    def ingestion_metadata_pretty(self, obj: NewsArticle) -> str:
        data = obj.ingestion_metadata or {}
        formatted = json.dumps(data, ensure_ascii=False, indent=2)
        return format_html('<pre style="max-height: 260px; overflow: auto;">{}</pre>', formatted)

    def get_readonly_fields(self, request: HttpRequest, obj: NewsArticle | None = None) -> tuple[str, ...]:
        readonly = set(super().get_readonly_fields(request, obj))
        if not request.user.has_perm("feed.can_moderate_news"):
            readonly.update({"is_published", "is_flagged", "tonality"})
        readonly.add("translated")
        return tuple(readonly)

    def get_actions(self, request: HttpRequest) -> dict[str, Any]:
        actions = super().get_actions(request)
        if not request.user.has_perm("feed.can_moderate_news"):
            for name in (
                "mark_as_published",
                "mark_as_unpublished",
                "mark_as_flagged",
                "mark_as_clean",
                "set_tonality_positive",
                "set_tonality_negative",
                "set_tonality_neutral",
            ):
                actions.pop(name, None)
        if not request.user.has_perm("feed.can_translate_news"):
            actions.pop("translate_to_russian", None)
        return actions

    def has_delete_permission(self, request: HttpRequest, obj: NewsArticle | None = None) -> bool:
        return request.user.has_perm("feed.delete_newsarticle")

    @admin.action(description="Опубликовать выбранные новости")
    def mark_as_published(self, request: HttpRequest, queryset: QuerySet[NewsArticle]) -> None:
        updated = queryset.update(is_published=True)
        messages.success(request, f"Опубликовано {updated} материалов")

    @admin.action(description="Снять с публикации выбранные новости")
    def mark_as_unpublished(self, request: HttpRequest, queryset: QuerySet[NewsArticle]) -> None:
        updated = queryset.update(is_published=False)
        messages.info(request, f"Снято с публикации: {updated}")

    @admin.action(description="Пометить как на проверке")
    def mark_as_flagged(self, request: HttpRequest, queryset: QuerySet[NewsArticle]) -> None:
        updated = queryset.update(is_flagged=True)
        messages.warning(request, f"На проверку отправлено: {updated}")

    @admin.action(description="Снять отметку проверки")
    def mark_as_clean(self, request: HttpRequest, queryset: QuerySet[NewsArticle]) -> None:
        updated = queryset.update(is_flagged=False)
        messages.success(request, f"Снята отметка проверки у {updated} материалов")

    @admin.action(description="Тональность → позитивная")
    def set_tonality_positive(self, request: HttpRequest, queryset: QuerySet[NewsArticle]) -> None:
        updated = queryset.update(tonality=NewsArticle.Tonality.POSITIVE)
        messages.success(request, f"Обновлена тональность (позитив) у {updated} материалов")

    @admin.action(description="Тональность → негативная")
    def set_tonality_negative(self, request: HttpRequest, queryset: QuerySet[NewsArticle]) -> None:
        updated = queryset.update(tonality=NewsArticle.Tonality.NEGATIVE)
        messages.warning(request, f"Обновлена тональность (негатив) у {updated} материалов")

    @admin.action(description="Сброс тональности")
    def set_tonality_neutral(self, request: HttpRequest, queryset: QuerySet[NewsArticle]) -> None:
        updated = queryset.update(tonality=NewsArticle.Tonality.NEUTRAL)
        messages.info(request, f"Сброшена тональность у {updated} материалов")

    @admin.action(description="Перевести на русский")
    def translate_to_russian(self, request: HttpRequest, queryset: QuerySet[NewsArticle]) -> None:
        if not getattr(settings, "FEED_TRANSLATE_RU_ENABLED", False):
            messages.error(request, "Перевод на русский отключен в настройках")
            return
        service = get_translation_service()
        if not service.is_available:
            messages.error(request, "Не настроен провайдер перевода")
            return
        rid = getattr(request, "request_id", get_request_id())
        processed = 0
        updated = 0
        for article in queryset.iterator():
            processed += 1
            source_title = article.title_orig or article.title
            source_lead = article.lead_orig or article.lead
            source_body = article.body_orig or article.body
            try:
                normalized = normalize_and_translate_article(
                    {
                        "title": source_title,
                        "lead": source_lead,
                        "body": source_body,
                    },
                    rid=rid,
                    translation_service=service,
                )
            except TranslationServiceError as exc:
                translate_logger.warning(
                    "manual translation failed",
                    extra={"rid": rid, "article_id": article.pk, "error": str(exc)},
                )
                continue
            if not normalized.get("translated"):
                continue
            article.title = normalized.get("title") or article.title
            article.lead = normalized.get("lead") or article.lead
            if article.body is not None or normalized.get("body") is not None:
                article.body = normalized.get("body") or article.body
            article.title_orig = normalized.get("title_orig") or source_title
            article.lead_orig = normalized.get("lead_orig") or source_lead
            article.body_orig = normalized.get("body_orig") or source_body
            article.lang = normalized.get("lang") or article.lang
            article.translated = normalized.get("translated", article.translated)
            provider_name = normalized.get("translation_provider")
            if not provider_name and service.provider is not None:
                provider_name = service.provider.name
            article.translation_provider = provider_name or article.translation_provider
            article.save(
                update_fields=[
                    "title",
                    "lead",
                    "body",
                    "title_orig",
                    "lead_orig",
                    "body_orig",
                    "lang",
                    "translated",
                    "translation_provider",
                    "updated_at",
                ]
            )
            updated += 1
        if updated:
            messages.success(request, f"Переведено {updated} из {processed} материалов")
        else:
            messages.warning(request, "Не удалось перевести выбранные материалы")


admin.site.site_header = "NutriBot Admin"
admin.site.site_title = "NutriBot Admin"
admin.site.index_title = "Панель управления контентом"


def _compute_feed_dashboard() -> dict[str, Any]:
    translation_enabled = getattr(settings, "FEED_TRANSLATE_RU_ENABLED", False)
    try:
        tz = timezone.get_default_timezone()
        today = timezone.localdate()
        today_start = timezone.make_aware(datetime.combine(today, time.min), tz)
        week_start = today_start - timedelta(days=7)
        base_qs = NewsArticle.objects.filter(is_published=True)
        today_count = base_qs.filter(published_at__gte=today_start).count()
        week_count = base_qs.filter(published_at__gte=week_start).count()
        flagged_count = base_qs.filter(is_flagged=True).count()
        translation_needed: int | None = None
        if translation_enabled:
            translation_needed = (
                base_qs.filter(translated=False).exclude(lang__iexact="ru").count()
            )
        return {
            "today": today_count,
            "week": week_count,
            "flagged": flagged_count,
            "translation_needed": translation_needed,
        }
    except (ProgrammingError, OperationalError):  # pragma: no cover - pre-migrate admin access
        return {
            "today": 0,
            "week": 0,
            "flagged": 0,
            "translation_needed": 0 if translation_enabled else None,
        }


def _build_quick_links(request: HttpRequest) -> list[dict[str, str]]:
    base = reverse("admin:feed_newsarticle_changelist")
    today = timezone.localdate()
    links = [
        {
            "label": "Сегодня",
            "url": f"{base}?published_at__gte={today.isoformat()}",
        },
        {
            "label": "На проверке",
            "url": f"{base}?is_flagged__exact=1",
        },
        {
            "label": "Черновики",
            "url": f"{base}?is_published__exact=0",
        },
    ]
    if getattr(settings, "FEED_TRANSLATE_RU_ENABLED", False):
        links.insert(
            2,
            {
                "label": "Без перевода",
                "url": f"{base}?translated__exact=0",
            },
        )
    return links


_original_each_context = admin.site.each_context


def _feed_each_context(self: admin.AdminSite, request: HttpRequest) -> dict[str, Any]:
    context = _original_each_context(request)
    context["feed_dashboard"] = {
        "metrics": _compute_feed_dashboard(),
        "links": _build_quick_links(request),
    }
    return context


admin.site.each_context = _feed_each_context.__get__(admin.site, admin.AdminSite)
admin.site.index_template = "admin/feed_index.html"