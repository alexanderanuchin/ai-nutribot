from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import ApplicationLog


@admin.register(ApplicationLog)
class ApplicationLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "level",
        "group",
        "logger_name",
        "message_preview",
        "request_id",
    )
    list_filter = ("level", "group")
    search_fields = ("message", "logger_name", "request_id")
    ordering = ("-created_at",)
    change_list_template = "admin/monitoring/applicationlog/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "console/",
                self.admin_site.admin_view(self.console_view),
                name="monitoring_applicationlog_console",
            ),
            path(
                "stream/",
                self.admin_site.admin_view(self.stream_view),
                name="monitoring_applicationlog_stream",
            ),
            path(
                "clear/",
                self.admin_site.admin_view(self.clear_history_view),
                name="monitoring_applicationlog_clear",
            ),
        ]
        return custom_urls + urls

    def console_view(self, request: HttpRequest):
        context = {
            **self.admin_site.each_context(request),
            "title": _("Онлайн-консоль логов"),
            "opts": self.model._meta,
            "levels": ApplicationLog.Level,
            "groups": ApplicationLog.Group,
            "stream_url": reverse("admin:monitoring_applicationlog_stream"),
            "clear_history_url": reverse("admin:monitoring_applicationlog_clear"),
        }
        return TemplateResponse(
            request,
            "admin/monitoring/applicationlog/console.html",
            context,
        )

    def stream_view(self, request: HttpRequest) -> JsonResponse:
        after = request.GET.get("after")
        limit_param = request.GET.get("limit")
        level = request.GET.get("level")
        logger_name = request.GET.get("logger")
        request_id = request.GET.get("rid")
        group = request.GET.get("group")

        queryset = self.get_queryset(request)
        if level:
            queryset = queryset.filter(level=level.upper())
        if logger_name:
            queryset = queryset.filter(logger_name__icontains=logger_name)
        if request_id:
            queryset = queryset.filter(request_id__icontains=request_id)
        if group and group in ApplicationLog.Group.values:
            queryset = queryset.filter(group=group)

        limit = 200
        if limit_param:
            try:
                limit = max(1, min(int(limit_param), 500))
            except ValueError:
                pass

        if after:
            try:
                after_id = int(after)
            except ValueError:
                after_id = None
            if after_id:
                queryset = queryset.filter(pk__gt=after_id).order_by("pk")
                entries = list(queryset[:limit])
            else:
                entries = []
        else:
            entries = list(queryset.order_by("-pk")[:limit])
            entries.reverse()

        results = [
            {
                "id": entry.pk,
                "created_at": timezone.localtime(entry.created_at).isoformat(),
                "level": entry.level,
                "group": entry.group,
                "logger_name": entry.logger_name,
                "message": entry.message,
                "request_id": entry.request_id,
                "extra": entry.extra or {},
                "exc_text": entry.exc_text,
            }
            for entry in entries
        ]
        return JsonResponse({"results": results})

    def clear_history_view(self, request: HttpRequest) -> JsonResponse:
        if request.method != "POST":
            return JsonResponse({"detail": "Method not allowed"}, status=405)
        if not self.has_delete_permission(request):
            return JsonResponse({"detail": "Forbidden"}, status=403)

        deleted_count, _ = ApplicationLog.objects.all().delete()
        return JsonResponse({"deleted": deleted_count})


__all__ = ["ApplicationLogAdmin"]
