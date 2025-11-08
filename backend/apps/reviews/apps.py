from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reviews"
    verbose_name = "Marketplace reviews"

    def ready(self) -> None:  # pragma: no cover - side effects
        from . import signals  # noqa: F401
