from django.apps import AppConfig


class MarketConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.market"

    def ready(self) -> None:  # pragma: no cover - import side effects
        from django.db.models.signals import post_migrate

        from . import signals  # noqa: F401
        from .roles import ensure_market_roles

        def _on_post_migrate(**_: object) -> None:
            ensure_market_roles()

        post_migrate.connect(_on_post_migrate, sender=self)
