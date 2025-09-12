from django.db import models
from django.conf import settings
from apps.catalog.models import MenuItem

class MenuPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    target_calories = models.IntegerField()
    target_protein = models.IntegerField()
    target_fat = models.IntegerField()
    target_carbs = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    provider = models.CharField(max_length=32, default="hybrid")

class PlanMeal(models.Model):
    plan = models.ForeignKey(MenuPlan, on_delete=models.CASCADE, related_name="meals")
    item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    qty = models.FloatField(default=1.0)
    time_hint = models.CharField(max_length=16, default="any")
