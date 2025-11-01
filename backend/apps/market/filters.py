from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from django.db import models
from django.db.models import Q, QuerySet

from .models import Product, Recipe, Store


QueryParams = Mapping[str, Any]


def coerce_decimal(value: Any) -> Decimal | None:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return Decimal(normalized)
        except (InvalidOperation, ValueError):  # pragma: no cover - defensive
            return None
    return None


def coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return int(normalized)
        except ValueError:  # pragma: no cover - defensive
            return None
    return None


def coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return None


def apply_store_filters(queryset: QuerySet[Store], params: QueryParams) -> QuerySet[Store]:
    search = params.get("search")
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(description__icontains=search)
            | Q(city__icontains=search)
        )
    city = params.get("city")
    if city:
        queryset = queryset.filter(city__iexact=city)
    tag = params.get("tag")
    if tag:
        queryset = queryset.filter(metadata__tags__icontains=tag)
    max_eta = coerce_int(params.get("max_eta"))
    if max_eta is not None:
        queryset = queryset.filter(metadata__delivery_eta_minutes__lte=max_eta)
    free_delivery = coerce_bool(params.get("free_delivery"))
    if free_delivery is True:
        queryset = queryset.filter(
            Q(metadata__delivery_price=0)
            | Q(metadata__delivery_price__isnull=True)
        )
    is_online = coerce_bool(params.get("is_online"))
    if is_online is True:
        queryset = queryset.filter(metadata__is_online=True)
    min_rating = coerce_decimal(params.get("min_rating"))
    if min_rating is not None:
        queryset = queryset.filter(metadata__rating__gte=float(min_rating))
    return queryset


def apply_product_filters(queryset: QuerySet[Product], params: QueryParams) -> QuerySet[Product]:
    store_param = params.get("store")
    if store_param:
        if str(store_param).isdigit():
            queryset = queryset.filter(store_id=int(store_param))
        else:
            queryset = queryset.filter(store__slug=store_param)
    search = params.get("search")
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(tags__icontains=search)
            | Q(description__icontains=search)
        )
    tag = params.get("tag")
    if tag:
        queryset = queryset.filter(tags__icontains=tag)
    origin = params.get("origin")
    if origin:
        queryset = queryset.filter(metadata__origin__iexact=origin)
    discount_only = coerce_bool(params.get("discount_only"))
    if discount_only:
        queryset = queryset.filter(metadata__discount_percent__gt=0)
    available = coerce_bool(params.get("available"))
    if available:
        queryset = queryset.filter(
            inventory__quantity__gt=models.F("inventory__reserved")
        )
    min_price = coerce_decimal(params.get("min_price"))
    if min_price is not None:
        queryset = queryset.filter(price__gte=min_price)
    max_price = coerce_decimal(params.get("max_price"))
    if max_price is not None:
        queryset = queryset.filter(price__lte=max_price)
    published = params.get("published")
    if published in {"true", "1", True}:
        queryset = queryset.filter(is_published=True)
    elif published in {"false", "0", False}:
        queryset = queryset.filter(is_published=False)
    min_rating = coerce_decimal(params.get("min_rating"))
    if min_rating is not None:
        queryset = queryset.filter(metadata__rating__gte=float(min_rating))
    return queryset


def apply_recipe_filters(queryset: QuerySet[Recipe], params: QueryParams) -> QuerySet[Recipe]:
    store_param = params.get("store")
    if store_param:
        if str(store_param).isdigit():
            queryset = queryset.filter(store_id=int(store_param))
        else:
            queryset = queryset.filter(store__slug=store_param)
    search = params.get("search")
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | Q(summary__icontains=search)
        )
    max_time = coerce_int(params.get("max_time"))
    if max_time is not None:
        queryset = queryset.filter(cooking_time_minutes__lte=max_time)
    difficulty = params.get("difficulty")
    if difficulty:
        queryset = queryset.filter(difficulty__iexact=difficulty)
    tag = params.get("tag")
    if tag:
        queryset = queryset.filter(metadata__tags__icontains=tag)
    min_rating = coerce_decimal(params.get("min_rating"))
    if min_rating is not None:
        queryset = queryset.filter(metadata__rating__gte=float(min_rating))
    min_protein = coerce_decimal(params.get("min_protein"))
    if min_protein is not None:
        queryset = queryset.filter(
            metadata__nutrition__protein_g__gte=float(min_protein)
        )
    max_price = coerce_decimal(params.get("max_price"))
    if max_price is not None:
        queryset = queryset.filter(
            Q(metadata__price__value__lte=float(max_price))
            | Q(metadata__price__lte=float(max_price))
        )
    return queryset
