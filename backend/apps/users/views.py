from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import decorators, generics, permissions, response, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .api_payloads import build_profile_response
from .models import Profile
from .serializers import (
    ProfileSerializer,
    ProfileUpdateSerializer,
    UserSerializer,
    RegisterSerializer,
    PhoneCheckSerializer,
    EmailCheckSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    PhoneEmailTokenObtainPairSerializer,
)
from .services import build_stars_balance_payload, get_bot_star_balance

class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Profile.objects.select_related("user").all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs


class MeViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _get_or_create_profile(self, user):
        profile, _ = Profile.objects.get_or_create(user=user)
        return profile

    def _build_me_payload(self, user, profile):
        return build_profile_response(user, profile)

    def me(self, request):
        profile = self._get_or_create_profile(request.user)
        payload = self._build_me_payload(request.user, profile)
        return response.Response(payload)

    @decorators.action(detail=False, methods=["patch"])
    def update_profile(self, request):
        prof = self._get_or_create_profile(request.user)
        ser = ProfileUpdateSerializer(prof, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated_profile = ser.save()
        request.user.refresh_from_db()
        payload = self._build_me_payload(request.user, updated_profile)
        if getattr(ser, "password_updated", False):
            refresh = RefreshToken.for_user(request.user)
            payload["tokens"] = {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        return response.Response(payload, status=status.HTTP_200_OK)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class PhoneEmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = PhoneEmailTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class CheckPhoneView(generics.GenericAPIView):
    serializer_class = PhoneCheckSerializer
    permission_classes = [permissions.AllowAny]
    User = get_user_model()

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data["phone"]
        exists = self.User.objects.filter(username=phone).exists()
        return response.Response({"available": not exists})


class CheckEmailView(generics.GenericAPIView):
    serializer_class = EmailCheckSerializer
    permission_classes = [permissions.AllowAny]
    User = get_user_model()

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"]
        exists = self.User.objects.filter(email=email).exists()
        return response.Response({"exists": exists})


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]
    User = get_user_model()

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"]
        users = self.User.objects.filter(email=email)
        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            send_mail(
                "Password reset",
                f"Перейдите по ссылке для сброса пароля: {reset_url}",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=True,
            )
        return response.Response({"detail": "Если такой пользователь существует, мы отправили письмо"})


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]
    User = get_user_model()

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        uid = ser.validated_data["uid"]
        token = ser.validated_data["token"]
        password = ser.validated_data["password"]
        try:
            uid_int = force_str(urlsafe_base64_decode(uid))
            user = self.User.objects.get(pk=uid_int)
        except (self.User.DoesNotExist, ValueError, TypeError):
            return response.Response({"detail": "Invalid link"}, status=status.HTTP_400_BAD_REQUEST)
        if not default_token_generator.check_token(user, token):
            return response.Response({"detail": "Invalid link"}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save()
        return response.Response({"detail": "Пароль обновлён"})


class StarsBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        payload = build_stars_balance_payload(profile)
        return response.Response(payload)


class BotStarsBalanceView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        try:
            balance = get_bot_star_balance()
        except Exception as exc:  # pragma: no cover - network/credentials errors
            return response.Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return response.Response(
            {
                "balance": {
                    "amount": balance.amount,
                    "currency": balance.currency,
                    "updated_at": balance.updated_at.isoformat() if balance.updated_at else None,
                }
            }
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_telegram_session(request, telegram_id: int):
    """
    Возвращает access/refresh токены и expires_at для заданного telegram_id.
    Требует заголовка X-Bot-Key.
    """

    bot_key = request.headers.get("X-Bot-Key")
    if bot_key != getattr(settings, "TELEGRAM_BOT_KEY", ""):
        return response.Response({"detail": "unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

    profile = Profile.objects.filter(telegram_id=telegram_id).first()
    if not profile:
        return response.Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

    session = getattr(profile, "telegram_session", None)
    if not session:
        return response.Response({"detail": "session not found"}, status=status.HTTP_404_NOT_FOUND)

    if session.expires_at <= timezone.now():
        try:
            refreshed = RefreshToken(session.refresh_token)
            new_access = refreshed.access_token
            session.access_token = str(new_access)
            session.expires_at = datetime.fromtimestamp(
                int(new_access["exp"]), tz=dt_timezone.utc
            )
            session.save(update_fields=["access_token", "expires_at", "updated_at"])
        except TokenError:
            return response.Response({"detail": "token expired"}, status=status.HTTP_401_UNAUTHORIZED)

    return response.Response(
        {
            "access": session.access_token,
            "refresh": session.refresh_token,
            "expires_at": session.expires_at.isoformat(),
        }
    )
