from __future__ import annotations

import logging

from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .eligibility import ensure_can_review
from .models import Review
from .serializers import ReviewSerializer
from .services import get_supported_content_type, update_rating
from .targets import resolve_target_model

logger = logging.getLogger(__name__)


class ReviewViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    queryset = Review.objects.select_related("author")

    def get_queryset(self):
        queryset = super().get_queryset()
        target_type = self.request.query_params.get("target_type")
        target_id = self.request.query_params.get("target_id")
        if target_type and target_id:
            try:
                model = resolve_target_model(target_type)
                content_type = get_supported_content_type(model)
            except ValueError:
                rid = getattr(self.request, "request_id", None)
                logger.warning(
                    "invalid review target type",
                    extra={"rid": rid, "target_type": target_type},
                )
                return queryset.none()
            try:
                object_id = int(target_id)
            except (TypeError, ValueError):
                rid = getattr(self.request, "request_id", None)
                logger.warning(
                    "invalid review target id",
                    extra={"rid": rid, "target_id": target_id},
                )
                return queryset.none()
            queryset = queryset.filter(content_type=content_type, object_id=object_id)
        return queryset

    def list(self, request, *args, **kwargs):
        target_instance = self._get_target_from_request()
        if target_instance is not None:
            summary = update_rating(target_instance)
            rid = getattr(request, "request_id", None)
            logger.debug(
                "reviews fetched",
                extra={
                    "rid": rid,
                    "target": target_instance.__class__.__name__,
                    "target_id": target_instance.pk,
                    "review_count": summary.count,
                },
            )
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = serializer.context.get("target_instance")
        assert target is not None  # ensured by serializer validate
        result = ensure_can_review(request.user, target)
        if not result.is_allowed:
            return Response({"detail": result.reason}, status=status.HTTP_403_FORBIDDEN)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def _get_target_from_request(self):
        target_type = self.request.query_params.get("target_type")
        target_id = self.request.query_params.get("target_id")
        if not target_type or not target_id:
            return None
        try:
            model = resolve_target_model(target_type)
            object_id = int(target_id)
        except (ValueError, TypeError):
            return None
        try:
            return model.objects.get(pk=object_id)
        except model.DoesNotExist:  # type: ignore[attr-defined]
            return None
