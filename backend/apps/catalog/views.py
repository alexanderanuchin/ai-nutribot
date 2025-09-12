from rest_framework import viewsets, permissions
from .models import MenuItem
from .serializers import MenuItemSerializer

class MenuItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MenuItem.objects.filter(is_available=True)
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticated]
