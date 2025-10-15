from django.contrib import admin
from .models import Profile, StarsRevenueSnapshot


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "telegram_id",
        "city",
        "sex",
        "height_cm",
        "weight_kg",
        "activity_level",
        "goal",
        "telegram_stars_balance",
        "telegram_stars_rate_rub",
        "calocoin_balance",
        "updated_at",
    )
    list_filter = ("sex", "activity_level", "goal", "city")
    search_fields = ("user__username", "user__email", "telegram_id", "city")


@admin.register(StarsRevenueSnapshot)
class StarsRevenueSnapshotAdmin(admin.ModelAdmin):
    list_display = ("fetched_at", "stars_total", "revenue_rub", "rate_rub", "currency")
    list_filter = ("currency",)
    ordering = ("-fetched_at",)
