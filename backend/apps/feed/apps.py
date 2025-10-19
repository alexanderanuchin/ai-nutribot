from django.apps import AppConfig


class FeedConfig(AppConfig):
    name = "apps.feed"
    verbose_name = "Feed"

    def ready(self) -> None:  # pragma: no cover - import side effects
        from . import signals  # noqa: F401