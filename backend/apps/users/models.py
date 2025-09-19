from decimal import Decimal

from django.conf import settings
from django.db import models

def _list_default():
    return []

class Profile(models.Model):
    class Sex(models.TextChoices):
        MALE = "m", "Male"
        FEMALE = "f", "Female"
        OTHER = "o", "Other"

    class Activity(models.TextChoices):
        SEDENTARY = "sedentary", "Sedentary"
        LIGHT     = "light", "Light"
        MODERATE  = "moderate", "Moderate"
        ACTIVE    = "active", "Active"
        ATHLETE   = "athlete", "Athlete"

    class Goal(models.TextChoices):
        LOSE     = "lose", "Lose fat"
        MAINTAIN = "maintain", "Maintain"
        GAIN     = "gain", "Gain"
        RECOMP   = "recomp", "Recomp"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")

    # переносим сюда «юзерские» поля
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    city = models.CharField(max_length=100, blank=True)

    sex = models.CharField(max_length=1, choices=Sex.choices, default=Sex.MALE)
    birth_date = models.DateField(null=True, blank=True)

    height_cm = models.PositiveSmallIntegerField(default=170)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, default=70.0)
    body_fat_pct = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    activity_level = models.CharField(max_length=16, choices=Activity.choices, default=Activity.MODERATE)
    goal = models.CharField(max_length=16, choices=Goal.choices, default=Goal.RECOMP)

    allergies = models.JSONField(default=_list_default, blank=True)
    exclusions = models.JSONField(default=_list_default, blank=True)

    daily_budget = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    telegram_stars_balance = models.PositiveIntegerField(default=0)
    telegram_stars_rate_rub = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Сколько рублей стоит одна Telegram Star при пополнении",
    )
    calocoin_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Баланс внутренней валюты CaloCoin",
    )
    calocoin_rate_rub = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Сколько рублей стоит один CaloCoin",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile<{self.user_id}>"
