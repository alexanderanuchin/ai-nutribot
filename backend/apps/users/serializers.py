from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile
import re

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class RegisterSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "phone", "password")

    def validate_phone(self, value):
        digits = re.sub(r"\D", "", value)

        if digits.startswith("8"):
            digits = digits[1:]
        elif digits.startswith("7") and len(digits) == 11:
            digits = digits[1:]
        elif digits.startswith("9") and len(digits) == 10:
            pass
        else:
            raise serializers.ValidationError("Введите корректный номер телефона")

        if len(digits) != 10:
            raise serializers.ValidationError("Введите корректный номер телефона")

        normalized = f"+7{digits}"
        if User.objects.filter(username=normalized).exists():
            raise serializers.ValidationError("Пользователь с таким телефоном уже существует")
        return normalized

    def create(self, validated_data):
        phone = validated_data.pop("phone")
        return User.objects.create_user(username=phone, **validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = (
            "id", "user",
            "telegram_id", "city",
            "sex", "birth_date",
            "height_cm", "weight_kg", "body_fat_pct",
            "activity_level", "goal",
            "allergies", "exclusions",
            "daily_budget",
            "created_at", "updated_at",
        )
