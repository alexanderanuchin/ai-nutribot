from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    label = "users"

    def ready(self):
        from . import signals  # noqa
        from .startup import log_bot_startup_metadata

        log_bot_startup_metadata()
