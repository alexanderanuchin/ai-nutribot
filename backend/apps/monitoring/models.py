from __future__ import annotations

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ApplicationLog(models.Model):
    class Level(models.TextChoices):
        DEBUG = "DEBUG", _("Отладка")
        INFO = "INFO", _("Информация")
        WARNING = "WARNING", _("Предупреждение")
        ERROR = "ERROR", _("Ошибка")
        CRITICAL = "CRITICAL", _("Критическая ошибка")

    class Group(models.TextChoices):
        APPLICATION = "application", _("Приложение")
        ADMINISTRATIVE = "administrative", _("Администрирование")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    level = models.CharField(max_length=16, choices=Level.choices)
    logger_name = models.CharField(max_length=255, db_index=True)
    message = models.TextField()
    request_id = models.CharField(max_length=128, blank=True)
    group = models.CharField(
        max_length=32,
        choices=Group.choices,
        default=Group.APPLICATION,
        db_index=True,
    )
    extra = models.JSONField(blank=True, null=True)
    exc_text = models.TextField(blank=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["-created_at", "level"]),
            models.Index(fields=["logger_name", "level"]),
        ]
        verbose_name = _("Событие лога")
        verbose_name_plural = _("События логов")

    def __str__(self) -> str:  # pragma: no cover - human readable only
        return f"[{self.level}] {self.logger_name}: {self.message[:80]}"

    @property
    def message_preview(self) -> str:
        return (self.message[:120] + "…") if len(self.message) > 120 else self.message


__all__ = ["ApplicationLog"]