from django.urls import path

from apps.nutrition.api.nutrition import (
    AcceptPlanView,
    GenerateAndSaveView,
    HistoryView,
    JobStatusView,
    LatestPlanView,
    RejectPlanView,
    RegeneratePlanView,
)

from .views import generate_menu, list_menu_plans, ping, plan_detail, update_plan_meal
from . import bot_api

urlpatterns = [
    path("generate_and_save/", GenerateAndSaveView.as_view()),
    path("jobs/<str:job_id>/", JobStatusView.as_view()),
    path("plans/latest/", LatestPlanView.as_view()),
    path("plans/history/", HistoryView.as_view()),
    path("plans/<int:plan_id>/accept/", AcceptPlanView.as_view()),
    path("plans/<int:plan_id>/reject/", RejectPlanView.as_view()),
    path("plans/<int:plan_id>/regenerate/", RegeneratePlanView.as_view()),
    path("generate/", generate_menu),
    path("plans/", list_menu_plans),
    path("plans/<int:plan_id>/", plan_detail),
    path("plans/<int:plan_id>/meals/<int:meal_id>/", update_plan_meal),
    path("ping/", ping),
    path("bot/upsert_profile/", bot_api.upsert_profile),
    path("bot/generate/", bot_api.generate_and_save),
]
