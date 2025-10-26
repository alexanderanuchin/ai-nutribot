from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from nutribot.middleware import get_request_id

from .events import publish_market_event, serialize_instance
from .models import MealPlan, Product, Recipe, Store
from .roles import VENDOR_GROUP_NAME, ensure_market_roles

User = get_user_model()


class _StateSnapshot:
    __slots__ = ("was_active", "was_verified")

    def __init__(self, was_active: bool, was_verified: bool) -> None:
        self.was_active = was_active
        self.was_verified = was_verified


def _get_group(name: str) -> Group | None:
    try:
        return Group.objects.get(name=name)
    except Group.DoesNotExist:  # pragma: no cover - defensive
        ensure_market_roles()
        try:
            return Group.objects.get(name=name)
        except Group.DoesNotExist:  # pragma: no cover
            return None


def _assign_group(user: User, name: str) -> None:
    if not user or not user.pk:
        return
    group = _get_group(name)
    if group is None:
        return
    if not user.groups.filter(pk=group.pk).exists():
        user.groups.add(group)


def _get_store_snapshot(instance: Store) -> _StateSnapshot:
    if not instance.pk:
        return _StateSnapshot(False, False)
    try:
        previous = Store.objects.get(pk=instance.pk)
    except Store.DoesNotExist:
        return _StateSnapshot(False, False)
    return _StateSnapshot(previous.is_active, previous.is_verified)


def _get_publish_snapshot(instance) -> bool:
    if not instance.pk:
        return False
    model_cls = type(instance)
    try:
        previous = model_cls.objects.get(pk=instance.pk)
    except model_cls.DoesNotExist:  # type: ignore[attr-defined]
        return False
    if hasattr(previous, "is_published"):
        return bool(previous.is_published)
    if hasattr(previous, "is_public"):
        return bool(previous.is_public)
    return False


@receiver(pre_save, sender=Store)
def store_pre_save(sender, instance: Store, **kwargs) -> None:
    instance._snapshot = _get_store_snapshot(instance)  # type: ignore[attr-defined]


@receiver(post_save, sender=Store)
def store_post_save(sender, instance: Store, created: bool, **kwargs) -> None:
    _assign_group(instance.owner, VENDOR_GROUP_NAME)

    rid = getattr(instance, "rid", get_request_id())
    payload = {
        "action": "created" if created else "updated",
        "store": serialize_instance(instance, "apps.market.serializers.StoreSerializer"),
        "meta": {
            "rid": rid,
        },
    }
    publish_market_event("stores", payload, context={"rid": rid})

    snapshot: _StateSnapshot | None = getattr(instance, "_snapshot", None)
    if snapshot is not None and not created:
        if not snapshot.was_verified and instance.is_verified:
            publish_market_event(
                "stores",
                {
                    "action": "verified",
                    "store": payload["store"],
                },
                context={"rid": rid},
            )
        if snapshot.was_active != instance.is_active:
            publish_market_event(
                "stores",
                {
                    "action": "status_changed",
                    "store": payload["store"],
                    "meta": {"previous_active": snapshot.was_active},
                },
                context={"rid": rid},
            )


@receiver(pre_save, sender=Product)
def product_pre_save(sender, instance: Product, **kwargs) -> None:
    instance._was_published = _get_publish_snapshot(instance)  # type: ignore[attr-defined]
    if instance.is_published and not instance.published_at:
        instance.published_at = timezone.now()


@receiver(post_save, sender=Product)
def product_post_save(sender, instance: Product, created: bool, **kwargs) -> None:
    product_data = serialize_instance(instance, "apps.market.serializers.ProductSerializer")
    publish_market_event(
        "products",
        {
            "action": "created" if created else "updated",
            "product": product_data,
        },
        context={"rid": getattr(instance, "rid", None)},
    )

    was_published: bool = getattr(instance, "_was_published", False)
    if not was_published and instance.is_published:
        publish_market_event(
            "products",
            {
                "action": "published",
                "product": product_data,
            },
            context={"rid": getattr(instance, "rid", None)},
        )


@receiver(pre_save, sender=Recipe)
def recipe_pre_save(sender, instance: Recipe, **kwargs) -> None:
    instance._was_published = _get_publish_snapshot(instance)  # type: ignore[attr-defined]
    if instance.is_public and not instance.published_at:
        instance.published_at = timezone.now()




@receiver(pre_save, sender=MealPlan)
def meal_plan_pre_save(sender, instance: MealPlan, **kwargs) -> None:
    instance._was_published = _get_publish_snapshot(instance)  # type: ignore[attr-defined]
    if instance.is_published and not instance.published_at:
        instance.published_at = timezone.now()


@receiver(post_save, sender=Recipe)
def recipe_post_save(sender, instance: Recipe, created: bool, **kwargs) -> None:
    recipe_data = serialize_instance(instance, "apps.market.serializers.RecipeSerializer")
    publish_market_event(
        "recipes",
        {
            "action": "created" if created else "updated",
            "recipe": recipe_data,
        },
        context={"rid": getattr(instance, "rid", None)},
    )

    was_public: bool = getattr(instance, "_was_published", False)
    if not was_public and instance.is_public:
        publish_market_event(
            "recipes",
            {
                "action": "published",
                "recipe": recipe_data,
            },
            context={"rid": getattr(instance, "rid", None)},
        )


@receiver(post_save, sender=MealPlan)
def meal_plan_post_save(sender, instance: MealPlan, created: bool, **kwargs) -> None:
    meal_plan_data = serialize_instance(instance, "apps.market.serializers.MealPlanSerializer")
    publish_market_event(
        "mealplans",
        {
            "action": "created" if created else "updated",
            "meal_plan": meal_plan_data,
        },
        context={"rid": getattr(instance, "rid", None)},
    )

    was_published: bool = getattr(instance, "_was_published", False)
    if not was_published and instance.is_published:
        publish_market_event(
            "mealplans",
            {
                "action": "published",
                "meal_plan": meal_plan_data,
            },
            context={"rid": getattr(instance, "rid", None)},
        )