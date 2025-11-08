from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Review
from .services import get_supported_content_type
from .targets import resolve_target_model

User = get_user_model()


class ReviewAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "username")
        read_only_fields = fields


class ReviewSerializer(serializers.ModelSerializer):
    author = ReviewAuthorSerializer(read_only=True)
    target_type = serializers.CharField(write_only=True, required=False)
    target_id = serializers.IntegerField(write_only=True, required=False, min_value=1)

    class Meta:
        model = Review
        fields = (
            "id",
            "author",
            "rating",
            "text",
            "created_at",
            "updated_at",
            "target_type",
            "target_id",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")

    def validate(self, attrs):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication is required")
        target_type = attrs.pop("target_type", None)
        target_id = attrs.pop("target_id", None)
        if target_type is None or target_id is None:
            raise serializers.ValidationError("target_type and target_id are required")
        model = resolve_target_model(target_type)
        try:
            content_type = get_supported_content_type(model)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        try:
            target = model.objects.get(pk=target_id)
        except model.DoesNotExist:  # type: ignore[attr-defined]
            raise serializers.ValidationError("Target object not found")
        attrs["content_type"] = content_type
        attrs["object_id"] = target.pk
        self.context["target_instance"] = target
        if Review.objects.filter(
            author=request.user,
            content_type=content_type,
            object_id=target.pk,
        ).exists():
            raise serializers.ValidationError("Вы уже оставили отзыв")
        return super().validate(attrs)

    def create(self, validated_data):
        request = self.context.get("request")
        if request is None:
            raise serializers.ValidationError("Request context is required")
        validated_data.setdefault("author", request.user)
        return super().create(validated_data)
