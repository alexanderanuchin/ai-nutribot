from typing import Any, Dict
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from .models import Profile
from .services import build_profile_metrics
from .sidebar import build_profile_sidebar_meta
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


def validate_password_strength(value: str) -> str:
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


AVATAR_ALLOWED_KINDS = {"initials", "preset", "upload"}
MAX_AVATAR_DATA_URL_LENGTH = 5_000_000


class AvatarPreferencesField(serializers.Field):
    default_error_messages = {
        "invalid": "Некорректный формат настроек аватара",
    }

    def get_default(self):
        return {"kind": "initials"}

    def to_representation(self, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return {"kind": "initials"}

        kind = value.get("kind") or "initials"
        if kind == "preset":
            preset_id = value.get("preset_id")
            if isinstance(preset_id, str) and preset_id:
                return {"kind": "preset", "preset_id": preset_id}
            return {"kind": "initials"}
        if kind == "upload":
            data_url = value.get("data_url")
            if isinstance(data_url, str) and data_url:
                return {"kind": "upload", "data_url": data_url}
            return {"kind": "initials"}
        return {"kind": "initials"}

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise serializers.ValidationError(self.error_messages["invalid"])

        kind = data.get("kind")
        if kind not in AVATAR_ALLOWED_KINDS:
            raise serializers.ValidationError({"kind": "Недопустимый тип аватара"})

        if kind == "preset":
            preset_id = data.get("preset_id")
            if not isinstance(preset_id, str) or not preset_id.strip():
                raise serializers.ValidationError({"preset_id": "Укажите идентификатор пресета"})
            if len(preset_id.strip()) > 64:
                raise serializers.ValidationError({"preset_id": "Слишком длинный идентификатор пресета"})
            return {"kind": "preset", "preset_id": preset_id.strip()}

        if kind == "upload":
            data_url = data.get("data_url")
            if not isinstance(data_url, str) or not data_url.strip():
                raise serializers.ValidationError({"data_url": "Передайте изображение для аватара"})
            normalized = data_url.strip()
            if not normalized.startswith("data:image/"):
                raise serializers.ValidationError({"data_url": "Ожидается data URL изображения"})
            if len(normalized) > MAX_AVATAR_DATA_URL_LENGTH:
                raise serializers.ValidationError({"data_url": "Размер изображения превышает допустимый лимит"})
            return {"kind": "upload", "data_url": normalized}

        return {"kind": "initials"}


class WalletSettingsField(serializers.Field):
    default_error_messages = {
        "invalid": "Некорректный формат настроек кошелька",
    }

    def get_default(self):
        return {"show_wallet": False}

    def to_representation(self, value: Any) -> Dict[str, Any]:
        base = {"show_wallet": False}
        if isinstance(value, dict):
            show_wallet = value.get("show_wallet")
            if isinstance(show_wallet, bool):
                base["show_wallet"] = show_wallet
        return base

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise serializers.ValidationError(self.error_messages["invalid"])

        result: Dict[str, Any] = {}
        if "show_wallet" in data:
            show_wallet = data.get("show_wallet")
            if not isinstance(show_wallet, bool):
                raise serializers.ValidationError({"show_wallet": "Ожидается булево значение"})
            result["show_wallet"] = show_wallet

        return result


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
        return validate_password_strength(value)

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
    experience_level_display = serializers.SerializerMethodField()
    metrics = serializers.SerializerMethodField()
    avatar_preferences = AvatarPreferencesField(required=False)
    wallet_settings = WalletSettingsField(required=False)
    sidebar_meta = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            "id", "user",
            "telegram_id", "city", "middle_name",
            "sex", "birth_date",
            "height_cm", "weight_kg", "body_fat_pct",
            "activity_level", "goal",
            "allergies", "exclusions",
            "daily_budget",
            "telegram_stars_balance", "telegram_stars_rate_rub",
            "calocoin_balance", "calocoin_rate_rub",
            "experience_level", "experience_level_display",
            "avatar_preferences", "wallet_settings",
            "sidebar_meta",
            "metrics",
            "created_at", "updated_at",
        )

    def __init__(self, *args, **kwargs):
        include_user = kwargs.pop("include_user", True)
        super().__init__(*args, **kwargs)
        if not include_user:
            self.fields.pop("user", None)

    def get_experience_level_display(self, obj):
        return obj.get_experience_level_display()

    def get_metrics(self, obj):
        return build_profile_metrics(obj)

    def get_sidebar_meta(self, obj):
        return build_profile_sidebar_meta(obj)


class ProfileUpdateSerializer(ProfileSerializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)

    class Meta(ProfileSerializer.Meta):
        fields = ProfileSerializer.Meta.fields + (
            "first_name",
            "last_name",
            "email",
            "phone",
            "password",
        )
        extra_kwargs = {"password": {"write_only": True}}

    def validate_phone(self, value):
        if value in (None, ""):
            raise serializers.ValidationError("Введите корректный номер телефона")
        normalized = normalize_phone(value)
        user = self.instance.user
        exists = User.objects.exclude(pk=user.pk).filter(username=normalized).exists()
        if exists:
            raise serializers.ValidationError("Пользователь с таким телефоном уже существует")
        return normalized

    def validate_email(self, value):
        if value == "":
            return ""
        user = self.instance.user
        exists = User.objects.exclude(pk=user.pk).filter(email__iexact=value).exists()
        if exists:
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value

    def validate_password(self, value):
        if value is None or value == "":
            raise serializers.ValidationError("Пароль не может быть пустым")
        return validate_password_strength(value)

    def update(self, instance, validated_data):
        user = instance.user
        update_fields = set()
        password_changed = False

        first_name = validated_data.pop("first_name", serializers.empty)
        if first_name is not serializers.empty:
            user.first_name = first_name
            update_fields.add("first_name")

        last_name = validated_data.pop("last_name", serializers.empty)
        if last_name is not serializers.empty:
            user.last_name = last_name
            update_fields.add("last_name")

        email = validated_data.pop("email", serializers.empty)
        if email is not serializers.empty:
            user.email = email
            update_fields.add("email")

        phone = validated_data.pop("phone", serializers.empty)
        if phone is not serializers.empty:
            user.username = phone
            update_fields.add("username")

        password = validated_data.pop("password", serializers.empty)
        if password is not serializers.empty:
            user.set_password(password)
            update_fields.add("password")
            password_changed = True

        if update_fields:
            user.save(update_fields=list(update_fields))

            self.password_updated = password_changed

        return super().update(instance, validated_data)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        return validate_password_strength(value)


class PhoneEmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Позволяет авторизоваться по номеру телефона или email."""

    def validate(self, attrs):
        username_or_email = attrs.get(self.username_field)

        if username_or_email:
            # Попробуем найти пользователя по email.
            if "@" in username_or_email:
                user = User.objects.filter(email__iexact=username_or_email).first()
                if user:
                    attrs[self.username_field] = user.get_username()
            else:
                # Попробуем нормализовать номер телефона.
                try:
                    normalized = normalize_phone(username_or_email)
                except serializers.ValidationError:
                    pass
                else:
                    attrs[self.username_field] = normalized

        return super().validate(attrs)
