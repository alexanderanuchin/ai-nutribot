from rest_framework import viewsets, permissions, decorators, response, status, generics
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model
from .models import Profile
from .serializers import (
    ProfileSerializer,
    UserSerializer,
    RegisterSerializer,
    PhoneCheckSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)


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

    @decorators.action(detail=False, methods=["get"])
    def profile(self, request):
        prof, _ = Profile.objects.get_or_create(user=request.user)
        return response.Response(ProfileSerializer(prof).data)

    @decorators.action(detail=False, methods=["patch"])
    def update_profile(self, request):
        prof, _ = Profile.objects.get_or_create(user=request.user)
        ser = ProfileSerializer(prof, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return response.Response(ser.data, status=status.HTTP_200_OK)

    @decorators.action(detail=False, methods=["get"])
    def user(self, request):
        return response.Response(UserSerializer(request.user).data)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
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