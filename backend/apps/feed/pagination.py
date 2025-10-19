from rest_framework.pagination import CursorPagination


class FeedCursorPagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"

    def get_page_size(self, request):
        try:
            return min(int(request.query_params.get("page_size", self.page_size)), 50)
        except (TypeError, ValueError):  # pragma: no cover - validation
            return self.page_size