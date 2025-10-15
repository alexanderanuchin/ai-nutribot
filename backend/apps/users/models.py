from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


def _list_default():
    return []


def _avatar_preferences_default():
    return {"kind": "initials"}


def _wallet_settings_default():
    return {"show_wallet": False}


class Profile(models.Model):
    class Sex(models.TextChoices):
        MALE = "m", "Male"
        FEMALE = "f", "Female"
        OTHER = "o", "Other"

    class Activity(models.TextChoices):
        SEDENTARY = "sedentary", "Sedentary"
        LIGHT = "light", "Light"
        MODERATE = "moderate", "Moderate"
        ACTIVE = "active", "Active"
        ATHLETE = "athlete", "Athlete"

    class Goal(models.TextChoices):
        LOSE = "lose", "Lose fat"
        MAINTAIN = "maintain", "Maintain"
        GAIN = "gain", "Gain"
        RECOMP = "recomp", "Recomp"

    class ExperienceLevel(models.TextChoices):
        NEWBIE = "newbie", "Новичок"
        ENTHUSIAST = "enthusiast", "Энтузиаст"
        PRO = "pro", "Профи"
        LEGEND = "legend", "Легенда"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")

    # переносим сюда «юзерские» поля
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    city = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=150, blank=True)
    experience_level = models.CharField(
        max_length=32,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.NEWBIE,
    )

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

    telegram_stars_balance = models.PositiveIntegerField(
        default=0,
        help_text="[deprecated] Используйте леджер TelegramStarLedgerEntry для актуального баланса",
    )
    stars_purchase_blocked = models.BooleanField(
        default=False,
        help_text="Если True — Telegram запрещает покупки Stars для этого пользователя",
    )
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

    avatar_preferences = models.JSONField(default=_avatar_preferences_default, blank=True)
    wallet_settings = models.JSONField(default=_wallet_settings_default, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile<{self.user_id}>"


class TelegramStarLedgerEntry(models.Model):
    class Direction(models.TextChoices):
        CREDIT = "credit", "Зачисление"
        DEBIT = "debit", "Списание"

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="star_ledger_entries",
    )
    wallet_transaction = models.OneToOneField(
        "orders.WalletTransaction",
        on_delete=models.CASCADE,
        related_name="star_ledger_entry",
    )
    direction = models.CharField(max_length=16, choices=Direction.choices)
    amount = models.PositiveIntegerField()
    occurred_at = models.DateTimeField(default=timezone.now)
    description = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=64, blank=True)
    telegram_payment_charge_id = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text="Идентификатор successful_payment из Telegram",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Запись леджера Stars"
        verbose_name_plural = "Леджер Stars"
        constraints = [
            models.UniqueConstraint(
                fields=["telegram_payment_charge_id"],
                condition=models.Q(telegram_payment_charge_id__isnull=False),
                name="users_starledger_unique_charge",
            )
        ]
        indexes = [
            models.Index(fields=["profile", "direction"], name="users_starledger_prof_dir"),
            models.Index(fields=["occurred_at"], name="users_starledger_occur"),
        ]

    def __str__(self):  # pragma: no cover
        return f"StarLedger<{self.profile_id}:{self.direction}:{self.amount}>"


class StarsRevenueSnapshot(models.Model):
    """Stores aggregated revenue metrics returned by payments.getStarsRevenueStats."""

    fetched_at = models.DateTimeField(default=timezone.now, db_index=True)
    stars_total = models.PositiveIntegerField(default=0)
    revenue_rub = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="RUB")
    rate_rub = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal("0.0000"))
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Снимок метрик Stars"
        verbose_name_plural = "Метрики Stars"
        ordering = ("-fetched_at", "-id")

    def __str__(self) -> str:  # pragma: no cover
        return f"StarsMetrics<{self.fetched_at:%Y-%m-%d %H:%M}>"
