from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .planner import build_menu_for_user

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_menu(request):
    data = build_menu_for_user(request.user)
    return Response(data)

@api_view(["GET"])
@permission_classes([AllowAny])
def ping(request):
    return Response({"status": "ok"})
