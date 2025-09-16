from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile
import re

User = get_user_model()


def normalize_phone(value: str) -> str:
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

    return f"+7{digits}"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class RegisterSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)
    sms_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("id", "phone", "email", "password", "sms_code")

    def validate_phone(self, value):
        normalized = normalize_phone(value)
        if User.objects.filter(username=normalized).exists():
            raise serializers.ValidationError("Пользователь с таким телефоном уже существует")
        return normalized

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Пароль должен содержать минимум 8 символов")
        if not re.search(r"[A-Z]", value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну заглавную букву")
        if not re.search(r"[a-z]", value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну строчную букву")
        if not re.search(r"\d", value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну цифру")
        if not re.search(r"[^\w\s]", value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы один специальный символ")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value


    def create(self, validated_data):
        phone = validated_data.pop("phone")
        validated_data.pop("sms_code", None)
        return User.objects.create_user(username=phone, **validated_data)


class PhoneCheckSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate_phone(self, value):
        return normalize_phone(value)


class EmailCheckSerializer(serializers.Serializer):
    email = serializers.EmailField()


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


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Пароль должен содержать минимум 8 символов")
        if not re.search(r"[A-Z]", value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну заглавную букву")
        if not re.search(r"[a-z]", value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну строчную букву")
        if not re.search(r"\d", value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну цифру")
        if not re.search(r"[^\w\s]", value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы один специальный символ")
        return value
