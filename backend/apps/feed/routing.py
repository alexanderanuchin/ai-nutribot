from django.urls import re_path

from .consumers import FeedConsumer

# NOTE: CloudPub проксирует WebSocket-запросы с ведущим слэшем, а Channels
# после обработки root_path оставляет его только если он присутствует в scope.
# Поэтому явно допускаем вариант как с ведущим '/', так и без него, чтобы
# исключить гонки на уровне промежуточных прокси.
websocket_urlpatterns = [
    re_path(r"^/?ws/feed/?$", FeedConsumer.as_asgi()),
]

