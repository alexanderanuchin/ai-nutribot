"""Dev fixtures for payment subsystem."""

from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.orders.models import DeliveryService, MealSubscription, SubscriptionPlan


def create():
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="demo",
        defaults={"email": "demo@example.com"},
    )
    profile = user.profile
    delivery, _ = DeliveryService.objects.get_or_create(
        slug="demo-delivery",
        defaults={"name": "Demo Delivery", "city": "Moscow"},
    )
    plan, _ = SubscriptionPlan.objects.get_or_create(
        slug="demo-plan",
        defaults={
            "name": "Demo Weekly",
            "city": "Moscow",
            "billing_period": SubscriptionPlan.BillingPeriod.WEEKLY,
            "price_calocoin": Decimal("150"),
            "delivery_service": delivery,
        },
    )
    MealSubscription.objects.get_or_create(
        user=user,
        profile=profile,
        plan=plan,
        defaults={
            "status": MealSubscription.Status.ACTIVE,
            "autopay_enabled": True,
            "city": "Moscow",
        },
    )
    print("Seeded demo user and subscription")


if __name__ == "__main__":
    create()