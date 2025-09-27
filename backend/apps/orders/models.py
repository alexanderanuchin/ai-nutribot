"""Domain models describing orders, subscriptions and wallet ledgers."""

from __future__ import annotations

from decimal import Decimal
import uuid

from django.conf import settings
from django.db import models
# Заказы реализуем на следующих шагах
from django.utils import timezone

from apps.catalog.models import MenuItem
from apps.nutrition.models import MenuPlan, PlanMeal
from apps.users.models import Profile


class DeliveryService(models.Model):
    """Represents an external delivery partner that fulfils meal orders."""

    slug = models.SlugField(max_length=50)
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=120)
    api_base_url = models.URLField(blank=True)
    api_key = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    supports_live_tracking = models.BooleanField(
        default=False,
        help_text="Позволяет ли партнёр отдавать ссылки на live-трекинг курьеров",
    )
    cutoff_lead_time_minutes = models.PositiveIntegerField(
        default=180,
        help_text="За сколько минут до начала слота можно принять заказ",
    )
    webhook_secret = models.CharField(
        max_length=255,
        blank=True,
        help_text="Секрет для подписи вебхуков от сервиса доставки",
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Произвольные настройки интеграции (ID ресторана, склад, тарифы)",
    )

    class Meta:
        unique_together = ("slug", "city")
        verbose_name = "Служба доставки"
        verbose_name_plural = "Службы доставки"
        indexes = [
            models.Index(fields=["city", "is_active"], name="orders_delivery_city_active"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.city})"


class DeliveryWindow(models.Model):
    """Delivery slot that can be chosen when creating an order."""

    service = models.ForeignKey(
        DeliveryService,
        on_delete=models.CASCADE,
        related_name="delivery_windows",
    )
    city = models.CharField(max_length=120)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_default = models.BooleanField(default=False)
    cutoff_lead_time_minutes = models.PositiveIntegerField(
        default=120,
        help_text="За сколько минут до начала слота требуется подтверждение",
    )

    class Meta:
        verbose_name = "Окно доставки"
        verbose_name_plural = "Окна доставки"
        unique_together = ("service", "city", "start_time", "end_time")
        ordering = ("city", "start_time")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.city}: {self.start_time:%H:%M}-{self.end_time:%H:%M}"


class SubscriptionPlan(models.Model):
    """Catalogue entity describing paid access to meal plans and deliveries."""

    class BillingPeriod(models.TextChoices):
        WEEKLY = "weekly", "Еженедельно"
        MONTHLY = "monthly", "Ежемесячно"
        QUARTERLY = "quarterly", "Ежеквартально"

    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    city = models.CharField(
        max_length=120,
        help_text="Город, для которого доступен тариф. Бот работает локально по городам.",
    )
    billing_period = models.CharField(
        max_length=20,
        choices=BillingPeriod.choices,
        default=BillingPeriod.WEEKLY,
    )
    price_rub = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Полная стоимость тарифа в рублях для отчётности",
    )
    price_telegram_stars = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Стоимость в Telegram Stars для автосписаний",
    )
    price_calocoin = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Стоимость в CaloCoin для внутреннего кошелька",
    )
    delivery_service = models.ForeignKey(
        DeliveryService,
        on_delete=models.PROTECT,
        related_name="subscription_plans",
    )
    default_delivery_window = models.ForeignKey(
        DeliveryWindow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_subscription_plans",
    )
    meals_per_week = models.PositiveSmallIntegerField(default=7)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Дополнительные параметры (минимальный заказ, доп. услуги)",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Подписочный тариф"
        verbose_name_plural = "Подписочные тарифы"
        indexes = [
            models.Index(fields=["city", "is_active"], name="orders_sub_city_active"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.billing_period})"


class MealSubscription(models.Model):
    """User subscription that generates menu plans and delivery orders."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        ACTIVE = "active", "Активна"
        PAUSED = "paused", "Пауза"
        CANCELLED = "cancelled", "Отменена"
        EXPIRED = "expired", "Истекла"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    autopay_enabled = models.BooleanField(
        default=True,
        help_text="Если включено — автосписание из кошелька/Stars",
    )
    preferred_delivery_window = models.ForeignKey(
        DeliveryWindow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )
    current_menu_plan = models.ForeignKey(
        MenuPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
        help_text="Какой план питания сейчас используется для генерации заказов",
    )
    current_period_start = models.DateField(null=True, blank=True)
    current_period_end = models.DateField(null=True, blank=True)
    next_billing_at = models.DateTimeField(null=True, blank=True)
    external_id = models.CharField(
        max_length=128,
        blank=True,
        help_text="ID подписки во внешней биллинговой системе",
    )
    city = models.CharField(max_length=120)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Подписка питания"
        verbose_name_plural = "Подписки питания"
        indexes = [
            models.Index(fields=["status", "city"], name="orders_sub_status_city"),
            models.Index(fields=["next_billing_at"], name="orders_sub_billing_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Subscription<{self.user_id}:{self.plan.slug}>"


class Order(models.Model):
    """Customer order created either ad-hoc or from a subscription."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PENDING_PAYMENT = "pending_payment", "Ожидает оплату"
        PAYMENT_FAILED = "payment_failed", "Ошибка оплаты"
        PAID = "paid", "Оплачен"
        CONFIRMED = "confirmed", "Подтверждён"
        PREPARING = "preparing", "Готовится"
        OUT_FOR_DELIVERY = "out_for_delivery", "Доставляется"
        DELIVERED = "delivered", "Доставлен"
        CANCELLED = "cancelled", "Отменён"

    class Kind(models.TextChoices):
        PRO_SUBSCRIPTION = "pro_subscription", "PRO подписка"
        CONSULTATION = "consultation", "Консультация"
        DIGITAL_PRODUCT = "digital_product", "Цифровой продукт"
        OTHER = "other", "Другое"

    class Currency(models.TextChoices):
        RUB = "RUB", "Рубли"
        TELEGRAM_STARS = "STARS", "Telegram Stars"
        CALOCOIN = "CALO", "CaloCoin"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    kind = models.CharField(
        max_length=32,
        choices=Kind.choices,
        default=Kind.PRO_SUBSCRIPTION,
    )
    subscription = models.ForeignKey(
        MealSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    menu_plan = models.ForeignKey(
        MenuPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    delivery_service = models.ForeignKey(
        DeliveryService,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
    )
    delivery_window = models.ForeignKey(
        DeliveryWindow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    delivery_date = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=120, blank=True)
    address_line = models.CharField(max_length=255, blank=True)
    apartment = models.CharField(max_length=32, blank=True)
    entrance = models.CharField(max_length=32, blank=True)
    intercom_code = models.CharField(max_length=32, blank=True)
    courier_instructions = models.TextField(blank=True)
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Итоговая стоимость заказа в валюте расчёта",
    )
    currency = models.CharField(
        max_length=8,
        choices=Currency.choices,
        default=Currency.RUB,
    )
    wallet_currency = models.CharField(
        max_length=8,
        choices=Currency.choices,
        null=True,
        blank=True,
        help_text="Чем фактически оплачен заказ (Stars/CaloCoin)",
    )
    items_count = models.PositiveIntegerField(default=0)
    payment_due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=255, blank=True)
    external_order_id = models.CharField(
        max_length=128,
        blank=True,
        help_text="ID заказа в системе доставки",
    )
    tracking_url = models.URLField(blank=True)
    reference = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    payment_transaction = models.OneToOneField(
        "orders.WalletTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_order",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        indexes = [
            models.Index(fields=["status", "delivery_date"], name="orders_order_status_date"),
            models.Index(fields=["external_order_id"], name="orders_order_external_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Order<{self.id}:{self.status}>"

    @property
    def amount(self) -> Decimal:
        return self.total_price

    @property
    def is_paid(self) -> bool:
        return self.status == self.Status.PAID or self.payment_transaction_id is not None

    def mark_paid(self, *, wallet_currency: str | None = None) -> None:
        """Utility to move the order into paid/confirmed state."""
        self.status = self.Status.PAID
        self.wallet_currency = wallet_currency or self.wallet_currency
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "wallet_currency", "paid_at", "updated_at"])


class OrderItem(models.Model):
    """Line item of an order referencing generated plan meals."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    plan_meal = models.ForeignKey(
        PlanMeal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Снимок нутриентов, веса и доп. пожеланий клиента",
    )

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
        indexes = [
            models.Index(fields=["order", "menu_item"], name="orders_orderitem_menu_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"OrderItem<{self.order_id}:{self.menu_item_id}>"


class PaymentAttempt(models.Model):
    """Represents an attempt to capture funds for an order or subscription."""

    class Provider(models.TextChoices):
        TELEGRAM_STARS = "telegram_stars", "Telegram Stars"
        CALOCOIN = "calocoin", "CaloCoin"
        CARD = "card", "Банковская карта"
        CASH = "cash", "Наличные"

    class Status(models.TextChoices):
        INITIATED = "initiated", "Создан"
        PENDING = "pending", "Ожидание подтверждения"
        SUCCEEDED = "succeeded", "Успешно"
        FAILED = "failed", "Ошибка"
        CANCELLED = "cancelled", "Отменён"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="payment_attempts",
    )
    subscription = models.ForeignKey(
        MealSubscription,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="payment_attempts",
    )
    provider = models.CharField(max_length=32, choices=Provider.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.INITIATED)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(
        max_length=8,
        choices=Order.Currency.choices,
        default=Order.Currency.RUB,
    )
    wallet_transaction = models.OneToOneField(
        "orders.WalletTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_attempt",
    )
    external_payment_id = models.CharField(max_length=128, blank=True)
    confirmation_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Снимок запроса, который отправили внешнему провайдеру",
    )
    failure_code = models.CharField(max_length=64, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    webhook_payload = models.JSONField(default=dict, blank=True)
    initiated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Попытка оплаты"
        verbose_name_plural = "Попытки оплаты"
        indexes = [
            models.Index(fields=["provider", "status"], name="orders_payment_provider_status"),
            models.Index(fields=["external_payment_id"], name="orders_payment_external_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        target = self.order_id or self.subscription_id
        return f"PaymentAttempt<{self.provider}:{target}>"


class WalletTransaction(models.Model):
    """Ledger entry for wallet balance changes (Telegram Stars / CaloCoin)."""

    class Currency(models.TextChoices):
        TELEGRAM_STARS = "STARS", "Telegram Stars"
        CALOCOIN = "CALO", "CaloCoin"

    class Direction(models.TextChoices):
        DEBIT = "debit", "Списание"
        CREDIT = "credit", "Пополнение"
        HOLD = "hold", "Блокировка средств"
        RELEASE = "release", "Разблокировка"

    class Status(models.TextChoices):
        PENDING = "pending", "В обработке"
        CONFIRMED = "confirmed", "Подтверждена"
        RELEASED = "released", "Разблокирована"
        FAILED = "failed", "Ошибка"

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="wallet_transactions")
    currency = models.CharField(max_length=8, choices=Currency.choices)
    direction = models.CharField(max_length=16, choices=Direction.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    related_order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wallet_transactions",
    )
    idempotency_key = models.CharField(
        max_length=128,
        default=uuid.uuid4,
        help_text="Используется для защиты от двойного списания",
    )
    description = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Транзакция кошелька"
        verbose_name_plural = "Транзакции кошелька"
        unique_together = ("profile", "idempotency_key")
        indexes = [
            models.Index(fields=["currency", "occurred_at"], name="orders_wallet_currency_date"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"WalletTransaction<{self.profile_id}:{self.direction}:{self.amount}>"

    @property
    def signed_amount(self) -> Decimal:
        """
        Удобный «подписанный» размер операции:
          +amount для CREDIT,
          -amount для DEBIT,
           0      для HOLD/RELEASE.
        """
        if self.direction == self.Direction.CREDIT:
            return self.amount
        if self.direction == self.Direction.DEBIT:
            return -self.amount
        return Decimal("0")


class IntegrationWebhookEvent(models.Model):
    """Stores incoming webhook notifications from payment or delivery services."""

    class Source(models.TextChoices):
        DELIVERY = "delivery", "Сервис доставки"
        PAYMENT = "payment", "Платёжный провайдер"

    class ProcessingStatus(models.TextChoices):
        RECEIVED = "received", "Получен"
        PROCESSED = "processed", "Обработан"
        FAILED = "failed", "Ошибка обработки"

    source = models.CharField(max_length=16, choices=Source.choices)
    external_event_id = models.CharField(max_length=128, blank=True)
    event_type = models.CharField(max_length=64)
    payload = models.JSONField()
    related_order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="webhook_events",
    )
    related_payment = models.ForeignKey(
        PaymentAttempt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="webhook_events",
    )
    status = models.CharField(
        max_length=16,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.RECEIVED,
    )
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_details = models.TextField(blank=True)

    class Meta:
        verbose_name = "Webhook событие"
        verbose_name_plural = "Webhook события"
        indexes = [
            models.Index(fields=["source", "status"], name="orders_webhook_source_status"),
            models.Index(fields=["external_event_id"], name="orders_webhook_external_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Webhook<{self.source}:{self.event_type}>"


# === ДОБАВЛЕНО: цели и «перки» кошелька ===============================

class WalletTarget(models.Model):
    """
    Цель накопления по конкретной валюте (например, накопить 1000 CALO).
    Использует те же коды валют, что и WalletTransaction.Currency (STARS/CALO).
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="wallet_targets",
    )
    currency = models.CharField(max_length=16, choices=WalletTransaction.Currency.choices)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    priority = models.PositiveSmallIntegerField(default=0)
    label = models.CharField(max_length=255, blank=True)
    progress_template = models.CharField(
        max_length=255,
        blank=True,
        help_text="Сообщение при неполном прогрессе. Плейсхолдеры {left}, {target}, {balance}.",
    )
    completed_template = models.CharField(
        max_length=255,
        blank=True,
        help_text="Сообщение при достижении цели. Плейсхолдеры {left}, {target}, {balance}.",
    )
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("priority", "currency", "id")
        indexes = [
            models.Index(fields=("profile", "currency", "is_active")),
        ]
        unique_together = ("profile", "currency", "priority")
        verbose_name = "Цель кошелька"
        verbose_name_plural = "Цели кошелька"

    def __str__(self) -> str:  # pragma: no cover
        return f"WalletTarget<{self.pk}:{self.currency}:{self.target_amount}>"


class WalletPerk(models.Model):
    """
    «Перки»/бенефиты в ЛК: карточки с заголовком, описанием и CTA.
    Не влияет на биллинг, чисто UI/маркетинг, но хранится рядом с кошельком.
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="wallet_perks",
    )
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    cta_label = models.CharField(max_length=128, blank=True)
    cta_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("priority", "id")
        indexes = [
            models.Index(fields=("profile", "is_active")),
        ]
        verbose_name = "Перк кошелька"
        verbose_name_plural = "Перки кошелька"

    def __str__(self) -> str:  # pragma: no cover
        return f"WalletPerk<{self.pk}:{self.title}>"

    @property
    def display_text(self) -> str:
        if self.description:
            return f"{self.title} — {self.description}"
        return self.title
