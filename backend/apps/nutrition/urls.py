from .views import generate_menu, ping
from . import bot_api
from django.urls import path

urlpatterns = [
    path("generate/", generate_menu),
    path("ping/", ping),
    path("bot/upsert_profile/", bot_api.upsert_profile),
    path("bot/generate/", bot_api.generate_and_save),
]
