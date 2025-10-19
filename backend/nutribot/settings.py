import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Tuple

from corsheaders.defaults import default_headers

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_JSON = os.getenv("LOG_JSON", "0") == "1"
LOG_REQUEST_BODY = os.getenv("LOG_REQUEST_BODY", "0") == "1"
LOG_SAFE_HEADERS = os.getenv("LOG_SAFE_HEADERS", "1") == "1"
LOG_DB_LEVEL = os.getenv("LOG_DB_LEVEL", LOG_LEVEL).upper()
LOG_DB_CAPACITY = int(os.getenv("LOG_DB_CAPACITY", "5000"))

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"


def _parse_allowed_hosts(raw_value: str | None) -> list[str]:
    default_hosts = {"backend", "localhost", "127.0.0.1", "[::1]"}
    if not raw_value:
        return ["*"]
    hosts = {host.strip() for host in raw_value.split(",") if host.strip()}
    if not hosts:
        return ["*"]
    if "*" in hosts:
        return ["*"]
    return sorted(hosts | default_hosts)


ALLOWED_HOSTS = _parse_allowed_hosts(os.getenv("ALLOWED_HOSTS"))

CSRF_TRUSTED_ORIGINS = ["https://*.cloudpub.ru"]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "channels",
    "rest_framework",
    "corsheaders",
    # project apps
    "apps.auth",
    "apps.users",
    "apps.catalog",
    "apps.nutrition",
    "apps.orders",
    "apps.monitoring",
    "apps.feed",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "nutribot.middleware.RequestIDMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "nutribot.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "nutribot.wsgi.application"
ASGI_APPLICATION = "nutribot.asgi.application"

_redis_url = os.getenv("REDIS_URL", "")
if _redis_url:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [_redis_url]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

USE_SQLITE_VALUE = os.getenv("USE_SQLITE")
if USE_SQLITE_VALUE is None:
    running_pytest = any("pytest" in arg for arg in sys.argv)
    USE_SQLITE_VALUE = "1" if running_pytest else "0"

if USE_SQLITE_VALUE == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "nutribot"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
            "HOST": os.getenv("POSTGRES_HOST", "db"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = os.getenv("TIME_ZONE", "Europe/Amsterdam")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "SIGNING_KEY": os.getenv("JWT_SECRET") or SECRET_KEY,
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("JWT_ACCESS_LIFETIME_MINUTES", "15"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("JWT_REFRESH_LIFETIME_DAYS", "7"))
    ),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = (
    [o for o in os.getenv("DJANGO_CORS_ORIGINS", "").split(",") if o]
    if os.getenv("DJANGO_CORS_ORIGINS")
    else []
)
CORS_ALLOW_HEADERS = list(
    dict.fromkeys(
        list(default_headers)
        + [
            "authorization",
            "content-type",
            "x-telegram-init-data",
            "idempotency-key",
        ]
    )
)
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
BOT_INTERNAL_KEY = os.getenv("BOT_INTERNAL_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _load_telegram_bot_token() -> Tuple[str, str]:
    file_path = os.getenv("TELEGRAM_BOT_TOKEN_FILE")
    if file_path:
        try:
            token = Path(file_path).read_text(encoding="utf-8").strip()
            if token:
                return token, f"file:{file_path}"
        except OSError:
            pass

    env_value = os.getenv("TELEGRAM_BOT_TOKEN")
    if env_value:
        return env_value, "env:TELEGRAM_BOT_TOKEN"
    bot_token = os.getenv("BOT_TOKEN")

    if bot_token:
        return bot_token, "env:BOT_TOKEN"

    return "", "missing"


TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_TOKEN_SOURCE = _load_telegram_bot_token()
STARS_RECONCILE_ENABLED = os.getenv("STARS_RECONCILE_ENABLED", "0") == "1"
TELEGRAM_MT_SESSION = os.getenv("TELEGRAM_MT_SESSION", "")
TELEGRAM_MT_BOT_TOKEN = os.getenv("TELEGRAM_MT_BOT_TOKEN") or TELEGRAM_BOT_TOKEN
TELEGRAM_MT_API_ID = int(os.getenv("TELEGRAM_MT_API_ID", "0") or 0)
TELEGRAM_MT_API_HASH = os.getenv("TELEGRAM_MT_API_HASH", "")
TELEGRAM_MT_TEST_MODE = os.getenv("TELEGRAM_MT_TEST_MODE", "0") == "1"

# Email settings
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@example.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

CATALOG_MINIMUM_AVAILABLE_ITEMS = int(os.getenv("CATALOG_MINIMUM_AVAILABLE_ITEMS", "120"))


def _split_env_list(env_name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = os.getenv(env_name)
    if not raw_value:
        return default
    return tuple(filter(None, (item.strip() for item in raw_value.split(",")))) or default


LOG_ADMIN_LOGGER_NAMES = _split_env_list("LOG_ADMIN_LOGGER_NAMES", ())
LOG_ADMIN_LOGGER_PREFIXES = _split_env_list("LOG_ADMIN_LOGGER_PREFIXES", ("audit.",))
LOG_SERVICE_LOGGER_NAMES = _split_env_list("LOG_SERVICE_LOGGER_NAMES", ())
LOG_SERVICE_LOGGER_PREFIXES = _split_env_list(
    "LOG_SERVICE_LOGGER_PREFIXES",
    (
        "monitoring.poller",
        "monitoring.scheduler",
        "service.",
        "scheduler.",
    ),
)
LOG_SERVICE_LOGGER_SUBSTRINGS = _split_env_list(
    "LOG_SERVICE_LOGGER_SUBSTRINGS",
    (
        "poller",
        "scheduler",
        "heartbeat",
    ),
)

# Alerts & notifications
STARS_RECONCILE_EMAILS = _split_env_list("STARS_RECONCILE_EMAILS", ())
SLACK_STARS_ALERT_WEBHOOK = os.getenv("SLACK_STARS_ALERT_WEBHOOK", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "nutribot.middleware.RequestIDLogFilter"},
    },
    "formatters": {
        "plain": {
            "format": "%(asctime)s %(levelname)s rid=%(request_id)s build=%(build_fingerprint)s %(name)s: %(message)s",
        },
        "json": {
            "()": "nutribot.middleware.JsonLogFormatter",
        },
        "color": {
            "()": "nutribot.middleware.ColoredConsoleFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s rid=%(request_id)s build=%(build_fingerprint)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": LOG_LEVEL,
            "filters": ["request_id"],
            "formatter": "json" if LOG_JSON else "color",
        },
        "db": {
            "class": "apps.monitoring.handlers.DatabaseLogHandler",
            "level": LOG_DB_LEVEL,
            "filters": ["request_id"],
            "capacity": LOG_DB_CAPACITY,
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "db"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django": {
            "handlers": ["console", "db"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "db"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console", "db"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "audit.auth": {"handlers": ["console", "db"], "level": LOG_LEVEL, "propagate": False},
        "audit.wallet": {"handlers": ["console", "db"], "level": LOG_LEVEL, "propagate": False},
        "audit.telegram": {"handlers": ["console", "db"], "level": LOG_LEVEL, "propagate": False},
        "audit.http": {"handlers": ["console", "db"], "level": LOG_LEVEL, "propagate": False},
        "audit.crm": {"handlers": ["console", "db"], "level": LOG_LEVEL, "propagate": False},
    },
}
