from .views import generate_menu, list_menu_plans, ping, plan_detail, update_plan_meal
from . import bot_api
from django.urls import path

urlpatterns = [
    path("generate/", generate_menu),
    path("plans/", list_menu_plans),
    path("plans/<int:plan_id>/", plan_detail),
    path("plans/<int:plan_id>/meals/<int:meal_id>/", update_plan_meal),
    path("ping/", ping),
    path("bot/upsert_profile/", bot_api.upsert_profile),
    path("bot/generate/", bot_api.generate_and_save),
]
