from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class MarketEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):  # noqa: D401 - short docstring not needed for stub
        """Return an empty events payload as a temporary stub."""
        return Response({"events": []}, status=200)
