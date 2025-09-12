from django.contrib import admin
from .models import MenuPlan, PlanMeal

class PlanMealInline(admin.TabularInline):
    model = PlanMeal
    extra = 0

@admin.register(MenuPlan)
class MenuPlanAdmin(admin.ModelAdmin):
    list_display = ("id","user","date","target_calories","provider","created_at")
    inlines = [PlanMealInline]
