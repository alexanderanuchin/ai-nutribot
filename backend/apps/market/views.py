from __future__ import annotations

from datetime import date
import logging

from django.db.models import F, Prefetch, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
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
    MealPlanAccess,
    MealPlanItem,
    Product,
    Recipe,
    RecipeAccess,
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
    CartCheckoutSerializer,
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
from .services import (
    CartCheckoutError,
    CartEmptyError,
    CartInactiveError,
    InventoryInsufficientError,
    WalletInsufficientFunds,
    checkout_cart,
    get_meal_plan_price_stars,
    get_recipe_price_stars,
    has_meal_plan_access,
    has_recipe_access,
    purchase_meal_plan,
    purchase_recipe,
)
from .services.meal_plan_export import MealPlanExportError, export_meal_plan
from .services.search import MarketSearchService
from apps.orders.serializers import OrderSerializer
from apps.users.models import Profile
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

    # ProductViewSet relies on default retrieve behavior.


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

    def get_permissions(self):
        if getattr(self, "action", None) == "purchase":
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

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
        if getattr(user, "is_authenticated", False):
            access_prefetch = Prefetch(
                "premium_accesses",
                queryset=RecipeAccess.objects.filter(profile__user=user),
                to_attr="_prefetched_accesses",
            )
            qs = qs.prefetch_related(access_prefetch)
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

    def retrieve(self, request, *args, **kwargs):
        recipe = self.get_object()
        if not request.user.is_authenticated:
            raise PermissionDenied("Требуется аутентификация")
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if not has_recipe_access(profile, recipe):
            raise PermissionDenied("Требуется покупка рецепта")
        serializer = self.get_serializer(recipe)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="purchase")
    def purchase(self, request, pk=None):
        recipe = self.get_object()
        if not request.user.is_authenticated:
            raise PermissionDenied("Требуется аутентификация")
        profile, _ = Profile.objects.get_or_create(user=request.user)
        rid = getattr(request, "request_id", get_request_id())
        idempotency_key = request.headers.get("Idempotency-Key") or request.META.get("HTTP_IDEMPOTENCY_KEY")
        try:
            result = purchase_recipe(
                profile,
                recipe,
                rid=rid,
                idempotency_key=idempotency_key,
            )
        except WalletInsufficientFunds as exc:
            raise ValidationError({"detail": str(exc), "code": "insufficient_stars"}) from exc
        serializer = self.get_serializer(recipe)
        status_code = status.HTTP_201_CREATED if result.wallet_transaction else status.HTTP_200_OK
        response_payload = {
            "recipe": serializer.data,
            "wallet_transaction_id": getattr(result.wallet_transaction, "id", None),
            "price_stars": str(get_recipe_price_stars(recipe) or 0),
        }
        return Response(response_payload, status=status_code)


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

    @action(detail=True, methods=["post"])
    def checkout(self, request, *args, **kwargs):
        cart = self.get_object()
        serializer = CartCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile, _ = Profile.objects.get_or_create(user=request.user)
        rid = getattr(request, "request_id", get_request_id())

        try:
            result = checkout_cart(
                cart,
                profile=profile,
                pay_with_wallet=serializer.validated_data.get("pay_with_wallet", False),
                wallet_currency=serializer.validated_data.get("wallet_currency"),
                metadata=serializer.validated_data.get("metadata"),
                rid=rid,
            )
        except WalletInsufficientFunds as exc:
            raise ValidationError({"pay_with_wallet": str(exc)}) from exc
        except InventoryInsufficientError as exc:
            raise ValidationError(
                {
                    "detail": "Недостаточно остатка на складе",
                    "inventory": {
                        "product_id": exc.product_id,
                        "requested": exc.requested,
                        "available": exc.available,
                    },
                }
            ) from exc
        except (CartInactiveError, CartEmptyError) as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        except CartCheckoutError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        order_data = OrderSerializer(result.order).data
        cart_payload = CartSerializer(
            result.cart,
            context=self.get_serializer_context(),
        ).data
        response_status = status.HTTP_201_CREATED
        payload = {
            "order": order_data,
            "cart": cart_payload,
            "paid": result.was_paid,
        }
        return Response(payload, status=response_status)


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

    def get_permissions(self):
        if getattr(self, "action", None) == "purchase":
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        items_prefetch = Prefetch(
            "items",
            queryset=MealPlanItem.objects.select_related(
                "recipe",
                "recipe__store",
                "product",
                "product__store",
            ),
        )
        qs = MealPlan.objects.all().select_related("user").prefetch_related(items_prefetch)

        user = self.request.user if getattr(self.request.user, "is_authenticated", False) else None
        if user:
            access_prefetch = Prefetch(
                "premium_accesses",
                queryset=MealPlanAccess.objects.filter(profile__user=user),
                to_attr="_prefetched_accesses",
            )
            qs = qs.prefetch_related(access_prefetch)
        scope = (self.request.query_params.get("scope") or "").lower()
        action = getattr(self, "action", None)

        if action in {"retrieve", "export", "purchase"}:
            filters = Q(is_published=True)
            if user:
                filters |= Q(user=user)
            qs = qs.filter(filters)
        else:
            if scope == "public":
                qs = qs.filter(is_published=True)
            elif user:
                qs = qs.filter(user=user)
            else:
                qs = qs.none()

        if action not in {"retrieve", "export"}:
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
            if scope != "public" and user:
                published = self.request.query_params.get("published")
                if published in {"true", "1"}:
                    qs = qs.filter(is_published=True)
                elif published in {"false", "0"}:
                    qs = qs.filter(is_published=False)

        return qs.order_by("-start_date", "-id")

    def retrieve(self, request, *args, **kwargs):
        plan = self.get_object()
        if not request.user.is_authenticated:
            raise PermissionDenied("Требуется аутентификация")
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if not has_meal_plan_access(profile, plan):
            raise PermissionDenied("План доступен после покупки")
        serializer = self.get_serializer(plan)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get"], url_path="export")
    def export(self, request, *args, **kwargs):
        plan = self.get_object()
        if not request.user.is_authenticated:
            raise PermissionDenied("Требуется аутентификация")
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if not has_meal_plan_access(profile, plan):
            raise PermissionDenied("План доступен после покупки")
        format_name = (
            request.query_params.get("type")
            or request.query_params.get("format")
            or "client"
        )
        try:
            response = export_meal_plan(plan, format_name)
        except MealPlanExportError as exc:
            raise ValidationError({"type": str(exc)}) from exc
        return response

    @action(detail=True, methods=["post"], url_path="purchase")
    def purchase(self, request, *args, **kwargs):
        plan = self.get_object()
        if not request.user.is_authenticated:
            raise PermissionDenied("Требуется аутентификация")
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if plan.user_id == request.user.id:
            serializer = self.get_serializer(plan)
            return Response(
                {
                    "plan": serializer.data,
                    "wallet_transaction_id": None,
                    "price_stars": str(get_meal_plan_price_stars(plan) or 0),
                },
                status=status.HTTP_200_OK,
            )
        rid = getattr(request, "request_id", get_request_id())
        idempotency_key = request.headers.get("Idempotency-Key") or request.META.get("HTTP_IDEMPOTENCY_KEY")
        try:
            result = purchase_meal_plan(
                profile,
                plan,
                rid=rid,
                idempotency_key=idempotency_key,
            )
        except WalletInsufficientFunds as exc:
            raise ValidationError({"detail": str(exc), "code": "insufficient_stars"}) from exc
        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        status_code = status.HTTP_201_CREATED if result.wallet_transaction else status.HTTP_200_OK
        return Response(
            {
                "plan": serializer.data,
                "wallet_transaction_id": getattr(result.wallet_transaction, "id", None),
                "price_stars": str(get_meal_plan_price_stars(plan) or 0),
            },
            status=status_code,
        )


class MealPlanItemViewSet(viewsets.ModelViewSet):
    serializer_class = MealPlanItemSerializer
    permission_classes = [IsMealPlanOwner]

    def get_queryset(self):
        qs = MealPlanItem.objects.select_related(
            "meal_plan",
            "meal_plan__user",
            "recipe",
            "recipe__store",
            "product",
            "product__store",
        )
        user = self.request.user if getattr(self.request.user, "is_authenticated", False) else None
        if self.request.method in permissions.SAFE_METHODS:
            if user:
                qs = qs.filter(Q(meal_plan__user=user) | Q(meal_plan__is_published=True))
            else:
                qs = qs.filter(meal_plan__is_published=True)
        else:
            if not user:
                return MealPlanItem.objects.none()
            qs = qs.filter(meal_plan__user=user)
        return qs.order_by("scheduled_for", "meal_plan_id")

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