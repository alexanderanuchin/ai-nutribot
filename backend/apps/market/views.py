from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import logging

from django.db import models
from django.db.models import Prefetch, Q
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Cart,
    CartItem,
    Inventory,
    MealPlan,
    MealPlanItem,
    Product,
    Recipe,
    RecipeIngredient,
    RecipeStep,
    Store,
)
from .pagination import MarketPagination
from .permissions import (
    IsCartOwner,
    IsMarketOperator,
    IsMarketOperatorOrReadOnly,
    IsMealPlanOwner,
    IsStoreOwnerOrModerator,
    is_market_moderator,
    is_market_operator,
)
from .serializers import (
    CartItemSerializer,
    CartSerializer,
    InventorySerializer,
    MealPlanItemSerializer,
    MealPlanSerializer,
    ProductSerializer,
    RecipeIngredientSerializer,
    RecipeSerializer,
    RecipeStepSerializer,
    StoreSerializer,
)
from .serializers import MarketSearchQuerySerializer, MarketSearchResponseSerializer
from .services.search import MarketSearchService
from nutribot.middleware import get_request_id


logger = logging.getLogger(__name__)


class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    pagination_class = MarketPagination

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        if self.action in {"update", "partial_update", "destroy"}:
            return [permissions.IsAuthenticated(), IsStoreOwnerOrModerator()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = Store.objects.select_related("owner")
        user = self.request.user
        if is_market_moderator(user):
            pass
        elif is_market_operator(user):
            qs = qs.filter(owner=user)
        else:
            qs = qs.filter(is_active=True)
        mine = self.request.query_params.get("mine")
        if mine and user.is_authenticated:
            qs = qs.filter(owner=user)
        city = self.request.query_params.get("city")
        if city:
            qs = qs.filter(city__iexact=city)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(metadata__tags__icontains=tag)
        max_eta = self.request.query_params.get("max_eta")
        if max_eta:
            try:
                qs = qs.filter(metadata__delivery_eta_minutes__lte=int(max_eta))
            except ValueError:
                pass
        free_delivery = self.request.query_params.get("free_delivery")
        if free_delivery in {"true", "1"}:
            qs = qs.filter(Q(metadata__delivery_price=0) | Q(metadata__delivery_price__isnull=True))
        is_online = self.request.query_params.get("is_online")
        if is_online in {"true", "1"}:
            qs = qs.filter(metadata__is_online=True)
        return qs.order_by("name")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance.owner_id != self.request.user.id and not is_market_moderator(self.request.user):
            raise PermissionDenied("Only store owner or moderator can update store")
        serializer.save()


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    pagination_class = MarketPagination
    permission_classes = [IsMarketOperatorOrReadOnly]

    def get_queryset(self):
        qs = (
            Product.objects.select_related("store", "store__owner", "inventory")
            .prefetch_related("ingredient_usages")
        )
        user = self.request.user
        if is_market_moderator(user):
            pass
        elif is_market_operator(user):
            qs = qs.filter(store__owner=user)
        else:
            qs = qs.filter(is_published=True, store__is_active=True)
        store_param = self.request.query_params.get("store")
        if store_param:
            if store_param.isdigit():
                qs = qs.filter(store_id=int(store_param))
            else:
                qs = qs.filter(store__slug=store_param)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(tags__icontains=search))
        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(tags__icontains=tag)
        origin = self.request.query_params.get("origin")
        if origin:
            qs = qs.filter(metadata__origin__iexact=origin)
        discount_only = self.request.query_params.get("discount_only")
        if discount_only in {"true", "1"}:
            qs = qs.filter(metadata__discount_percent__gt=0)
        available = self.request.query_params.get("available")
        if available in {"true", "1"}:
            qs = qs.filter(inventory__quantity__gt=models.F("inventory__reserved"))
        min_price = self.request.query_params.get("min_price")
        if min_price:
            try:
                qs = qs.filter(price__gte=Decimal(min_price))
            except InvalidOperation:
                pass
        max_price = self.request.query_params.get("max_price")
        if max_price:
            try:
                qs = qs.filter(price__lte=Decimal(max_price))
            except InvalidOperation:
                pass
        published = self.request.query_params.get("published")
        if published in {"true", "1"}:
            qs = qs.filter(is_published=True)
        elif published in {"false", "0"}:
            qs = qs.filter(is_published=False)
        return qs.order_by("title")

    def _assert_store_owner(self, store: Store) -> None:
        if is_market_moderator(self.request.user):
            return
        if store.owner_id != self.request.user.id:
            raise PermissionDenied("Недостаточно прав для управления продуктами магазина")

    def perform_create(self, serializer):
        store: Store = serializer.validated_data["store"]
        self._assert_store_owner(store)
        product = serializer.save()
        Inventory.objects.get_or_create(product=product)

    def perform_update(self, serializer):
        store: Store = serializer.instance.store
        self._assert_store_owner(store)
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_store_owner(instance.store)
        instance.delete()


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    pagination_class = MarketPagination
    permission_classes = [IsMarketOperatorOrReadOnly]

    def get_queryset(self):
        qs = Recipe.objects.select_related("store", "author").prefetch_related("steps", "ingredients")
        user = self.request.user
        if is_market_moderator(user):
            pass
        elif is_market_operator(user):
            qs = qs.filter(store__owner=user)
        else:
            qs = qs.filter(is_public=True, store__is_active=True)
        store_param = self.request.query_params.get("store")
        if store_param:
            if store_param.isdigit():
                qs = qs.filter(store_id=int(store_param))
            else:
                qs = qs.filter(store__slug=store_param)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(summary__icontains=search))
        max_time = self.request.query_params.get("max_time")
        if max_time:
            try:
                qs = qs.filter(cooking_time_minutes__lte=int(max_time))
            except ValueError:
                pass
        difficulty = self.request.query_params.get("difficulty")
        if difficulty:
            qs = qs.filter(difficulty__iexact=difficulty)
        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(metadata__tags__icontains=tag)
        return qs.order_by("title")

    def _assert_store_owner(self, store: Store) -> None:
        if is_market_moderator(self.request.user):
            return
        if store.owner_id != self.request.user.id:
            raise PermissionDenied("Недостаточно прав для управления рецептами магазина")

    def perform_create(self, serializer):
        store: Store = serializer.validated_data["store"]
        self._assert_store_owner(store)
        author = serializer.validated_data.get("author") or self.request.user
        serializer.save(author=author)

    def perform_update(self, serializer):
        store: Store = serializer.instance.store
        self._assert_store_owner(store)
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_store_owner(instance.store)
        instance.delete()


class RecipeStepViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeStepSerializer
    permission_classes = [IsMarketOperatorOrReadOnly]

    def get_queryset(self):
        qs = RecipeStep.objects.select_related("recipe", "recipe__store", "recipe__store__owner")
        user = self.request.user
        if is_market_moderator(user):
            return qs
        if is_market_operator(user):
            return qs.filter(recipe__store__owner=user)
        return qs.filter(recipe__is_public=True)

    def perform_create(self, serializer):
        recipe: Recipe = serializer.validated_data["recipe"]
        self._assert_recipe_access(recipe)
        serializer.save()

    def perform_update(self, serializer):
        self._assert_recipe_access(serializer.instance.recipe)
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_recipe_access(instance.recipe)
        instance.delete()

    def _assert_recipe_access(self, recipe: Recipe) -> None:
        if is_market_moderator(self.request.user):
            return
        if recipe.store.owner_id != self.request.user.id:
            raise PermissionDenied("Недостаточно прав для изменения шага рецепта")


class RecipeIngredientViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeIngredientSerializer
    permission_classes = [IsMarketOperatorOrReadOnly]

    def get_queryset(self):
        qs = RecipeIngredient.objects.select_related(
            "recipe",
            "recipe__store",
            "recipe__store__owner",
            "product",
        )
        user = self.request.user
        if is_market_moderator(user):
            return qs
        if is_market_operator(user):
            return qs.filter(recipe__store__owner=user)
        return qs.filter(recipe__is_public=True)

    def perform_create(self, serializer):
        recipe: Recipe = serializer.validated_data["recipe"]
        self._assert_recipe_access(recipe)
        serializer.save()

    def perform_update(self, serializer):
        self._assert_recipe_access(serializer.instance.recipe)
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_recipe_access(instance.recipe)
        instance.delete()

    def _assert_recipe_access(self, recipe: Recipe) -> None:
        if is_market_moderator(self.request.user):
            return
        if recipe.store.owner_id != self.request.user.id:
            raise PermissionDenied("Недостаточно прав для изменения ингредиента рецепта")


class InventoryViewSet(viewsets.ModelViewSet):
    serializer_class = InventorySerializer
    permission_classes = [IsMarketOperator]

    def get_queryset(self):
        qs = Inventory.objects.select_related("product", "product__store", "product__store__owner")
        user = self.request.user
        if is_market_moderator(user):
            return qs
        return qs.filter(product__store__owner=user)

    def _assert_product_access(self, product: Product) -> None:
        if is_market_moderator(self.request.user):
            return
        if product.store.owner_id != self.request.user.id:
            raise PermissionDenied("Недостаточно прав для управления остатками продукта")

    def perform_create(self, serializer):
        product: Product = serializer.validated_data["product"]
        self._assert_product_access(product)
        serializer.save()

    def perform_update(self, serializer):
        self._assert_product_access(serializer.instance.product)
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_product_access(instance.product)
        instance.delete()


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsCartOwner]
    pagination_class = MarketPagination

    def get_queryset(self):
        return (
            Cart.objects.filter(user=self.request.user)
            .select_related("store")
            .prefetch_related("items", "items__product")
            .order_by("-updated_at")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsCartOwner]

    def get_queryset(self):
        return (
            CartItem.objects.select_related("cart", "product", "cart__store")
            .filter(cart__user=self.request.user)
            .order_by("-added_at")
        )

    def perform_create(self, serializer):
        cart: Cart = serializer.validated_data["cart"]
        if cart.user_id != self.request.user.id:
            raise PermissionDenied("Нельзя изменять чужую корзину")
        product: Product = serializer.validated_data["product"]
        price = serializer.validated_data.get("price_snapshot")
        if price is None:
            serializer.save(price_snapshot=product.price)
        else:
            serializer.save()

    def perform_update(self, serializer):
        if serializer.instance.cart.user_id != self.request.user.id:
            raise PermissionDenied("Нельзя изменять чужую корзину")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.cart.user_id != self.request.user.id:
            raise PermissionDenied("Нельзя изменять чужую корзину")
        instance.delete()


class MealPlanViewSet(viewsets.ModelViewSet):
    serializer_class = MealPlanSerializer
    permission_classes = [IsMealPlanOwner]
    pagination_class = MarketPagination

    def get_queryset(self):
        qs = MealPlan.objects.filter(user=self.request.user).prefetch_related(
            Prefetch("items", queryset=MealPlanItem.objects.select_related("recipe", "product"))
        )
        date_from = self.request.query_params.get("from")
        if date_from:
            try:
                parsed = date.fromisoformat(date_from)
            except ValueError:
                parsed = None
            if parsed:
                qs = qs.filter(start_date__gte=parsed)
        date_to = self.request.query_params.get("to")
        if date_to:
            try:
                parsed = date.fromisoformat(date_to)
            except ValueError:
                parsed = None
            if parsed:
                qs = qs.filter(Q(end_date__lte=parsed) | Q(end_date__isnull=True))
        published = self.request.query_params.get("published")
        if published in {"true", "1"}:
            qs = qs.filter(is_published=True)
        elif published in {"false", "0"}:
            qs = qs.filter(is_published=False)
        return qs.order_by("-start_date", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MealPlanItemViewSet(viewsets.ModelViewSet):
    serializer_class = MealPlanItemSerializer
    permission_classes = [IsMealPlanOwner]

    def get_queryset(self):
        return (
            MealPlanItem.objects.select_related("meal_plan", "recipe", "product", "meal_plan__user")
            .filter(meal_plan__user=self.request.user)
            .order_by("scheduled_for", "meal_plan_id")
        )

    def perform_create(self, serializer):
        meal_plan: MealPlan = serializer.validated_data["meal_plan"]
        if meal_plan.user_id != self.request.user.id:
            raise PermissionDenied("Нельзя изменять чужой план питания")
        serializer.save()

    def perform_update(self, serializer):
        if serializer.instance.meal_plan.user_id != self.request.user.id:
            raise PermissionDenied("Нельзя изменять чужой план питания")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.meal_plan.user_id != self.request.user.id:
            raise PermissionDenied("Нельзя изменять чужой план питания")
        instance.delete()


class MarketSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *_args, **_kwargs):
        query_serializer = MarketSearchQuerySerializer(data=request.query_params, context={"request": request})
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        service = MarketSearchService(
            user=request.user,
            query=params.get("q", ""),
            resource=params.get("resource", "all"),
            limit=params.get("limit", 12),
            filters=params.get("filters") or {},
        )
        payload = service.execute()

        rid = getattr(request, "request_id", get_request_id())
        logger.info(
            "market.search.executed",
            extra={
                "rid": rid,
                "user_id": getattr(request.user, "id", None),
                "resource": params.get("resource", "all"),
                "query": params.get("q", ""),
                "filters": params.get("filters") or {},
                "total": payload.total,
                "count": len(payload.results),
            },
        )

        response_data = MarketSearchResponseSerializer(
            {
                "query": params.get("q", ""),
                "resource": params.get("resource", "all"),
                "total": payload.total,
                "results": [
                    {
                        "resource": result.resource,
                        "id": result.id,
                        "title": result.title,
                        "subtitle": result.subtitle,
                        "description": result.description,
                        "tags": result.tags,
                        "metrics": result.metrics,
                        "preview": result.preview,
                    }
                    for result in payload.results
                ],
                "facets": payload.facets,
                "suggestions": payload.suggestions,
            }
        ).data

        return Response(response_data, status=status.HTTP_200_OK)