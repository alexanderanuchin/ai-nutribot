from __future__ import annotations

from typing import Iterable

from rest_framework import permissions

from .roles import MODERATOR_GROUP_NAME, VENDOR_GROUP_NAME

ROLE_GROUPS: tuple[str, ...] = (VENDOR_GROUP_NAME, MODERATOR_GROUP_NAME)


def _user_in_groups(user, groups: Iterable[str]) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    return user.groups.filter(name__in=groups).exists()


def is_market_operator(user) -> bool:
    return _user_in_groups(user, ROLE_GROUPS)


def is_market_moderator(user) -> bool:
    return _user_in_groups(user, (MODERATOR_GROUP_NAME,))


class IsMarketOperatorOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return is_market_operator(request.user)


class IsStoreOwnerOrModerator(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if is_market_moderator(request.user):
            return True
        return getattr(obj, "owner_id", None) == getattr(request.user, "id", None)


class IsCartOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return getattr(obj, "user_id", None) == getattr(request.user, "id", None)
        return getattr(obj, "user_id", None) == getattr(request.user, "id", None)


class IsMealPlanOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user_id = getattr(request.user, "id", None)
        owner_id = getattr(obj, "user_id", None)
        if owner_id is None:
            meal_plan = getattr(obj, "meal_plan", None)
            owner_id = getattr(meal_plan, "user_id", None) if meal_plan else None
        if owner_id and owner_id == user_id:
            return True
        if request.method in permissions.SAFE_METHODS:
            if getattr(obj, "is_published", False):
                return True
            meal_plan = getattr(obj, "meal_plan", None)
            if meal_plan and getattr(meal_plan, "is_published", False):
                return True
        return False


class IsMarketOperator(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_market_operator(request.user)

