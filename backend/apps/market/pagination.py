from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class MarketPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100
    page_size_query_param = "page_size"

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request)
        if page_size is None:
            page_size = self.page.paginator.per_page

        return Response(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": page_size,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )