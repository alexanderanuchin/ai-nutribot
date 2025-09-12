from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user","telegram_id","city","sex","height_cm","weight_kg","activity_level","goal","updated_at")
    list_filter = ("sex","activity_level","goal","city")
    search_fields = ("user__username","user__email","telegram_id","city")
