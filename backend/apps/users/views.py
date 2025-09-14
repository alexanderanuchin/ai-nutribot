from rest_framework import viewsets, permissions, decorators, response, status, generics
from django.contrib.auth import get_user_model
from .models import Profile
from .serializers import (
    ProfileSerializer,
    UserSerializer,
    RegisterSerializer,
    PhoneCheckSerializer,
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
