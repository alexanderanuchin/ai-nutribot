from __future__ import annotations

from datetime import date
import logging

from django.db.models import F, Prefetch, Q
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import (
    apply_product_filters,
    apply_recipe_filters,
    apply_store_filters,
)
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
from .ordering import (
    MarketOrderingFilter,
    coalesce_json_float,
    json_float,
    json_int,
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
    filter_backends = [MarketOrderingFilter]
    ordering_fields = ("name", "rating", "eta", "freshness", "created_at", "id")
    ordering_aliases = {
        "rating": json_float("metadata__rating"),
        "eta": json_int("metadata__delivery_eta_minutes"),
        "freshness": F("created_at"),
    }
    ordering = ("name", "id")

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
        qs = apply_store_filters(qs, self.request.query_params)
        return qs

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
    filter_backends = [MarketOrderingFilter]
    ordering_fields = ("title", "price", "discount", "rating", "created", "created_at", "id")
    ordering_aliases = {
        "discount": json_float("metadata__discount_percent"),
        "rating": json_float("metadata__rating"),
        "created": F("created_at"),
    }
    ordering = ("title", "id")

    def get_queryset(self):
        qs = Product.objects.select_related("store", "store__owner", "inventory")
        user = self.request.user
        if is_market_moderator(user):
            pass
        elif is_market_operator(user):
            qs = qs.filter(store__owner=user)
        else:
            qs = qs.filter(is_published=True, store__is_active=True)
        qs = apply_product_filters(qs, self.request.query_params)
        return qs

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
    filter_backends = [MarketOrderingFilter]
    ordering_fields = (
        "title",
        "time_minutes",
        "calories",
        "rating",
        "price",
        "created",
        "created_at",
        "id",
    )
    ordering_aliases = {
        "time_minutes": F("cooking_time_minutes"),
        "calories": json_float("metadata__nutrition__calories"),
        "rating": json_float("metadata__rating"),
        "price": coalesce_json_float(["metadata__price__value", "metadata__price"]),
        "created": F("created_at"),
    }
    ordering = ("title", "id")

    def get_queryset(self):
        ingredients_prefetch = Prefetch(
            "ingredients",
            queryset=RecipeIngredient.objects.select_related("product"),
        )
        qs = Recipe.objects.select_related("store", "store__owner", "author").prefetch_related(
            "steps",
            ingredients_prefetch,
        )
        user = self.request.user
        if is_market_moderator(user):
            pass
        elif is_market_operator(user):
            qs = qs.filter(store__owner=user)
        else:
            qs = qs.filter(is_public=True, store__is_active=True)
        qs = apply_recipe_filters(qs, self.request.query_params)
        return qs

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
        items_prefetch = Prefetch(
            "items",
            queryset=CartItem.objects.select_related("product"),
        )
        return (
            Cart.objects.filter(user=self.request.user)
            .select_related("store")
            .prefetch_related(items_prefetch)
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