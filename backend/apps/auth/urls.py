from django.urls import path

from .views import WebAppLoginView, WebAppRefreshView

urlpatterns = [
    path('webapp/login/', WebAppLoginView.as_view(), name='webapp-login'),
    path('webapp/refresh/', WebAppRefreshView.as_view(), name='webapp-refresh'),
]