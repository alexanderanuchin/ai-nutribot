# apps/orders/admin.py
from django.contrib import admin
from .models import (
    DeliveryService, DeliveryWindow,
    SubscriptionPlan, MealSubscription,
    Order, OrderItem,
    PaymentAttempt, WalletTransaction,
    IntegrationWebhookEvent,
)

@admin.register(DeliveryService)
class DeliveryServiceAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "city", "is_active")
    list_filter = ("city", "is_active")
    search_fields = ("slug", "name", "city")

@admin.register(DeliveryWindow)
class DeliveryWindowAdmin(admin.ModelAdmin):
    list_display = ("service", "city", "start_time", "end_time", "is_default")
    list_filter = ("city", "service", "is_default")

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "delivery_date", "city",
                    "total_price", "currency", "wallet_currency")
    list_filter = ("status", "city", "currency", "wallet_currency", "delivery_date")
    search_fields = ("id", "user__username", "external_order_id")
    inlines = [OrderItemInline]
    readonly_fields = ("created_at", "updated_at", "paid_at", "cancelled_at")

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "city", "billing_period", "is_active",
                    "price_rub", "price_telegram_stars", "price_calocoin")
    list_filter = ("city", "billing_period", "is_active")
    search_fields = ("slug", "name")

@admin.register(MealSubscription)
class MealSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "plan", "status", "city",
                    "autopay_enabled", "next_billing_at")
    list_filter = ("status", "city", "autopay_enabled")
    search_fields = ("user__username", "plan__slug")
    readonly_fields = ("created_at", "updated_at")

@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "status", "amount", "currency",
                    "order", "subscription", "external_payment_id", "initiated_at")
    list_filter = ("provider", "status", "currency", "initiated_at")
    search_fields = ("external_payment_id", "order__id", "subscription__id")

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "profile", "currency", "direction", "status",
                    "amount", "occurred_at", "idempotency_key", "related_order")
    list_filter = ("currency", "direction", "status", "occurred_at")
    search_fields = ("idempotency_key", "profile__user__username", "related_order__id")

@admin.register(IntegrationWebhookEvent)
class IntegrationWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "event_type", "status",
                    "external_event_id", "received_at", "processed_at")
    list_filter = ("source", "status", "received_at")
    search_fields = ("external_event_id", "event_type")
