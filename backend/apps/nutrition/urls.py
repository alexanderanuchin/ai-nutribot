from .views import generate_menu, list_menu_plans, ping, update_plan_status
from . import bot_api
from django.urls import path

urlpatterns = [
    path("generate/", generate_menu),
    path("plans/", list_menu_plans),
    path("plans/<int:plan_id>/", update_plan_status),
    path("ping/", ping),
    path("bot/upsert_profile/", bot_api.upsert_profile),
    path("bot/generate/", bot_api.generate_and_save),
]
