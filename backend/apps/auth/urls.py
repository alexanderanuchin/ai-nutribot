from django.urls import path

from .views import WebAppLoginView

urlpatterns = [
    path('webapp/login/', WebAppLoginView.as_view(), name='webapp-login'),
]